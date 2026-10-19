"""python run.py story.txt [--out out] [--size 1280x720] [--fps 24] [--no-bg-fetch]
Vertical Shorts: --size 1080x1920"""
import argparse
from story_parser import parse
from render import build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", default="out")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--no-bg-fetch", action="store_true", help="skip AI backgrounds, use gradients")
    a = ap.parse_args()
    w, h = map(int, a.size.lower().split("x"))
    story = parse(open(a.script, encoding="utf-8").read())
    print("wrote", build(story, a.out, (w, h), a.fps, not a.no_bg_fetch))


if __name__ == "__main__":
    main()
