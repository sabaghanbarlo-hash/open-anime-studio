"""Parse a storytelling script.

    # title: The Fox and the Moon
    @character Fox | skin=#f4c29a, hair=#c8642a, shirt=#2a9d8f, style=short, voice=en-US-GuyNeural
    @character Mia | skin=#e8b896, hair=#2b1d2e, shirt=#e76f51, style=long, voice=en-US-JennyNeural
    [bg: moonlit forest clearing, anime background, soft glow]
    Once upon a time, a little fox lived at the edge of the forest.   <- storyteller (first character)
    Mia: "Have you ever tried to catch the moon?"                      <- named speaker
    [bg: a quiet village at dawn]
    ...

A [bg: ...] line starts a new scene. Lines without "Name:" are spoken by the
storyteller (the first @character). Quotation marks around dialogue are stripped.
"""
import re
from dataclasses import dataclass, field

DEFAULT_VOICE = "en-US-AriaNeural"


@dataclass
class Line:
    speaker: str
    text: str


@dataclass
class Scene:
    bg: str
    lines: list = field(default_factory=list)


@dataclass
class Story:
    title: str = "story"
    characters: dict = field(default_factory=dict)  # name -> dict of params
    scenes: list = field(default_factory=list)
    storyteller: str = "Storyteller"


def _params(s):
    out = {}
    for kv in s.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse(text):
    st = Story()
    scene = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.lower().startswith("# title:"):
                st.title = re.sub(r"[^\w\- ]", "", line.split(":", 1)[1]).strip().replace(" ", "_") or "story"
            continue
        if line.lower().startswith("@character"):
            name, _, rest = line[len("@character"):].partition("|")
            st.characters[name.strip()] = _params(rest)
            if len(st.characters) == 1:
                st.storyteller = name.strip()
            continue
        m = re.match(r"^\[bg:\s*(.*)\]$", line, re.I)
        if m:
            scene = Scene(m.group(1))
            st.scenes.append(scene)
            continue
        if scene is None:
            scene = Scene("soft pastel anime background")
            st.scenes.append(scene)
        m = re.match(r"^([A-Za-z][\w ]{0,20}):\s*(.+)$", line)
        if m and m.group(1).strip() in st.characters:
            speaker, body = m.group(1).strip(), m.group(2)
        else:
            speaker, body = st.storyteller, line
        body = body.strip().strip('"\u201c\u201d')
        scene.lines.append(Line(speaker, body))
    if st.storyteller not in st.characters:
        st.characters[st.storyteller] = {"voice": DEFAULT_VOICE}
    for sc in st.scenes:
        for ln in sc.lines:
            st.characters.setdefault(ln.speaker, {})
    return st
