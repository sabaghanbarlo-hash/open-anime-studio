from __future__ import annotations

import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, pipeline, planner, storage
from .jobs import JobManager
from .media import ffmpeg_available
from .prompts import CAMERA_PROMPTS, MOTION_PROMPTS, build_image_prompt, build_video_prompt
from .providers import comfy_client, llm_ollama
from .providers.registry import IMAGE_PROVIDERS, VIDEO_PROVIDERS
from .schemas import AssembleJobRequest, KeyframeJobRequest, Plan, ProjectInput, VideoJobRequest

PID = re.compile('^[a-f0-9]{12}$')
SID = re.compile('^s[0-9]{2,3}$')
jobs = JobManager()
config.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Honest status of every feature in the spec. The frontend shows this table as-is.
FEATURES = {
    'structured_planning': ('implemented', 'Ollama JSON planner with a rule-based fallback.'),
    'character_profile': ('implemented', 'The profile text is injected into every scene prompt.'),
    'character_reference_images': ('experimental', 'IP-Adapter workflow template is included but untested; needs ComfyUI_IPAdapter_plus.'),
    'keyframes': ('needs_setup', 'ComfyUI SDXL workflow is included; you must set OAS_SDXL_CHECKPOINT.'),
    'image_to_video': ('needs_setup', 'Provider code is in place; export LTX / Wan 2.2 workflows from your ComfyUI into backend/workflows/.'),
    'camera_motion': ('partial', 'Sent as text to AI models (soft control); exact with the FFmpeg provider.'),
    'subtitles': ('implemented', 'ASS and SRT generation, burned in with libass. Persian needs an Arabic-script font.'),
    'assembly': ('implemented', 'FFmpeg normalise and concat for 16:9, 9:16 and 1:1.'),
    'denoise': ('implemented', 'FFmpeg hqdn3d (classical filter, not AI).'),
    'frame_interpolation': ('implemented', 'FFmpeg minterpolate (classical, can artefact on anime). RIFE is not integrated.'),
    'ai_upscaling': ('not_implemented', 'No Real-ESRGAN or similar integration yet.'),
    'audio': ('not_implemented', 'AudioProvider interface only. No TTS, music or SFX providers yet.'),
    'temporal_consistency': ('limited', 'Only through the shared character prompt, reference images and image-to-video conditioning.'),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    jobs.start()
    yield
    jobs.stop()


app = FastAPI(title='Open Anime Studio', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_methods=['*'], allow_headers=['*'])


@app.middleware('http')
async def private_network_access(request: Request, call_next):
    # Lets a page served from https://*.github.io call this backend on localhost (Chrome preflight).
    response = await call_next(request)
    if request.headers.get('access-control-request-private-network') == 'true':
        response.headers['Access-Control-Allow-Private-Network'] = 'true'
    return response


def _pid(pid: str) -> str:
    if not PID.match(pid):
        raise HTTPException(400, 'Bad project id')
    return pid


def _sid(sid: str) -> str:
    if not SID.match(sid):
        raise HTTPException(400, 'Bad scene id')
    return sid


def _load(pid: str) -> Plan:
    try:
        return storage.load_plan(_pid(pid))
    except FileNotFoundError:
        raise HTTPException(404, 'Project not found')


@app.get('/health')
async def health():
    return {
        'backend': 'ok',
        'ffmpeg': ffmpeg_available(),
        'comfyui': await comfy_client.client.is_up(),
        'comfyui_url': config.COMFY_URL,
        'ollama': await llm_ollama.is_up(),
        'ollama_model': config.OLLAMA_MODEL,
    }


@app.get('/capabilities')
async def capabilities():
    return {
        'image_providers': [p.info() for p in IMAGE_PROVIDERS.values()],
        'video_providers': [p.info() for p in VIDEO_PROVIDERS.values()],
        'camera_movements': list(CAMERA_PROMPTS),
        'motions': list(MOTION_PROMPTS),
        'subtitle_languages': ['ja', 'en', 'fa'],
        'aspect_ratios': ['16:9', '9:16', '1:1'],
        'features': {k: {'status': v[0], 'note': v[1]} for k, v in FEATURES.items()},
    }


@app.post('/plan')
async def create_plan(inp: ProjectInput):
    plan = await planner.make_plan(inp)
    return storage.create_project(plan)


@app.get('/projects/{pid}')
async def get_project(pid: str):
    return _load(pid)


@app.put('/projects/{pid}/plan')
async def put_plan(pid: str, plan: Plan):
    _load(pid)
    plan.project_id = pid
    ids = [s.scene_id for s in plan.scenes]
    if not all(SID.match(i) for i in ids) or len(set(ids)) != len(ids):
        raise HTTPException(400, 'Scene ids must be unique and look like s01')
    storage.save_plan(plan)
    return plan


@app.post('/projects/{pid}/rebuild-prompts')
async def rebuild_prompts(pid: str):
    plan = _load(pid)
    for s in plan.scenes:
        s.image_prompt = build_image_prompt(s, plan.character)
        s.video_prompt = build_video_prompt(s, plan.character)
    storage.save_plan(plan)
    return plan


@app.post('/projects/{pid}/reference')
async def upload_reference(pid: str, file: UploadFile = File(...)):
    plan = _load(pid)
    ext = ('.' + (file.filename or '').rsplit('.', 1)[-1].lower()) if '.' in (file.filename or '') else ''
    if ext not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise HTTPException(400, 'Use a png, jpg or webp image')
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, 'Image larger than 20 MB')
    folder = storage.project_dir(pid) / 'reference'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ('character' + ext)).write_bytes(data)
    plan.character.reference_image = 'reference/character' + ext
    storage.save_plan(plan)
    return plan


@app.post('/projects/{pid}/scenes/{sid}/keyframe')
async def make_keyframe(pid: str, sid: str, req: KeyframeJobRequest):
    _load(pid)
    _sid(sid)
    job = jobs.submit('keyframe', lambda j: pipeline.keyframe_job(pid, sid, req, j))
    return {'job_id': job.id}


@app.post('/projects/{pid}/scenes/{sid}/video')
async def make_video(pid: str, sid: str, req: VideoJobRequest):
    _load(pid)
    _sid(sid)
    job = jobs.submit('video', lambda j: pipeline.video_job(pid, sid, req, j))
    return {'job_id': job.id}


@app.post('/projects/{pid}/assemble')
async def assemble(pid: str, req: AssembleJobRequest):
    _load(pid)
    job = jobs.submit('assemble', lambda j: pipeline.assemble_job(pid, req, j))
    return {'job_id': job.id}


@app.get('/jobs/{job_id}')
async def get_job(job_id: str):
    job = jobs.jobs.get(job_id)
    if job is None:
        raise HTTPException(404, 'Unknown job')
    return job.public()


app.mount('/files', StaticFiles(directory=str(config.PROJECTS_DIR)), name='files')
if config.DOCS_DIR.exists():
    # Optional: serve the frontend from the backend too (avoids any https -> http browser restrictions).
    app.mount('/ui', StaticFiles(directory=str(config.DOCS_DIR), html=True), name='ui')
