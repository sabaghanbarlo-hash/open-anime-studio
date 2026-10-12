from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .schemas import Scene, SubtitleOptions

NL = chr(92) + 'N'  # ASS hard line break
ALIGN = {'bottom': 2, 'middle': 5, 'top': 8}


@dataclass
class Cue:
    start: float
    end: float
    text: str


def build_cues(scenes: List[Scene], durations: List[float], lang: str, offset: float = 0.0) -> Tuple[List[Cue], List[str]]:
    """Spread each scene's dialogue lines evenly across that scene's real clip duration."""
    cues: List[Cue] = []
    warnings: List[str] = []
    t0 = 0.0
    for scene, dur in zip(scenes, durations):
        n = len(scene.dialogue)
        if n:
            slot = max(0.5, dur - 0.3) / n
            for i, line in enumerate(scene.dialogue):
                text = (line.text.get(lang) or '').strip()
                if not text:
                    warnings.append('Scene ' + scene.scene_id + ' line ' + str(i + 1) + ' has no ' + lang + ' text; skipped.')
                    continue
                start = max(0.0, t0 + 0.15 + i * slot + offset)
                end = start + max(0.5, slot - 0.1)
                cues.append(Cue(start, end, text))
        t0 += dur
    return cues, warnings


def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    return str(cs // 360000) + ':' + str((cs // 6000) % 60).zfill(2) + ':' + str((cs // 100) % 60).zfill(2) + '.' + str(cs % 100).zfill(2)


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return str(ms // 3600000).zfill(2) + ':' + str((ms // 60000) % 60).zfill(2) + ':' + str((ms // 1000) % 60).zfill(2) + ',' + str(ms % 1000).zfill(3)


def write_srt(cues: List[Cue], path: Path) -> None:
    out = []
    for i, c in enumerate(cues, 1):
        out.append(str(i) + chr(10) + _srt_time(c.start) + ' --> ' + _srt_time(c.end) + chr(10) + c.text + chr(10))
    path.write_text(chr(10).join(out), encoding='utf-8')


def write_ass(cues: List[Cue], path: Path, width: int, height: int, opts: SubtitleOptions) -> None:
    head = [
        '[Script Info]',
        'ScriptType: v4.00+',
        'PlayResX: ' + str(width),
        'PlayResY: ' + str(height),
        'WrapStyle: 0',
        'ScaledBorderAndShadow: yes',
        '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Default,' + opts.font + ',' + str(opts.size) + ',&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,'
        + str(opts.outline) + ',0,' + str(ALIGN[opts.position]) + ',40,40,' + str(opts.margin_v) + ',1',
        '',
        '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    for c in cues:
        text = c.text.replace('{', '(').replace('}', ')').replace(chr(10), NL)
        head.append('Dialogue: 0,' + _ass_time(c.start) + ',' + _ass_time(c.end) + ',Default,,0,0,0,,' + text)
    path.write_text(chr(10).join(head) + chr(10), encoding='utf-8')
