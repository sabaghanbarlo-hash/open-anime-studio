from __future__ import annotations

import json

import httpx

from .. import config


async def is_up() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(config.OLLAMA_URL + '/api/tags')
            return r.status_code == 200
    except Exception:
        return False


async def chat_json(system: str, user: str, timeout: float = 180) -> dict:
    payload = {
        'model': config.OLLAMA_MODEL,
        'stream': False,
        'format': 'json',
        'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
        'options': {'temperature': 0.4},
    }
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(config.OLLAMA_URL + '/api/chat', json=payload)
        r.raise_for_status()
        return json.loads(r.json()['message']['content'])
