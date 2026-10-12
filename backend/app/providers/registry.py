from __future__ import annotations

from typing import Dict

from .base import ImageProvider, VideoProvider
from .image_comfyui import ComfyImageProvider
from .video_comfyui import ComfyVideoProvider
from .video_kenburns import KenBurnsProvider

# To add a model or backend: implement ImageProvider / VideoProvider and register it here.
# The frontend discovers providers through GET /capabilities, so it needs no changes.
IMAGE_PROVIDERS: Dict[str, ImageProvider] = {p.id: p for p in [ComfyImageProvider()]}

VIDEO_PROVIDERS: Dict[str, VideoProvider] = {
    p.id: p
    for p in [
        ComfyVideoProvider(
            'comfyui-ltx',
            'ComfyUI - LTX-Video image-to-video',
            'video_ltx.json',
            8,
            'Check the license on the LTX-Video model card for the exact version you download.',
            'Export an LTX image-to-video workflow in API format, replace values with placeholders, see backend/workflows/README.md.',
        ),
        ComfyVideoProvider(
            'comfyui-wan22',
            'ComfyUI - Wan 2.2 image-to-video',
            'video_wan22.json',
            4,
            'Wan 2.2 is published with open weights; verify the license on the model card you download.',
            'Export a Wan 2.2 image-to-video workflow in API format, replace values with placeholders, see backend/workflows/README.md.',
        ),
        KenBurnsProvider(),
    ]
}
