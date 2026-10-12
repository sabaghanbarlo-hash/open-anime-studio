from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from . import config, subtitles
from .media import probe_duration, run
from .schemas import AssembleJobRequest, Scene


def _fontsdir_arg() -> str:
    if not config.FONTS_DIR.exists():
        return ''
    p = str(config.FONTS_DIR).replace(chr(92), '/').replace(':', chr(92) + ':')
    return ':fontsdir=' + p


async def assemble_video(workdir: Path, clips: List[Path], scenes: List[Scene], opts: AssembleJobRequest, aspect: str, out: Path, job=None) -> dict:
    warnings: List[str] = []
    w, h = config.FINAL_SIZES[aspect]
    workdir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    target_fps = opts.interpolate_fps or opts.fps
    chain = 'scale=' + str(w) + ':' + str(h) + ':force_original_aspect_ratio=increase,crop=' + str(w) + ':' + str(h) + ',setsar=1'
    if opts.denoise:
        chain += ',hqdn3d=2:1.5:3:3'
    if opts.interpolate_fps:
        chain += ',minterpolate=fps=' + str(target_fps) + ':mi_mode=mci'
    else:
        chain += ',fps=' + str(target_fps)

    names: List[str] = []
    durations: List[float] = []
    for i, clip in enumerate(clips):
        if job:
            job.message = 'Normalising clip ' + str(i + 1) + ' of ' + str(len(clips))
        name = 'norm_' + str(i).zfill(2) + '.mp4'
        await run([config.FFMPEG, '-y', '-i', str(clip), '-vf', chain, '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', name], cwd=workdir)
        durations.append(await probe_duration(workdir / name))
        names.append(name)

    if job:
        job.message = 'Joining clips'
    q = chr(39)
    (workdir / 'list.txt').write_text(chr(10).join('file ' + q + n + q for n in names) + chr(10), encoding='utf-8')
    await run([config.FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', 'list.txt', '-c', 'copy', 'concat.mp4'], cwd=workdir)

    files = {}
    sub: Optional[object] = opts.subtitles
    if sub is not None:
        cues, warns = subtitles.build_cues(scenes, durations, sub.language, sub.offset)
        warnings += warns
        if not cues:
            warnings.append('No subtitle text found for language ' + sub.language + '; subtitles were not added.')
            sub = None
        else:
            subtitles.write_ass(cues, out.parent / 'subtitles.ass', w, h, sub)
            subtitles.write_srt(cues, out.parent / 'subtitles.srt')
            files['ass'] = 'output/subtitles.ass'
            files['srt'] = 'output/subtitles.srt'

    if sub is not None and sub.burn_in:
        if job:
            job.message = 'Burning subtitles'
        ass_abs = str(out.parent / 'subtitles.ass')
        # Run from the output folder so the filter path stays simple.
        await run([config.FFMPEG, '-y', '-i', str((workdir / 'concat.mp4').resolve()), '-vf', 'ass=subtitles.ass' + _fontsdir_arg(), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(out.resolve())], cwd=out.parent)
        _ = ass_abs
        if sub.language == 'fa' and not config.FONTS_DIR.exists():
            warnings.append('Persian subtitles need a font with Arabic script (for example Vazirmatn). Put it in backend/fonts/ and use its family name.')
    else:
        out.write_bytes((workdir / 'concat.mp4').read_bytes())

    warnings.append('Audio: this version produces silent video. Audio providers are interface-only.')
    return {'video': 'output/final.mp4', 'files': files, 'warnings': warnings, 'duration': round(sum(durations), 2)}
