"""Turn keyframes + captions into an MP4 with gentle camera motion (Ken Burns)."""
import subprocess, os

ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def scene_clip(frame, caption, seconds, out, size, fps=30, zoom_in=True):
    W, H = size
    n = int(seconds * fps)
    z = "min(zoom+0.0007,1.12)" if zoom_in else "if(eq(on,0),1.12,max(zoom-0.0007,1.0))"
    fc = (
        f"[0:v]scale={W*2}:{H*2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={n}:s={W}x{H}:fps={fps}[v];"
    )
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", frame]
    if caption:
        cmd += ["-loop", "1", "-i", caption]
        fc += (
            f"[1:v]scale={W}:{H},format=rgba,fade=in:st=0.3:d=0.3:alpha=1[c];"
            f"[v][c]overlay=0:0:shortest=1,format=yuv420p[out]"
        )
    else:
        fc += "[v]format=yuv420p[out]"
    cmd += ["-filter_complex", fc, "-map", "[out]", "-t", str(seconds), "-r", str(fps),
            "-c:v", "libx264", "-preset", "veryfast", out]
    _run(cmd)


def concat(clips, out, audio=None):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst]
    if audio:
        cmd += ["-i", audio, "-shortest", "-c:a", "aac"]
    cmd += ["-c:v", "copy", out]
    _run(cmd)
