"""Procedural anime-style half-body character (flat colours, clean outlines).
Swap this class for PNG-layer art later; the Rig drives either."""
from PIL import Image, ImageDraw
import math

SS = 2           # supersampling for smooth edges
W, H = 520, 760  # character canvas (final pixels)
HEAD_H = 640
PIVOT = (260, 450)
OUT = (45, 35, 40, 255)


def _hex(c, default):
    if not c:
        return default
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


class Character:
    def __init__(self, name, params):
        self.name = name
        self.skin = _hex(params.get("skin"), (246, 211, 182, 255))
        self.hair = _hex(params.get("hair"), (40, 32, 44, 255))
        self.shirt = _hex(params.get("shirt"), (236, 236, 240, 255))
        self.style = params.get("style", "short")
        self.shade = tuple(max(0, int(c * 0.88)) for c in self.skin[:3]) + (255,)
        self._body = self._draw_body()
        self._arms, self._heads = {}, {}

    @staticmethod
    def _s(v):
        if isinstance(v, (list, tuple)):
            return [tuple(c * SS for c in x) for x in v] if v and isinstance(v[0], (list, tuple)) else [x * SS for x in v]
        return v * SS

    def _canvas(self, w, h):
        im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        return im, ImageDraw.Draw(im)

    def _limb(self, d, pts, width, color):
        pts = [(x * SS, y * SS) for x, y in pts]
        d.line(pts, fill=color, width=int(width * SS), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = width * SS / 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)

    def _draw_body(self):
        im, d = self._canvas(W, H)
        s = self._s
        # arms hanging (viewer's left arm always; right arm drawn per frame)
        self._limb(d, [(115, 500), (95, 640), (105, 745)], 70, self.shirt)
        d.ellipse(s([75, 725, 135, 785]), fill=self.skin)
        # neck + torso
        d.rectangle(s([232, 380, 288, 470]), fill=self.shade)
        d.polygon([(x * SS, y * SS) for x, y in [(95, 490), (150, 455), (260, 475), (370, 455), (425, 490), (450, 760), (70, 760)]], fill=self.shirt, outline=OUT)
        d.arc(s([215, 440, 305, 500]), 20, 160, fill=OUT, width=3 * SS)
        return im.resize((W, H), Image.LANCZOS)

    def _arm(self, g, style):
        """Right arm (viewer's right). g=0 rest, g=1 raised gesture."""
        im, d = self._canvas(W, H)
        sh = (405, 500)
        rest = [(425, 640), (415, 745)]
        up = [(470 - 40 * style, 590), (400 - 60 * style, 470 + 30 * style)]
        pts = [sh] + [(rest[i][0] + (up[i][0] - rest[i][0]) * g, rest[i][1] + (up[i][1] - rest[i][1]) * g) for i in range(2)]
        self._limb(d, pts, 70, self.shirt)
        hx, hy = pts[-1]
        d.ellipse(self._s([hx - 32, hy - 32, hx + 32, hy + 32]), fill=self.skin)
        return im.resize((W, H), Image.LANCZOS)

    def _head(self, st):
        im, d = self._canvas(W, HEAD_H)
        s = self._s
        cx, cy = 260, 292
        if self.style == "long":
            d.rounded_rectangle(s([105, 160, 415, 560]), radius=120 * SS, fill=self.hair, outline=OUT, width=3 * SS)
        # face
        d.ellipse(s([cx - 135, cy - 140, cx + 135, cy + 150]), fill=self.skin, outline=OUT, width=3 * SS)
        d.ellipse(s([cx - 150, cy - 10, cx - 125, cy + 50]), fill=self.skin, outline=OUT, width=3 * SS)  # ears
        d.ellipse(s([cx + 125, cy - 10, cx + 150, cy + 50]), fill=self.skin, outline=OUT, width=3 * SS)
        # hair front
        d.pieslice(s([cx - 150, cy - 175, cx + 150, cy + 60]), 180, 360, fill=self.hair, outline=OUT, width=3 * SS)
        d.polygon(s([(cx - 140, cy - 60), (cx - 60, cy - 20), (cx - 20, cy - 95), (cx + 20, cy - 25), (cx + 70, cy - 90), (cx + 140, cy - 60), (cx + 100, cy - 140), (cx - 100, cy - 140)]), fill=self.hair)
        # eyes
        lk = st["look"] * 7
        for ex in (cx - 62, cx + 62):
            top = cy + 20 - 38 * (1 - st["blink"])
            if st["blink"] > 0.85:
                d.arc(s([ex - 30, cy + 10, ex + 30, cy + 40]), 10, 170, fill=OUT, width=4 * SS)
            else:
                ry = 38 * (1 - 0.85 * st["blink"])
                d.ellipse(s([ex - 30, cy + 20 - ry, ex + 30, cy + 20 + ry]), fill=(255, 255, 255, 255), outline=OUT, width=3 * SS)
                d.ellipse(s([ex - 19 + lk, cy + 20 - ry * 0.7, ex + 19 + lk, cy + 20 + ry * 0.75]), fill=(52, 40, 48, 255))
                d.ellipse(s([ex - 8 + lk, cy + 20 - ry * 0.5, ex + 4 + lk, cy + 20 - ry * 0.5 + 14]), fill=(255, 255, 255, 255))
        # brows
        by = cy - 30 - 12 * st["brow"]
        for ex, sg in ((cx - 62, -1), (cx + 62, 1)):
            d.line(s([(ex - 28, by + 4 * sg * 0 + 5), (ex, by - 4 + 6 * st["brow"] * sg * 0), (ex + 28, by + 6)]), fill=self.hair if self.style != "long" else OUT, width=6 * SS)
        # blush + nose
        for bx in (cx - 85, cx + 85):
            d.ellipse(s([bx - 24, cy + 62, bx + 24, cy + 88]), fill=(240, 150, 150, 110))
        d.line(s([(cx, cy + 62), (cx - 5, cy + 78), (cx + 3, cy + 80)]), fill=OUT, width=3 * SS)
        # mouth: height follows lip-sync continuously
        m = st["mouth"]
        my = cy + 108
        if m < 0.07:
            d.arc(s([cx - 22, my - 14, cx + 22, my + 12]), 15, 165, fill=OUT, width=4 * SS)
        else:
            rx, ry = 14 + 12 * m, 4 + 32 * m
            d.ellipse(s([cx - rx, my - ry * 0.4, cx + rx, my + ry]), fill=(120, 42, 52, 255), outline=OUT, width=3 * SS)
            if m > 0.4:
                d.ellipse(s([cx - rx * 0.6, my + ry * 0.35, cx + rx * 0.6, my + ry * 0.95]), fill=(235, 120, 130, 255))
        return im.resize((W, HEAD_H), Image.LANCZOS)

    def render(self, st):
        """Returns RGBA (W,H) for the given animation state. Face/arm layers are cached on
        quantised values (imperceptible steps) so long videos render quickly."""
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bob = int(2 * st["breath"] + st["nod"] * 0.4)
        out.alpha_composite(self._body, (0, bob // 2))
        ak = (round(st["gest"] * 24), round(st["gstyle"] * 4))
        if ak not in self._arms:
            self._arms[ak] = self._arm(ak[0] / 24, ak[1] / 4)
        out.alpha_composite(self._arms[ak], (0, bob // 2))
        q = dict(st, mouth=round(st["mouth"] * 16) / 16, blink=round(st["blink"] * 6) / 6,
                 brow=round(st["brow"] * 4) / 4, look=round(st["look"] * 4) / 4)
        hk = (q["mouth"], q["blink"], q["brow"], q["look"])
        if hk not in self._heads:
            self._heads[hk] = self._head(q)
        head = self._heads[hk]
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        full.paste(head, (0, 0))
        full = full.rotate(st["tilt"], center=PIVOT, resample=Image.BICUBIC)
        out.alpha_composite(full, (0, bob))
        return out
