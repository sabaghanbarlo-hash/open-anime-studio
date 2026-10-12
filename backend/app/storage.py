from __future__ import annotations

import uuid
from pathlib import Path

from . import config
from .errors import ProviderError
from .schemas import Plan


def project_dir(pid: str) -> Path:
    return config.PROJECTS_DIR / pid


def create_project(plan: Plan) -> Plan:
    plan.project_id = uuid.uuid4().hex[:12]
    project_dir(plan.project_id).mkdir(parents=True, exist_ok=True)
    save_plan(plan)
    return plan


def load_plan(pid: str) -> Plan:
    path = project_dir(pid) / 'plan.json'
    if not path.exists():
        raise FileNotFoundError(pid)
    return Plan.model_validate_json(path.read_text(encoding='utf-8'))


def save_plan(plan: Plan) -> None:
    path = project_dir(plan.project_id) / 'plan.json'
    path.write_text(plan.model_dump_json(indent=2), encoding='utf-8')


def resolve(pid: str, rel: str) -> Path:
    """Resolve a project-relative path and refuse anything that escapes the project folder."""
    base = project_dir(pid).resolve()
    path = (base / rel).resolve()
    if base != path and base not in path.parents:
        raise ProviderError('Path escapes the project folder')
    if not path.exists():
        raise ProviderError('File not found: ' + rel)
    return path
