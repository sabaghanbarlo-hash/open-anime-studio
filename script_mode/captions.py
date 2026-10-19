"""Render the rounded caption pill (with furigana) as a transparent PNG."""
import re
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]


def _font(size):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _segments(jp):
    """'彼女[かのじょ]は' -> [('彼女','かのじょ'),('は','')]"""
    out, pos = [], 0
    for m in re.finditer(r"([^\[\]]+?)\[([^\]]*)\]", jp):
        pre = jp[pos:m.start()]
        if pre:
            out.append((pre, ""))
        out.append((m.group(1), m.group(2)))
        pos = m.end()
    if jp[pos:]:
        out.append((jp[pos:], ""))
    return out


def render_caption(scene, path, size=(1920, 1080)):
    W, H = size
    big, ruby_f, small = _font(70), _font(28), _font(60)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    segs = _segments(scene.jp)
    tail = ""
    if scene.romaji:
        tail += f" ({scene.romaji})"
    if scene.en:
        tail += f" = {scene.en}"

    jp_w = sum(d.textlength(t, font=big) for t, _ in segs)
    tail_w = d.textlength(tail, font=small)
    total = jp_w + tail_w
    pad_x, pad_y = 40, 22
    box_w, box_h = total + pad_x * 2, 150
    x0 = (W - box_w) / 2
    y0 = H - 200
    d.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=36, fill=(255, 255, 255, 190))

    x, base_y = x0 + pad_x, y0 + 52
    for text, ruby in segs:
        w = d.textlength(text, font=big)
        if ruby:
            rw = d.textlength(ruby, font=ruby_f)
            d.text((x + (w - rw) / 2, y0 + 12), ruby, font=ruby_f, fill=(40, 40, 40, 255))
        d.text((x, base_y), text, font=big, fill=(40, 40, 40, 255))
        x += w
    d.text((x, base_y + 8), tail, font=small, fill=(40, 40, 40, 255))
    img.save(path)
    return path
