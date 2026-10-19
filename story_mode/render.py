import math, os, subprocess, wave
import numpy as np
from PIL import Image
from bg import get_bg
from lipsync import envelope
from puppet import Character, W as CW, H as CH
from rig import Rig
from tts import synth, read_wav, SR
from story_parser import DEFAULT_VOICE

GAP = 0.35  # pause after each line (seconds)


def _srt_time(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s % 1) * 1000):03}"


def build(story, out_dir, size=(1280, 720), fps=24, fetch_bg=True, log=print):
    os.makedirs(out_dir, exist_ok=True)
    chars = {n: Character(n, p) for n, p in story.characters.items()}
    rigs = {n: Rig(seed=i + 1) for i, n in enumerate(chars)}

    # 1) voices
    segs = []
    audio_parts, srt, t0 = [], [], 0.0
    for si, sc in enumerate(story.scenes):
        for li, ln in enumerate(sc.lines):
            wav = f"{out_dir}/voice_{si:02d}_{li:02d}.wav"
            voice = story.characters[ln.speaker].get("voice", DEFAULT_VOICE)
            engine = synth(ln.text, voice, wav)
            x = read_wav(wav)
            dur = len(x) / SR + GAP
            n = int(math.ceil(dur * fps))
            x = np.concatenate([x, np.zeros(int(n / fps * SR) - len(x), dtype=np.float32)])
            segs.append(dict(scene=si, speaker=ln.speaker, frames=n, env=envelope(x, SR, fps, n)))
            audio_parts.append(x)
            srt.append((t0, t0 + dur - GAP, ln.text))
            t0 += n / fps
        log(f"voices: scene {si + 1}/{len(story.scenes)} ({engine})")
    full = np.concatenate(audio_parts)
    wav_path = f"{out_dir}/narration.wav"
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((full * 32767).astype(np.int16).tobytes())
    with open(f"{out_dir}/{story.title}.srt", "w", encoding="utf-8") as f:
        for i, (a, b, tx) in enumerate(srt, 1):
            f.write(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{tx}\n\n")

    # 2) backgrounds (oversized for camera moves)
    big = (int(size[0] * 1.15), int(size[1] * 1.15))
    bgs = [get_bg(sc.bg, big, f"{out_dir}/cache", fetch_bg) for sc in story.scenes]

    # 3) which characters appear in each scene + layout
    scale = 0.88 * size[1] / CH
    cw, ch = int(CW * scale), int(CH * scale)
    cast = []
    for sc in story.scenes:
        names = [story.storyteller] if story.storyteller in {l.speaker for l in sc.lines} or not sc.lines else []
        for l in sc.lines:
            if l.speaker not in names:
                names.append(l.speaker)
        if not names:
            names = [story.storyteller]
        n = len(names)
        xs = [int(size[0] * (i + 1) / (n + 1) - cw / 2) for i in range(n)]
        cast.append(dict(zip(names, xs)))

    # 4) frames -> ffmpeg
    video = f"{out_dir}/{story.title}.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-",
         "-i", wav_path, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", video],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    dt = 1.0 / fps
    prev = None
    scene_frames = {}
    for sg in segs:
        scene_frames[sg["scene"]] = scene_frames.get(sg["scene"], 0) + sg["frames"]
    scene_idx = {k: 0 for k in scene_frames}
    total = sum(s["frames"] for s in segs)
    done = 0
    for sg in segs:
        si = sg["scene"]
        for f in range(sg["frames"]):
            k = scene_idx[si] / max(1, scene_frames[si])   # progress through scene 0..1
            # slow ease-in-out zoom + drift (alternates direction per scene)
            e = 0.5 - 0.5 * math.cos(math.pi * k)
            z = 1.0 + 0.08 * (e if si % 2 == 0 else 1 - e)
            bw, bh = bgs[si].size
            vw, vh = bw / 1.15 / z, bh / 1.15 / z
            ox = (bw - vw) / 2 + (e - 0.5) * (bw - vw) * 0.6 * (1 if si % 2 == 0 else -1)
            oy = (bh - vh) / 2
            frame = bgs[si].resize(size, Image.BILINEAR, box=(ox, oy, ox + vw, oy + vh)).convert("RGBA")
            for name, x in cast[si].items():
                speaking = name == sg["speaker"]
                st = rigs[name].update(dt, float(sg["env"][f]) if speaking else 0.0, speaking)
                im = chars[name].render(st).resize((cw, ch), Image.BILINEAR)
                frame.alpha_composite(im, (x, size[1] - ch + int(0.04 * ch)))
            rgb = frame.convert("RGB")
            if f < 8 and prev is not None and scene_idx[si] == f:  # crossfade into new scene
                rgb = Image.blend(prev, rgb, (f + 1) / 9)
            ff.stdin.write(rgb.tobytes())
            prev = rgb
            scene_idx[si] += 1
            done += 1
        log(f"render {done}/{total} frames")
    ff.stdin.close(); ff.wait()
    return video
