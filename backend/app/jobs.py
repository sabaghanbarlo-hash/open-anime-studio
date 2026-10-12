from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional

from .errors import ProviderError

log = logging.getLogger('oas.jobs')


@dataclass
class Job:
    id: str
    kind: str
    status: str = 'queued'
    message: str = ''
    result: Optional[dict] = None
    error: Optional[str] = None
    created: float = field(default_factory=time.time)

    def public(self) -> dict:
        return {'id': self.id, 'kind': self.kind, 'status': self.status, 'message': self.message, 'result': self.result, 'error': self.error}


class JobManager:
    """One worker, so GPU jobs run strictly one after another."""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._queue: Optional[asyncio.Queue] = None
        self._task: Optional[asyncio.Task] = None

    def start(self):
        self._queue = asyncio.Queue()
        self._task = asyncio.create_task(self._worker())

    def stop(self):
        if self._task:
            self._task.cancel()

    def submit(self, kind: str, factory: Callable[[Job], Awaitable[dict]]) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind)
        self.jobs[job.id] = job
        self._queue.put_nowait((job, factory))
        if len(self.jobs) > 200:
            old = sorted((j for j in self.jobs.values() if j.status in ('done', 'error')), key=lambda j: j.created)[:50]
            for j in old:
                self.jobs.pop(j.id, None)
        return job

    async def _worker(self):
        while True:
            job, factory = await self._queue.get()
            job.status = 'running'
            try:
                job.result = await factory(job)
                job.status = 'done'
                job.message = 'Done'
            except ProviderError as e:
                job.status = 'error'
                job.error = str(e)
            except Exception as e:
                log.exception('job failed')
                job.status = 'error'
                job.error = type(e).__name__ + ': ' + str(e)
