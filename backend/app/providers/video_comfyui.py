from __future__ import annotations

from .. import config
from ..errors import ProviderError, ProviderNotConfigured
from ..media import run
from . import comfy_client
from .base import GenResult, VideoProvider, VideoRequest

VIDEO_EXTS = ('.mp4', '.webm', '.mkv', '.mov')


def snap_frames(seconds: float, fps: int, step: int) -> int:
    """Video models want frame counts of the form step*k+1 (LTX: 8k+1, Wan: 4k+1)."""
    wanted = max(1, round(seconds * fps))
    k = max(1, round((wanted - 1) / step))
    return k * step + 1


class ComfyVideoProvider(VideoProvider):
    requires_gpu = True

    def __init__(self, key: str, title: str, template: str, frame_step: int, license_note: str, hint: str):
        self.id = key
        self.name = title
        self.template = template
        self.frame_step = frame_step
        self.license_note = license_note
        self.hint = hint

    def configured(self):
        if not (config.WORKFLOW_DIR / self.template).exists():
            return False, 'Missing backend/workflows/' + self.template + '. ' + self.hint
        return True, ''

    async def generate(self, req: VideoRequest) -> GenResult:
        template = comfy_client.load_template(self.template, self.hint)
        if not await comfy_client.client.is_up():
            raise ProviderError('ComfyUI is not reachable at ' + config.COMFY_URL + '. Start ComfyUI first.')
        uploaded = await comfy_client.client.upload_image(req.image)
        frames = snap_frames(req.duration, req.fps, self.frame_step)
        w, h = req.resolution
        values = {
            'IMAGE': uploaded,
            'PROMPT': req.prompt,
            'NEGATIVE': req.negative_prompt,
            'WIDTH': w,
            'HEIGHT': h,
            'LENGTH': frames,
            'FPS': req.fps,
            'SEED': req.seed,
        }
        entry = await comfy_client.client.run(comfy_client.fill_template(template, values), timeout=3600)
        files = comfy_client.client.output_files(entry)
        videos = [f for f in files if f['filename'].lower().endswith(VIDEO_EXTS)]
        if not videos:
            raise ProviderError(
                'The workflow produced no video file (got: ' + ', '.join(f['filename'] for f in files) + '). '
                'End your workflow with a video-saving node (SaveVideo or VHS Video Combine) that writes an mp4.'
            )
        data = await comfy_client.client.download(videos[-1])
        req.output.parent.mkdir(parents=True, exist_ok=True)
        if videos[-1]['filename'].lower().endswith('.mp4'):
            req.output.write_bytes(data)
        else:
            tmp = req.output.with_suffix('.src' + videos[-1]['filename'][videos[-1]['filename'].rfind('.'):])
            tmp.write_bytes(data)
            await run([config.FFMPEG, '-y', '-i', str(tmp), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(req.output)])
            tmp.unlink(missing_ok=True)
        return GenResult(req.output, ['frames ' + str(frames) + ' at ' + str(req.fps) + ' fps', 'seed ' + str(req.seed)])
