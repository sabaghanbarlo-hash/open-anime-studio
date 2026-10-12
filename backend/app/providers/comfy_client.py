from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

import httpx

from .. import config
from ..errors import ProviderError, ProviderNotConfigured

PLACEHOLDER = re.compile('^[{][{]([A-Z_]+)[}][}]$')


def fill_template(node: Any, values: Dict[str, Any]) -> Any:
    """Replace placeholder strings like {{PROMPT}} in an API-format ComfyUI workflow.
    A string that is exactly one placeholder is replaced by the typed value (int, float, str)."""
    if isinstance(node, dict):
        return {k: fill_template(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [fill_template(v, values) for v in node]
    if isinstance(node, str):
        m = PLACEHOLDER.match(node)
        if m and m.group(1) in values:
            return values[m.group(1)]
        out = node
        for k, v in values.items():
            out = out.replace('{{' + k + '}}', str(v))
        return out
    return node


def load_template(name: str, hint: str = '') -> dict:
    path = config.WORKFLOW_DIR / name
    if not path.exists():
        raise ProviderNotConfigured('Workflow template backend/workflows/' + name + ' not found. ' + hint)
    return json.loads(path.read_text(encoding='utf-8'))


class ComfyClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip('/')
        self.client_id = uuid.uuid4().hex

    async def is_up(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(self.base + '/system_stats')
                return r.status_code == 200
        except Exception:
            return False

    async def upload_image(self, path: Path) -> str:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                self.base + '/upload/image',
                files={'image': (path.name, path.read_bytes())},
                data={'overwrite': 'true'},
            )
            r.raise_for_status()
            return r.json()['name']

    async def run(self, workflow: dict, timeout: float = 3600, poll: float = 2.0) -> dict:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(self.base + '/prompt', json={'prompt': workflow, 'client_id': self.client_id})
            if r.status_code != 200:
                raise ProviderError('ComfyUI rejected the workflow: ' + r.text[:1200])
            pid = r.json()['prompt_id']
            waited = 0.0
            while waited < timeout:
                h = await c.get(self.base + '/history/' + pid)
                h.raise_for_status()
                entry = h.json().get(pid)
                if entry:
                    status = entry.get('status', {})
                    if status.get('status_str') == 'error':
                        raise ProviderError('ComfyUI execution error: ' + json.dumps(status.get('messages', []))[:1200])
                    if status.get('completed') or entry.get('outputs'):
                        return entry
                await asyncio.sleep(poll)
                waited += poll
        raise ProviderError('Timed out waiting for ComfyUI')

    @staticmethod
    def output_files(entry: dict) -> List[dict]:
        files = []
        for node in entry.get('outputs', {}).values():
            for val in node.values():
                if isinstance(val, list):
                    files.extend(i for i in val if isinstance(i, dict) and 'filename' in i)
        final = [f for f in files if f.get('type') == 'output']
        return final or files

    async def download(self, item: dict) -> bytes:
        params = {'filename': item['filename'], 'subfolder': item.get('subfolder', ''), 'type': item.get('type', 'output')}
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.get(self.base + '/view', params=params)
            r.raise_for_status()
            return r.content


client = ComfyClient(config.COMFY_URL)
