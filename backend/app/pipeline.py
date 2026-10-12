from __future__ import annotations

import random

from . import config, storage
from .assemble import assemble_video
from .errors import ProviderError
from .prompts import build_image_prompt, build_video_prompt
from .providers.base import ImageRequest, VideoRequest
from .providers.registry import IMAGE_PROVIDERS, VIDEO_PROVIDERS
from .schemas import AssembleJobRequest, KeyframeJobRequest, VideoJobRequest


def _scene(plan, sid):
    for s in plan.scenes:
        if s.scene_id == sid:
            return s
    raise ProviderError('Unknown scene ' + sid)


def _seed(v):
    return v if v is not None else random.randint(0, 2 ** 32 - 1)


async def keyframe_job(pid: str, sid: str, req: KeyframeJobRequest, job) -> dict:
    plan = storage.load_plan(pid)
    scene = _scene(plan, sid)
    provider = IMAGE_PROVIDERS.get(req.provider)
    if provider is None:
        raise ProviderError('Unknown image provider ' + req.provider)
    w, h = config.KEYFRAME_SIZES[plan.input.aspect_ratio]
    ref = None
    if req.use_reference:
        rel = plan.character.reference_image
        if not rel and plan.scenes and plan.scenes[0].scene_id != sid and plan.scenes[0].keyframe:
            rel = plan.scenes[0].keyframe  # reuse the first keyframe as the character reference
        if rel:
            ref = storage.resolve(pid, rel)
    out = storage.project_dir(pid) / 'keyframes' / (sid + '.png')
    job.message = 'Generating keyframe with ' + provider.name
    res = await provider.generate(ImageRequest(
        prompt=scene.image_prompt or build_image_prompt(scene, plan.character),
        negative_prompt=scene.negative_prompt,
        width=w,
        height=h,
        seed=_seed(req.seed),
        output=out,
        reference_image=ref,
    ))
    plan = storage.load_plan(pid)
    _scene(plan, sid).keyframe = 'keyframes/' + sid + '.png'
    storage.save_plan(plan)
    return {'keyframe': 'keyframes/' + sid + '.png', 'notes': res.notes}


async def video_job(pid: str, sid: str, req: VideoJobRequest, job) -> dict:
    plan = storage.load_plan(pid)
    scene = _scene(plan, sid)
    if not scene.keyframe:
        raise ProviderError('Generate a keyframe for this scene first.')
    provider = VIDEO_PROVIDERS.get(req.provider)
    if provider is None:
        raise ProviderError('Unknown video provider ' + req.provider)
    size = req.resolution or list(config.CLIP_SIZES[plan.input.aspect_ratio])
    if len(size) != 2:
        raise ProviderError('resolution must be [width, height]')
    out = storage.project_dir(pid) / 'clips' / (sid + '.mp4')
    job.message = 'Generating clip with ' + provider.name + ' (AI video can take several minutes)'
    res = await provider.generate(VideoRequest(
        image=storage.resolve(pid, scene.keyframe),
        prompt=scene.video_prompt or build_video_prompt(scene, plan.character),
        negative_prompt=scene.negative_prompt,
        duration=scene.duration,
        fps=req.fps,
        resolution=(size[0], size[1]),
        camera_motion=scene.camera_movement,
        seed=_seed(req.seed),
        output=out,
    ))
    plan = storage.load_plan(pid)
    _scene(plan, sid).clip = 'clips/' + sid + '.mp4'
    storage.save_plan(plan)
    return {'clip': 'clips/' + sid + '.mp4', 'notes': res.notes}


async def assemble_job(pid: str, req: AssembleJobRequest, job) -> dict:
    plan = storage.load_plan(pid)
    clips = []
    for s in plan.scenes:
        if not s.clip:
            raise ProviderError('Scene ' + s.scene_id + ' has no clip yet.')
        clips.append(storage.resolve(pid, s.clip))
    base = storage.project_dir(pid)
    aspect = req.aspect_ratio or plan.input.aspect_ratio
    return await assemble_video(base / 'build', clips, plan.scenes, req, aspect, base / 'output' / 'final.mp4', job)
