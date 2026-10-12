from __future__ import annotations

import json
import logging
import math
import re

from . import config
from .prompts import CAMERA_PROMPTS, DEFAULT_NEGATIVE, MOTION_PROMPTS, build_image_prompt, build_video_prompt
from .providers import llm_ollama
from .schemas import LANGS, DialogueLine, Plan, ProjectInput, Scene

log = logging.getLogger('oas.planner')
MAX_CLIP = 5.0
MAX_SCENES = 12

SYSTEM = (
    'You are a storyboard planner for short anime clips. Reply with one JSON object that has a key named scenes '
    'holding a list. Each scene object may contain: location, characters (list of names), character_actions, '
    'facial_expression, dialogue (list of objects with speaker and text; text is an object keyed by language code ja, en, fa), '
    'camera_angle, camera_movement (one of the given options), motion (list chosen from the given options), lighting, '
    'environment, visual_style, mood, duration (seconds between 2 and 5). '
    'Rules: describe actions, expressions and setting only. Never redescribe the character hair, eyes or clothing, '
    'because the character profile is attached to every scene separately. '
    'Provide dialogue in all three languages when you are confident, otherwise leave a language out. '
    'Keep the total duration close to the requested duration and respect target_scene_count.'
)


def parse_dialogue(raw: str, lang: str):
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        speaker, text = '', line
        m = re.match('^([^:：]{1,24})[:：][ ]*(.+)$', line)
        if m:
            speaker, text = m.group(1).strip(), m.group(2).strip()
        lines.append(DialogueLine(speaker=speaker, text={lang: text}))
    return lines


def heuristic_scenes(inp: ProjectInput):
    n = min(MAX_SCENES, max(1, math.ceil(inp.duration / MAX_CLIP)))
    lines = parse_dialogue(inp.dialogue, inp.dialogue_language)
    per = round(min(8.0, max(1.0, inp.duration / n)), 2)
    scenes = []
    for i in range(n):
        chunk = lines[i * len(lines) // n:(i + 1) * len(lines) // n]
        scenes.append(Scene(
            scene_id='s' + str(i + 1).zfill(2),
            duration=per,
            location=inp.environment,
            characters=[inp.character.name],
            character_actions=inp.description,
            facial_expression=inp.mood,
            dialogue=chunk,
            camera_angle=inp.shot_type,
            camera_movement=inp.camera_movement,
            motion=list(inp.motion),
            lighting=inp.lighting,
            environment=inp.environment,
            visual_style=inp.animation_style,
            mood=inp.mood,
            negative_prompt=DEFAULT_NEGATIVE,
        ))
    return scenes


def coerce_scene(d: dict, idx: int, inp: ProjectInput) -> Scene:
    def s(key, default=''):
        v = d.get(key)
        return v.strip() if isinstance(v, str) and v.strip() else default

    dialogue = []
    raw_lines = d.get('dialogue') if isinstance(d.get('dialogue'), list) else []
    for line in raw_lines:
        if not isinstance(line, dict):
            continue
        text = line.get('text')
        if isinstance(text, str):
            text = {inp.dialogue_language: text}
        if not isinstance(text, dict):
            continue
        text = {k: v.strip() for k, v in text.items() if k in LANGS and isinstance(v, str) and v.strip()}
        if text:
            dialogue.append(DialogueLine(speaker=str(line.get('speaker') or ''), text=text))
    cam = s('camera_movement', inp.camera_movement)
    if cam not in CAMERA_PROMPTS:
        cam = inp.camera_movement
    motion_raw = d.get('motion') if isinstance(d.get('motion'), list) else []
    motion = [m for m in motion_raw if m in MOTION_PROMPTS] or list(inp.motion)
    try:
        duration = float(d.get('duration', MAX_CLIP))
    except (TypeError, ValueError):
        duration = MAX_CLIP
    chars = d.get('characters') if isinstance(d.get('characters'), list) else []
    return Scene(
        scene_id='s' + str(idx + 1).zfill(2),
        duration=min(8.0, max(1.0, duration)),
        location=s('location', inp.environment),
        characters=[str(c) for c in chars] or [inp.character.name],
        character_actions=s('character_actions', inp.description),
        facial_expression=s('facial_expression', inp.mood),
        dialogue=dialogue,
        camera_angle=s('camera_angle', inp.shot_type),
        camera_movement=cam,
        motion=motion,
        lighting=s('lighting', inp.lighting),
        environment=s('environment', inp.environment),
        visual_style=s('visual_style', inp.animation_style),
        mood=s('mood', inp.mood),
        negative_prompt=DEFAULT_NEGATIVE,
    )


async def llm_scenes(inp: ProjectInput):
    n = min(MAX_SCENES, max(1, math.ceil(inp.duration / MAX_CLIP)))
    user = json.dumps({
        'request': inp.model_dump(),
        'target_scene_count': n,
        'camera_movement_options': list(CAMERA_PROMPTS),
        'motion_options': list(MOTION_PROMPTS),
        'dialogue_languages': list(LANGS),
    }, ensure_ascii=False)
    data = await llm_ollama.chat_json(SYSTEM, user)
    raw = data.get('scenes') if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise ValueError('the model did not return a scenes list')
    scenes = [coerce_scene(d, i, inp) for i, d in enumerate(raw[:MAX_SCENES]) if isinstance(d, dict)]
    if not scenes:
        raise ValueError('the model returned zero usable scenes')
    return scenes


async def make_plan(inp: ProjectInput) -> Plan:
    warnings = []
    used = 'rule-based'
    scenes = None
    if await llm_ollama.is_up():
        try:
            scenes = await llm_scenes(inp)
            used = 'ollama:' + config.OLLAMA_MODEL
        except Exception as e:
            log.warning('LLM planning failed: %s', e)
            warnings.append('LLM planning failed (' + type(e).__name__ + ': ' + str(e) + '). Used the rule-based planner instead.')
    else:
        warnings.append('Ollama is not running at ' + config.OLLAMA_URL + '. The rule-based planner only splits your text into scenes: it does not write story beats and cannot translate dialogue.')
    if scenes is None:
        scenes = heuristic_scenes(inp)
    for sc in scenes:
        sc.image_prompt = build_image_prompt(sc, inp.character)
        sc.video_prompt = build_video_prompt(sc, inp.character)
    return Plan(project_id='', input=inp, character=inp.character, scenes=scenes, planner=used, warnings=warnings)
