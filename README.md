# Open Anime Studio

A free, open-source anime video generator. **No paid APIs, no API keys.** It turns a description into a structured scene plan, makes anime keyframes, animates them with an open-weights image-to-video model, adds subtitles (Japanese, English, Persian) and assembles an MP4.

> **Status: v0.1 scaffold, written in one pass and not yet run end-to-end.** The architecture and code are real (no fake buttons), but expect to fix small things on first run, and you must set up the models yourself. See the status table below. Please open issues for anything that breaks.

## The three layers

```
  Browser (GitHub Pages or /ui)         Local / your GPU server                  Optional
  +---------------------------+  HTTP   +--------------------------------+      +------------------+
  | docs/  static HTML + JS   | ------> | backend/  FastAPI job server   | ---> | remote backend   |
  | forms, scene editor,      |         |  - planner  -> Ollama (LLM)    |      | you run elsewhere|
  | previews, subtitle opts   |         |  - keyframe -> ComfyUI (SDXL)  |      | (same API, just  |
  +---------------------------+         |  - clip     -> ComfyUI (LTX/Wan)|     | a different URL) |
   Cannot run models.                   |  - assemble -> FFmpeg          |      +------------------+
   Only talks to the Backend URL.       +--------------------------------+
```

- **Frontend / GitHub hosting:** `docs/` is plain static files. GitHub Pages serves it. It performs **no** generation.
- **Local AI inference:** the `backend/` server plus ComfyUI and (optionally) Ollama on your GPU machine.
- **Optional external inference:** run the same backend on any server you control and change the *Backend URL* in the UI. Nothing in this repo calls a paid generation service.

## What is implemented

| Feature | Status |
|---|---|
| Structured scene plan (all fields in the spec) | Implemented. Ollama JSON planner, rule-based fallback |
| Reusable character profile | Implemented (profile text injected in every scene prompt) |
| Keyframes | Included ComfyUI SDXL workflow; **you set `OAS_SDXL_CHECKPOINT`** |
| Reference images for consistency | Experimental IP-Adapter template, untested |
| Image-to-video (LTX-Video, Wan 2.2) | Provider code done; **you export the ComfyUI workflow** (`backend/workflows/README.md`) |
| Camera / character motion | Sent as prompt text to AI models (soft control). Exact only for the FFmpeg provider |
| Subtitles ja/en/fa, font, position, size, outline, timing | Implemented (ASS + SRT, libass burn-in) |
| MP4 assembly 16:9, 9:16, 1:1 | Implemented (FFmpeg) |
| Per-scene preview before assembly | Implemented |
| Denoise, frame interpolation | Implemented with classical FFmpeg filters (`hqdn3d`, `minterpolate`), not AI |
| AI upscaling, RIFE | **Not implemented** |
| Audio (voice, music, ambience, SFX) | **Interface only** (`AudioProvider`); output is silent |
| Temporal consistency | Limited: shared character prompt, reference images, image-to-video conditioning |

The UI shows this same table from `GET /capabilities`.

## Quick start

Requirements: Python 3.10+, FFmpeg (with libass) on PATH, [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running, optionally [Ollama](https://ollama.com).

```bash
git clone https://github.com/sabaghanbarlo-hash/open-anime-studio
cd open-anime-studio/backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv/Scripts/activate
pip install -r requirements.txt

export OAS_SDXL_CHECKPOINT='your-anime-sdxl.safetensors'   # file in ComfyUI/models/checkpoints
export OAS_COMFY_URL='http://127.0.0.1:8188'
export OAS_OLLAMA_MODEL='qwen2.5:7b-instruct'               # optional: ollama pull qwen2.5:7b-instruct
uvicorn app.main:app --port 8000
```

Then open **http://127.0.0.1:8000/ui/** (the backend serves the frontend too) and press *Connect*.

### Using the GitHub Pages frontend

In the repo settings enable **Pages** from branch `main`, folder `/docs`. Open the Pages URL, set Backend URL to `http://127.0.0.1:8000` and press Connect. Chromium browsers and Firefox allow an https page to call `localhost`; Safari blocks it, so use the `/ui/` address above there. If you expose the backend beyond localhost, set `OAS_ALLOWED_ORIGINS=https://YOURNAME.github.io` and put it behind your own authentication.

### Persian and Japanese subtitles

Put a font file with Arabic script (for example Vazirmatn, SIL OFL) into `backend/fonts/` and enter its family name in the UI. Japanese needs a CJK font (for example Noto Sans JP). Subtitle text comes from the dialogue boxes; the rule-based planner cannot translate, so either fill the languages yourself or run Ollama (a 7B model's Persian is rough, so proofread).

## Models and licenses

Check the model card of every file you download; terms differ by version and can change.

| Role | Suggested | Notes |
|---|---|---|
| Image-to-video | Wan 2.2 (ComfyUI template) | Open weights from Alibaba. Large VRAM needs; the smaller 5B variant targets about 24 GB at 720p per upstream docs |
| Image-to-video | LTX-Video (ComfyUI template) | Lighter on VRAM; verify the license of your exact version |
| Keyframes | Any SDXL anime checkpoint | Licenses vary a lot (some forbid commercial use). Read yours |
| Planner LLM | `qwen2.5:7b-instruct` via Ollama | Any Ollama model works through `OAS_OLLAMA_MODEL` |

## Adding a model or backend

Providers live in `backend/app/providers/` and are registered in `registry.py`. The frontend discovers them from `/capabilities`, so it never needs rebuilding.

```python
class MyVideoProvider(VideoProvider):
    id = 'my-model'
    name = 'My model'
    async def generate(self, req: VideoRequest) -> GenResult:
        # req.image, req.prompt, req.duration, req.fps, req.resolution, req.camera_motion
        ...
```

`VideoRequest` is the Python form of `VideoProvider.generate({image, prompt, duration, fps, resolution, cameraMotion})`.

## Testing the pipeline without a video model

The `kenburns` provider animates a keyframe with a real FFmpeg camera move (it is **not** AI). It lets you test planning, keyframes, subtitles and assembly before the Wan/LTX workflows are set up. Keyframes still need ComfyUI.

## Repo layout

```
docs/       static frontend (GitHub Pages)
backend/    FastAPI server, providers, planner, subtitles, assembly
  app/providers/    image, video and LLM providers (swap here)
  workflows/        ComfyUI API-format templates and instructions
```

## Known limits

- AI clips are a few seconds long; longer videos are chained scenes. Characters can still drift between scenes.
- Jobs run one at a time (one GPU), state is kept on disk under `backend/data/`.
- No authentication: do not expose the backend to the internet as is.

Licensed under Apache-2.0 (see `LICENSE`).
