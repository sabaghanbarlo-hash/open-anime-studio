from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class ImageRequest:
    prompt: str
    negative_prompt: str
    width: int
    height: int
    seed: int
    output: Path
    reference_image: Optional[Path] = None


@dataclass
class VideoRequest:
    """Python form of VideoProvider.generate({image, prompt, duration, fps, resolution, cameraMotion})."""

    image: Path
    prompt: str
    negative_prompt: str
    duration: float
    fps: int
    resolution: Tuple[int, int]
    camera_motion: str
    seed: int
    output: Path


@dataclass
class GenResult:
    path: Path
    notes: List[str] = field(default_factory=list)


class Provider(ABC):
    id: str = ''
    name: str = ''
    kind: str = ''
    requires_gpu: bool = True
    license_note: str = ''

    def configured(self) -> Tuple[bool, str]:
        return True, ''

    def info(self) -> dict:
        ok, detail = self.configured()
        return {
            'id': self.id,
            'name': self.name,
            'kind': self.kind,
            'requires_gpu': self.requires_gpu,
            'configured': ok,
            'detail': detail,
            'license_note': self.license_note,
        }


class ImageProvider(Provider):
    kind = 'image'

    @abstractmethod
    async def generate(self, req: ImageRequest) -> GenResult: ...


class VideoProvider(Provider):
    kind = 'video'

    @abstractmethod
    async def generate(self, req: VideoRequest) -> GenResult: ...


class AudioProvider(Provider):
    """Interface only. No audio providers ship in v0.1 (TTS, music, ambience and SFX are future work)."""

    kind = 'audio'
