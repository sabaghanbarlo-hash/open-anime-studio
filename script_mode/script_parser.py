"""Parse a pasted lesson script into scenes.

Line format (one scene per line):
    JP | romaji | English | visual description | [seconds]

Furigana: write 漢字[かんじ] and it renders as ruby text above the kanji.
Lines starting with '#' are comments. Lines starting with '@character' define a
character once so the look stays consistent:
    @character Haru | young man, short black hair, white t-shirt

Free text (no '|') becomes a caption-less scene, one per paragraph.
"""
from dataclasses import dataclass, field
import re


@dataclass
class Scene:
    index: int
    jp: str = ""
    romaji: str = ""
    en: str = ""
    visual: str = ""
    seconds: float = 3.0

    @property
    def has_caption(self) -> bool:
        return bool(self.jp or self.en)


@dataclass
class Script:
    title: str = "lesson"
    characters: dict = field(default_factory=dict)
    scenes: list = field(default_factory=list)


def parse(text: str) -> Script:
    script = Script()
    blocks = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.lower().startswith("# title:"):
                script.title = line.split(":", 1)[1].strip()
            continue
        if line.lower().startswith("@character"):
            body = line[len("@character"):].strip()
            name, _, desc = body.partition("|")
            script.characters[name.strip()] = desc.strip()
            continue
        blocks.append(line)

    for line in blocks:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 1:
            script.scenes.append(Scene(len(script.scenes), visual=parts[0]))
            continue
        parts += [""] * (5 - len(parts))
        jp, romaji, en, visual, secs = parts[:5]
        try:
            seconds = float(secs) if secs else 3.0
        except ValueError:
            seconds = 3.0
        script.scenes.append(Scene(len(script.scenes), jp, romaji, en, visual, seconds))
    return script


def strip_furigana(s: str) -> str:
    return re.sub(r"\[[^\]]*\]", "", s)
