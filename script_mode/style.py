"""Visual style preset matching the sample: clean 2D anime/cartoon lesson look."""

STYLE_PREFIX = (
    "flat 2D anime-style illustration, clean dark outlines, soft cel shading, "
    "warm natural skin tones, friendly expressive faces, simple clothes, "
    "plain light grey gradient background with a faint sparkle in the lower right, "
    "no text, no watermark, 16:9"
)
NEGATIVE = "text, letters, watermark, extra fingers, deformed hands, photorealistic, 3d render, blurry"


def build_prompt(scene, characters: dict) -> str:
    chars = [f"{n}: {d}" for n, d in characters.items() if n.lower() in scene.visual.lower()]
    char_part = ("Characters (keep identical across scenes) - " + "; ".join(chars) + ". ") if chars else ""
    return f"{STYLE_PREFIX}. {char_part}{scene.visual}"
