"""Shared frame timeline and process helpers. No project-specific paths."""
from pathlib import Path
from fractions import Fraction
import json, math, os, shutil, subprocess

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write_json(path, data):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def binary(name):
    env = {"ffmpeg":"FFMPEG_BIN", "ffprobe":"FFPROBE_BIN",
           "blender":"BLENDER_BIN"}.get(name)
    value = os.environ.get(env, "") if env else ""
    if not value and env:
        from runtime_config import load
        value = load().get(name)
    found = value or shutil.which(name)
    if not found or not Path(found).is_file():
        raise FileNotFoundError(f"{name} unavailable; set {env or 'PATH'}")
    return str(Path(found).resolve())

def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, encoding="utf-8",
                          errors="replace", **kwargs)

def ff(args, **kwargs):
    return run([binary("ffmpeg"), "-hide_banner", "-nostdin", *args], **kwargs)

def probe(path):
    return json.loads(run([binary("ffprobe"), "-v", "error", "-show_format",
        "-show_streams", "-of", "json", Path(path).resolve()], capture_output=True).stdout)

def fps_value(value):
    f = Fraction(str(value)).limit_denominator(100000)
    if f <= 0 or f > 240: raise ValueError("fps must be in (0, 240]")
    return f

def prepare_output(path, overwrite=False, inputs=()):
    p = Path(path).resolve()
    if any(p == Path(x).resolve() for x in inputs):
        raise ValueError("Output would overwrite an input")
    if p.exists() and not overwrite: raise FileExistsError(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def asset(base, value):
    p = Path(value)
    p = p if p.is_absolute() else base / p
    p = p.resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    return p

def load_manifest(path):
    p = Path(path).resolve(); d = read_json(p); base = p.parent
    if d.get("schema_version") != 1: raise ValueError("manifest schema_version must be 1")
    fps = fps_value(d["fps"])
    for key in ("width","height"):
        if type(d[key]) is not int or d[key] <= 0 or d[key] % 2:
            raise ValueError(f"{key} must be a positive even integer")
    if not d.get("clips"): raise ValueError("At least one rendered clip required")
    frame = 0
    for c in d["clips"]:
        if type(c.get("frames")) is not int or c["frames"] <= 0:
            raise ValueError("clip.frames must be a positive integer")
        c["path"] = str(asset(base, c["path"]))
        c["start_frame"] = frame
        frame += c["frames"]
    d["total_frames"] = frame; d["duration"] = float(frame / fps)
    d["fps_num"] = fps.numerator; d["fps_den"] = fps.denominator
    d["audio"] = {k:str(asset(base,v)) for k,v in d.get("audio",{}).items() if v}
    if not d["audio"].get("mix"): raise ValueError("audio.mix required")
    subtitles = d.get("subtitles", [])
    last = 0.
    for i,s in enumerate(subtitles):
        a,b = s["start"],s["end"]
        if not all(type(t) in (int,float) and math.isfinite(t) for t in (a,b)):
            raise ValueError(f"Non-finite subtitle {i}")
        if not (0 <= a < b <= d["duration"] + 0.000001) or a < last - 0.000001:
            raise ValueError(f"Subtitle bounds/overlap at {i}")
        if not isinstance(s.get("text"),str) or not s["text"].strip():
            raise ValueError(f"Empty subtitle {i}")
        last = b
    if subtitles and any(c.get("captions_baked",False) for c in d["clips"]):
        raise ValueError("Text subtitles would duplicate baked captions")
    last_chapter=-1
    for c in d.get("chapters",[]):
        if type(c.get("frame")) is not int or not 0 <= c["frame"] < frame:
            raise ValueError("chapter.frame out of range")
        if c["frame"] <= last_chapter or not isinstance(c.get("name"),str) or not c["name"].strip():
            raise ValueError("Chapters must have names and strictly increasing frames")
        last_chapter=c["frame"]
    return d

def inspect_clips(d):
    """Check actual video streams before concat/editor export."""
    signatures=[]; errors=[]
    fps = fps_value(d["fps"])
    for i,c in enumerate(d["clips"]):
        p=probe(c["path"]); streams=[s for s in p["streams"] if s["codec_type"]=="video"]
        if len(streams)!=1: errors.append(f"clip {i}: expected one video stream"); continue
        v=streams[0]
        if (v["width"],v["height"])!=(d["width"],d["height"]):
            errors.append(f"clip {i}: resolution mismatch")
        if fps_value(v["r_frame_rate"]) != fps: errors.append(f"clip {i}: fps mismatch")
        if "nb_frames" in v:
            if int(v["nb_frames"]) != c["frames"]: errors.append(f"clip {i}: frame count mismatch")
        else:
            count=run([binary("ffprobe"),"-v","error","-count_frames","-select_streams","v:0",
                       "-show_entries","stream=nb_read_frames","-of","csv=p=0",c["path"]],capture_output=True)
            if int(count.stdout.strip())!=c["frames"]: errors.append(f"clip {i}: decoded frame count mismatch")
        signatures.append(tuple(v.get(k) for k in
            ("codec_name","profile","pix_fmt","width","height","r_frame_rate","time_base")))
    if errors: raise ValueError("; ".join(errors))
    return signatures
