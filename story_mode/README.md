# Story Mode - paste a story, get a YouTube video

Free, CPU-only. Needs Python 3, ffmpeg on PATH, and `pip install -r requirements.txt`.

    python run.py sample_story.txt --out out                # 1280x720 YouTube
    python run.py my_story.txt --size 1080x1920             # Shorts / vertical
    python run.py my_story.txt --no-bg-fetch                # gradient backgrounds, no internet for images

Script format: see sample_story.txt. `@character` lines set look + voice, `[bg: ...]` starts a new scene,
plain lines are spoken by the first character (the storyteller), `Name: text` lines by that character.
Output: MP4 with voice, plus an .srt subtitle file.

Voices: edge-tts (free, needs internet). Without it the tool falls back to espeak-ng, then to test babble.
Backgrounds: free Pollinations image API, falling back to gradients.
Motion: mouth follows the audio, random blinks, eased head sway and nods, hand gestures on emphasis.
