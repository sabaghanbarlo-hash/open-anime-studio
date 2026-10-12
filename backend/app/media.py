from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import List, Optional

from . import config
from .errors import ProviderError


def ffmpeg_available() -> bool:
    return shutil.which(config.FFMPEG) is not None


async def run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise ProviderError(cmd[0] + ' not found. Install FFmpeg and make sure it is on PATH.')
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise ProviderError(cmd[0] + ' failed: ' + err.decode(errors='replace')[-1500:])
    return out.decode(errors='replace')


async def probe_duration(path: Path) -> float:
    out = await run([config.FFPROBE, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)])
    return float(out.strip())
