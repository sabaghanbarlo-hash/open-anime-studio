from __future__ import annotations

from .. import config
from ..media import ffmpeg_available, run
from .base import GenResult, VideoProvider, VideoRequest


class KenBurnsProvider(VideoProvider):
    """Not an AI model. It animates the keyframe with a real FFmpeg camera move.
    Useful to test the whole pipeline (keyframe -> clip -> subtitles -> MP4) on a machine without a GPU."""

    id = 'kenburns'
    name = 'FFmpeg camera move on the still (no AI, pipeline test)'
    requires_gpu = False
    license_note = 'No model involved. FFmpeg only.'

    def configured(self):
        if ffmpeg_available():
            return True, ''
        return False, 'FFmpeg was not found on PATH.'

    async def generate(self, req: VideoRequest) -> GenResult:
        w, h = req.resolution
        n = max(2, round(req.duration * req.fps))
        p = 'on/' + str(n)
        cx = 'iw/2-(iw/zoom/2)'
        cy = 'ih/2-(ih/zoom/2)'
        moves = {
            'static': ('1.0', cx, cy),
            'slow_push': ('1.0+0.2*' + p, cx, cy),
            'pull': ('1.2-0.2*' + p, cx, cy),
            'pan_left': ('1.2', '(iw-iw/zoom)*(1-' + p + ')', cy),
            'pan_right': ('1.2', '(iw-iw/zoom)*' + p, cy),
            'tracking': ('1.2', '(iw-iw/zoom)*' + p, cy),
            'tilt_up': ('1.2', cx, '(ih-ih/zoom)*(1-' + p + ')'),
            'tilt_down': ('1.2', cx, '(ih-ih/zoom)*' + p),
        }
        z, x, y = moves.get(req.camera_motion, moves['static'])
        bw, bh = w * 2, h * 2
        vf = (
            'scale=' + str(bw) + ':' + str(bh) + ':force_original_aspect_ratio=increase,crop=' + str(bw) + ':' + str(bh)
            + ',zoompan=z=' + z + ':x=' + x + ':y=' + y + ':d=' + str(n) + ':s=' + str(w) + 'x' + str(h) + ':fps=' + str(req.fps)
            + ',format=yuv420p'
        )
        req.output.parent.mkdir(parents=True, exist_ok=True)
        await run([config.FFMPEG, '-y', '-i', str(req.image), '-vf', vf, '-frames:v', str(n), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(req.output)])
        return GenResult(req.output, ['No AI motion: this is a camera move over the still image.'])
