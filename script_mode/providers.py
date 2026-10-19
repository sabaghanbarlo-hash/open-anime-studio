"""Keyframe providers. Plug your free/local image model in by subclassing."""
from PIL import Image, ImageDraw


class KeyframeProvider:
    def generate(self, prompt: str, negative: str, out_path: str, size=(1920, 1080)) -> str:
        raise NotImplementedError


class PlaceholderProvider(KeyframeProvider):
    """Grey card showing the prompt - for testing the pipeline offline."""

    def generate(self, prompt, negative, out_path, size=(1920, 1080)):
        img = Image.new("RGB", size, (200, 205, 212))
        d = ImageDraw.Draw(img)
        d.text((60, 60), prompt[:300], fill=(60, 60, 60))
        img.save(out_path)
        return out_path


class FolderProvider(KeyframeProvider):
    """Use pre-made images: folder/scene_01.png, scene_02.png ... (e.g. from a local
    ComfyUI/Stable Diffusion run using the prompts in scenes.json)."""

    def __init__(self, folder):
        self.folder = folder
        self._n = 0

    def generate(self, prompt, negative, out_path, size=(1920, 1080)):
        self._n += 1
        src = f"{self.folder}/scene_{self._n:02d}.png"
        Image.open(src).convert("RGB").resize(size).save(out_path)
        return out_path
