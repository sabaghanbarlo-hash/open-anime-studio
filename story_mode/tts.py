"""Free text-to-speech. Uses edge-tts when installed (pip install edge-tts, needs internet);
falls back to espeak-ng, then to synthetic babble so the pipeline can still be tested offline."""
import asyncio, os, shutil, subprocess, wave
import numpy as np

SR = 24000


def _to_wav(src, dst):
    subprocess.run(["ffmpeg", "-y", "-i", src, "-ar", str(SR), "-ac", "1", dst], check=True, capture_output=True)


def _babble(text, dst):
    """Offline stand-in: syllable-rate amplitude-modulated noise, ~0.075s per character."""
    rng = np.random.default_rng(len(text))
    dur = max(0.8, len(text) * 0.065)
    t = np.arange(int(dur * SR)) / SR
    env = np.abs(np.sin(np.pi * t * rng.uniform(3.5, 4.5))) ** 1.5
    env *= (np.sin(2 * np.pi * t * 0.7 + 1) > -0.8)
    sig = (np.sin(2 * np.pi * 140 * t) + 0.4 * rng.standard_normal(len(t))) * env * 0.4
    with wave.open(dst, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((sig * 32767).astype(np.int16).tobytes())


def synth(text, voice, dst, rate="+0%"):
    try:
        import edge_tts
        mp3 = dst + ".mp3"
        asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(mp3))
        _to_wav(mp3, dst); os.remove(mp3)
        return "edge-tts"
    except Exception:
        pass
    if shutil.which("espeak-ng"):
        tmp = dst + ".esp.wav"
        subprocess.run(["espeak-ng", "-w", tmp, text], check=True, capture_output=True)
        _to_wav(tmp, dst); os.remove(tmp)
        return "espeak-ng"
    _babble(text, dst)
    return "babble (install edge-tts for real voices)"


def read_wav(path):
    with wave.open(path, "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
