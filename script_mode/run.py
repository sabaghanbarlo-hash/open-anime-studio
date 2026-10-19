"""Usage: python run.py script.txt [--aspect 16:9] [--keyframes DIR] [--out out/]"""
import argparse, json, os
from script_parser import parse
from style import build_prompt, NEGATIVE
from captions import render_caption
from providers import PlaceholderProvider, FolderProvider
from assemble import scene_clip, concat, ASPECTS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--aspect", default="16:9", choices=ASPECTS)
    ap.add_argument("--keyframes", help="folder of scene_01.png... (skip to use placeholders)")
    ap.add_argument("--audio")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    size = ASPECTS[a.aspect]
    os.makedirs(a.out, exist_ok=True)
    script = parse(open(a.script, encoding="utf-8").read())
    provider = FolderProvider(a.keyframes) if a.keyframes else PlaceholderProvider()

    manifest, clips = [], []
    for i, s in enumerate(script.scenes, 1):
        prompt = build_prompt(s, script.characters)
        manifest.append({"scene": i, "prompt": prompt, "negative": NEGATIVE, "seconds": s.seconds})
        frame = provider.generate(prompt, NEGATIVE, f"{a.out}/scene_{i:02d}.png", size)
        cap = render_caption(s, f"{a.out}/cap_{i:02d}.png", size) if s.has_caption else None
        clip = f"{a.out}/clip_{i:02d}.mp4"
        scene_clip(frame, cap, s.seconds, clip, size, zoom_in=(i % 2 == 1))
        clips.append(clip)
        print(f"scene {i}/{len(script.scenes)} done")

    json.dump(manifest, open(f"{a.out}/scenes.json", "w"), indent=2, ensure_ascii=False)
    final = f"{a.out}/{script.title}.mp4"
    concat(clips, final, a.audio)
    print("wrote", final)


if __name__ == "__main__":
    main()
