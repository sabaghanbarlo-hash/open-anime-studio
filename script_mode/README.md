# Script Mode

Paste a script, get a short anime-style lesson video like the Japanese vocab sample:
flat 2D characters on a soft grey background, a rounded caption pill with furigana
(`かのじょ (Kanojo) = She`), gentle zoom, MP4 output.

## Script format

```
# title: my_lesson
@character Haru | young man, short black hair, white t-shirt
JP | romaji | English | what the scene shows | seconds
彼女[かのじょ] | Kanojo | She | Haru gestures toward Mio | 3
```

`漢字[ふりがな]` renders ruby text above the kanji. `@character` lines keep designs consistent in every prompt.

## Run

```
pip install pillow  # plus ffmpeg on PATH
python run.py sample_script.txt --out out                 # placeholder frames, tests the pipeline
python run.py my.txt --keyframes ./frames --aspect 9:16    # real frames named scene_01.png ...
```

`out/scenes.json` holds one image prompt per scene (style preset + character bible) to feed your local image model (ComfyUI / SD / Flux). Each scene is animated with a gentle zoom; swap in an image-to-video provider (Wan 2.2, LTX-Video) by adding a class in `providers.py`.
