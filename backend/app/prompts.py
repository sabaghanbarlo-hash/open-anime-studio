from __future__ import annotations

from .schemas import CharacterProfile, Scene

# Camera moves are passed to AI video models as text (a soft hint they may follow loosely).
# The FFmpeg provider implements them exactly.
CAMERA_PROMPTS = {
    'static': 'static camera',
    'slow_push': 'slow camera push in',
    'pull': 'slow camera pull back',
    'pan_left': 'camera pans left',
    'pan_right': 'camera pans right',
    'tilt_up': 'camera tilts up',
    'tilt_down': 'camera tilts down',
    'tracking': 'tracking shot following the character',
}

MOTION_PROMPTS = {
    'walking': 'character walking',
    'turning': 'character turns around',
    'hair_movement': 'hair gently moving in the wind',
    'blinking': 'character blinks naturally',
    'facial_expression': 'subtle change of facial expression',
    'environment_movement': 'environment in motion, drifting clouds, falling leaves',
}

DEFAULT_NEGATIVE = (
    'lowres, bad anatomy, bad hands, extra fingers, missing fingers, deformed, blurry, '
    'watermark, text, signature, jpeg artifacts, inconsistent character design'
)


def _join(parts) -> str:
    return ', '.join(p.strip() for p in parts if p and p.strip())


def build_image_prompt(scene: Scene, character: CharacterProfile) -> str:
    env = scene.environment if scene.environment != scene.location else ''
    return _join([
        'masterpiece, best quality',
        scene.visual_style,
        scene.camera_angle,
        character.prompt_fragment(),
        scene.character_actions,
        scene.facial_expression,
        scene.location,
        env,
        scene.lighting,
        scene.mood,
    ])


def build_video_prompt(scene: Scene, character: CharacterProfile) -> str:
    motion = [MOTION_PROMPTS[m] for m in scene.motion if m in MOTION_PROMPTS]
    return _join([
        character.prompt_fragment(),
        scene.character_actions,
        scene.facial_expression,
        scene.environment or scene.location,
        scene.visual_style,
        CAMERA_PROMPTS.get(scene.camera_movement, ''),
        *motion,
        scene.lighting,
        scene.mood,
    ])
