from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

AspectRatio = Literal['16:9', '9:16', '1:1']
Lang = Literal['ja', 'en', 'fa']
LANGS = ('ja', 'en', 'fa')


class CharacterProfile(BaseModel):
    name: str = 'Character'
    description: str = ''
    age: str = ''
    hairstyle: str = ''
    hair_color: str = ''
    eye_color: str = ''
    clothing: str = ''
    body_proportions: str = ''
    accessories: str = ''
    personality: str = ''
    visual_style: str = 'anime'
    reference_image: Optional[str] = None

    def prompt_fragment(self) -> str:
        hair = ' '.join(x for x in (self.hair_color, self.hairstyle) if x)
        parts = [
            self.age,
            hair + ' hair' if hair else '',
            self.eye_color + ' eyes' if self.eye_color else '',
            self.clothing,
            self.accessories,
            self.body_proportions,
            self.description,
        ]
        return ', '.join(p.strip() for p in parts if p and p.strip())


class DialogueLine(BaseModel):
    speaker: str = ''
    text: Dict[str, str] = Field(default_factory=dict)  # language code -> text


class Scene(BaseModel):
    scene_id: str
    duration: float = Field(5.0, ge=1.0, le=8.0)
    location: str = ''
    characters: List[str] = Field(default_factory=list)
    character_actions: str = ''
    facial_expression: str = ''
    dialogue: List[DialogueLine] = Field(default_factory=list)
    camera_angle: str = 'medium shot'
    camera_movement: str = 'static'
    motion: List[str] = Field(default_factory=list)
    lighting: str = ''
    environment: str = ''
    visual_style: str = 'anime'
    mood: str = ''
    negative_prompt: str = ''
    image_prompt: str = ''
    video_prompt: str = ''
    keyframe: Optional[str] = None
    clip: Optional[str] = None


class ProjectInput(BaseModel):
    description: str
    character: CharacterProfile = Field(default_factory=CharacterProfile)
    environment: str = ''
    dialogue: str = ''
    dialogue_language: Lang = 'en'
    duration: float = Field(5.0, ge=1, le=60)
    aspect_ratio: AspectRatio = '16:9'
    camera_movement: str = 'slow_push'
    animation_style: str = 'modern anime, cel shading'
    mood: str = ''
    lighting: str = ''
    shot_type: str = 'medium shot'
    motion: List[str] = Field(default_factory=list)


class Plan(BaseModel):
    project_id: str = ''
    input: ProjectInput
    character: CharacterProfile
    scenes: List[Scene]
    planner: str = 'heuristic'
    warnings: List[str] = Field(default_factory=list)


class KeyframeJobRequest(BaseModel):
    provider: str = 'comfyui-sdxl'
    seed: Optional[int] = None
    use_reference: bool = True


class VideoJobRequest(BaseModel):
    provider: str = 'comfyui-ltx'
    fps: int = Field(24, ge=8, le=60)
    seed: Optional[int] = None
    resolution: Optional[List[int]] = None  # [width, height], multiples of 32


class SubtitleOptions(BaseModel):
    language: Lang = 'en'
    font: str = 'Arial'
    size: int = Field(48, ge=10, le=200)
    position: Literal['top', 'middle', 'bottom'] = 'bottom'
    outline: float = Field(2.0, ge=0, le=10)
    margin_v: int = Field(40, ge=0, le=400)
    offset: float = Field(0.0, ge=-10, le=10)
    burn_in: bool = True


class AssembleJobRequest(BaseModel):
    aspect_ratio: Optional[AspectRatio] = None
    fps: int = Field(24, ge=8, le=60)
    interpolate_fps: Optional[int] = Field(None, ge=24, le=120)
    denoise: bool = False
    subtitles: Optional[SubtitleOptions] = None
