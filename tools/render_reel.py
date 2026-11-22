#!/usr/bin/env python3
"""Render a NovelGrooves meme reel (1080x1920) from a JSON spec.

Spec example:
{
  "out": "reel.mp4",
  "hook": "trying to be sad but you share Spotify with your toddler",
  "shots": [
    {"image": "sad.png", "audio": "songA.wav", "start": 127.5, "dur": 14.5,
     "label": "Mira Collins - An Hour of the Night", "motion": "slowzoom"},
    {"image": "sing.png", "audio": "songB.wav", "start": 0.0, "dur": 13.0,
     "label": "De Avonturenband - Floeba Tandenpoetslied", "motion": "bounce", "bpm": 132}
  ]
}
Each shot = one still (later: a generated video clip, key "video") plus an audio
segment. Shots are hard-cut, like a playlist that jumps to the next track.
Hook text sits on top for the whole reel; a small "now playing" label per shot.
"""
import json, os, subprocess, sys, tempfile, textwrap

W, H, FPS = 1080, 1920, 30
FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(r.returncode)


def shot_clip(s, i, tmp, hook_lines):
    dur = float(s["dur"])
    n = int(round(dur * FPS))
    motion = s.get("motion", "slowzoom")
    if motion == "bounce":
        bpm = float(s.get("bpm", 120))
        f = bpm / 60.0
        z = f"1.06+0.025*abs(sin(PI*{f}*on/{FPS}))"
        x = f"iw/2-(iw/zoom/2)+6*sin(2*PI*{f}*on/{FPS})"
        y = f"ih/2-(ih/zoom/2)"
    else:  # slow push-in
        z = f"1.0+0.12*on/{n}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    src = s.get("video")
    if src:
        vin = ["-stream_loop", "-1", "-i", src]
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
    else:
        vin = ["-loop", "1", "-i", s["image"]]
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS}")
    # hook text (top) and now-playing label (bottom)
    draw = []
    ytxt = 150
    for ln in hook_lines:
        draw.append(f"drawtext=fontfile={FONT_BOLD}:text='{esc(ln)}':fontsize=62:fontcolor=white:"
                    f"borderw=6:bordercolor=black@0.85:x=(w-text_w)/2:y={ytxt}")
        ytxt += 82
    if s.get("label"):
        draw.append(f"drawbox=x=60:y={H-300}:w={W-120}:h=110:color=black@0.55:t=fill")
        draw.append(f"drawtext=fontfile={FONT_MED}:text='{esc('Now playing')}':fontsize=30:"
                    f"fontcolor=white@0.75:x=95:y={H-288}")
        draw.append(f"drawtext=fontfile={FONT_BOLD}:text='{esc(s['label'])}':fontsize=40:"
                    f"fontcolor=white:x=95:y={H-245}")
    vf = vf + "," + ",".join(draw) + ",format=yuv420p"
    af = "afade=t=in:st=0:d=0.05"
    if s.get("fadeout"):
        af += f",afade=t=out:st={dur-float(s['fadeout'])}:d={s['fadeout']}"
    out = os.path.join(tmp, f"shot{i}.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", *vin, "-ss", str(s["start"]), "-t", str(dur),
         "-i", s["audio"], "-filter_complex", f"[0:v]{vf}[v];[1:a]{af},aresample=48000,aformat=channel_layouts=stereo[a]",
         "-map", "[v]", "-map", "[a]", "-t", str(dur), "-r", str(FPS), "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k", out])
    return out


def main():
    spec = json.load(open(sys.argv[1]))
    hook_lines = textwrap.wrap(spec.get("hook", ""), 26) if spec.get("hook") else []
    with tempfile.TemporaryDirectory() as tmp:
        parts = [shot_clip(s, i, tmp, hook_lines) for i, s in enumerate(spec["shots"])]
        lst = os.path.join(tmp, "list.txt")
        open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
             "-c", "copy", "-movflags", "+faststart", spec["out"]])
    print(spec["out"])


if __name__ == "__main__":
    main()
