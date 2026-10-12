import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
DATA_DIR = Path(os.getenv('OAS_DATA_DIR', str(ROOT / 'data'))).resolve()
PROJECTS_DIR = DATA_DIR / 'projects'
WORKFLOW_DIR = ROOT / 'workflows'
FONTS_DIR = ROOT / 'fonts'
DOCS_DIR = REPO_ROOT / 'docs'

COMFY_URL = os.getenv('OAS_COMFY_URL', 'http://127.0.0.1:8188')
OLLAMA_URL = os.getenv('OAS_OLLAMA_URL', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.getenv('OAS_OLLAMA_MODEL', 'qwen2.5:7b-instruct')
SDXL_CHECKPOINT = os.getenv('OAS_SDXL_CHECKPOINT', '')
FFMPEG = os.getenv('OAS_FFMPEG', 'ffmpeg')
FFPROBE = os.getenv('OAS_FFPROBE', 'ffprobe')
# Comma separated list of allowed browser origins. '*' is fine for a backend on localhost;
# restrict it (e.g. https://YOURNAME.github.io) if you expose the backend on a network.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv('OAS_ALLOWED_ORIGINS', '*').split(',') if o.strip()]

# All sizes are multiples of 32 so common video models accept them.
KEYFRAME_SIZES = {'16:9': (1344, 768), '9:16': (768, 1344), '1:1': (1024, 1024)}
CLIP_SIZES = {'16:9': (832, 480), '9:16': (480, 832), '1:1': (640, 640)}
FINAL_SIZES = {'16:9': (1280, 720), '9:16': (720, 1280), '1:1': (960, 960)}
