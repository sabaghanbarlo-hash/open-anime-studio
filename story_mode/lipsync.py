"""Audio envelope -> per-frame mouth energy (0..1), no external tools."""
import numpy as np


def envelope(samples, sr, fps, total_frames):
    hop = sr / fps
    win = int(hop * 1.5)
    env = np.zeros(total_frames, dtype=np.float32)
    for i in range(total_frames):
        a = int(i * hop)
        seg = samples[a:a + win]
        env[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0
    ref = np.percentile(env[env > 0], 92) if np.any(env > 0) else 1.0
    env = np.clip(env / max(ref, 1e-6), 0, 1.2)
    env = np.clip(env, 0, 1) ** 0.75
    env[env < 0.05] = 0.0
    return env
