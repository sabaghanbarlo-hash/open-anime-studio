"""Backgrounds: free Pollinations image API (no key) with a gradient fallback."""
import colorsys, hashlib, io, os, urllib.parse, urllib.request
from PIL import Image


def _gradient(prompt, size):
    h = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16) / 0xFFFFFF
    top = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.35, 0.95)]
    bot = [int(c * 255) for c in colorsys.hsv_to_rgb((h + 0.08) % 1, 0.5, 0.65)]
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(size[1]):
        f = y / size[1]
        col = tuple(int(top[i] * (1 - f) + bot[i] * f) for i in range(3))
        for x in range(size[0]):
            px[x, y] = col
    return img


def get_bg(prompt, size, cache_dir, fetch=True):
    os.makedirs(cache_dir, exist_ok=True)
    key = hashlib.md5(f"{prompt}{size}".encode()).hexdigest()[:10]
    path = f"{cache_dir}/bg_{key}.jpg"
    if os.path.exists(path):
        return Image.open(path).convert("RGB")
    img = None
    if fetch:
        try:
            q = urllib.parse.quote(prompt + ", no people, no text, anime background art, wide shot")
            url = f"https://image.pollinations.ai/prompt/{q}?width={size[0]}&height={size[1]}&nologo=true"
            with urllib.request.urlopen(url, timeout=60) as r:
                img = Image.open(io.BytesIO(r.read())).convert("RGB").resize(size)
        except Exception:
            img = None
    if img is None:
        img = _gradient(prompt, size)
    img.save(path, quality=92)
    return img
