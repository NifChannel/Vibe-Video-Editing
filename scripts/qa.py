"""Observable delivery checks: full decode, actual frames, captions, A/V length and loudness."""
from pathlib import Path
import argparse, json, math, re
from fractions import Fraction
from common import load_manifest, inspect_clips, probe, ff, binary, run, read_json, write_json
from ffmpeg_ops import loudness

def check(manifest, video, config=None, frames_dir=None):
    d=load_manifest(manifest); errors=[]; warnings=[]
    try: inspect_clips(d)
    except (ValueError,FileNotFoundError) as e: errors.append(str(e))
    p=probe(video); vs=[s for s in p["streams"] if s["codec_type"]=="video"]
    aa=[s for s in p["streams"] if s["codec_type"]=="audio"]
    if len(vs)!=1 or len(aa)!=1: errors.append("Expected one video and one audio stream")
    v=vs[0] if vs else {}; a=aa[0] if aa else {}
    if (v.get("width"),v.get("height"))!=(d["width"],d["height"]): errors.append("Resolution mismatch")
    if Fraction(v.get("r_frame_rate","0/1"))!=Fraction(str(d["fps"])): errors.append("FPS mismatch")
    count=run([binary("ffprobe"),"-v","error","-count_frames","-select_streams","v:0",
               "-show_entries","stream=nb_read_frames","-of","csv=p=0",str(Path(video).resolve())],capture_output=True)
    actual=int(count.stdout.strip())
    if actual!=d["total_frames"]: errors.append(f"Frames {actual} != {d['total_frames']}")
    tolerance=max(.05,1/float(Fraction(str(d["fps"]))))
    for name,stream in (("video",v),("audio",a)):
        if "duration" not in stream: warnings.append(f"{name} duration unavailable")
        elif abs(float(stream["duration"])-d["duration"])>tolerance: errors.append(f"{name} duration mismatch")
    ff(["-v","error","-xerror","-i",str(Path(video).resolve()),"-f","null","-"],capture_output=True)
    ex=(config or {}).get("export",{})
    stats=loudness(video,ex.get("target_lufs",-16),ex.get("true_peak_dbtp",-1.5),ex.get("loudness_range",8))
    integrated=float(stats["input_i"]); peak=float(stats["input_tp"])
    if not math.isfinite(integrated) or abs(integrated-ex.get("target_lufs",-16))>1:
        errors.append("Integrated loudness differs from target by more than 1 LU")
    if not math.isfinite(peak) or peak>ex.get("true_peak_dbtp",-1.5)+.15:
        errors.append("True peak exceeds target (including 0.15 dB measurement tolerance)")
    previews=[]
    if frames_dir:
        folder=Path(frames_dir); folder.mkdir(parents=True,exist_ok=True)
        rate=float(Fraction(str(d["fps"])))
        for i,c in enumerate(d["clips"]):
            t=(c["start_frame"]+min(c["frames"]//2,round(rate*2)))/rate
            out=folder/f"shot_{i:03}.png"
            ff(["-y","-ss",str(t),"-i",str(Path(video).resolve()),"-frames:v","1",
                "-vf","scale=640:-2",str(out.resolve())],capture_output=True)
            previews.append(str(out.resolve()))
    return dict(passed=not errors,errors=errors,warnings=warnings,full_decode="passed",
                frames=actual,expected_frames=d["total_frames"],duration=d["duration"],
                subtitle_bounds="passed",loudness=stats,previews=previews,
                remaining_review="Inspect frames, Chinese glyphs, safe areas and listen to edits; machine checks do not establish aesthetic quality.")

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("manifest")
    p.add_argument("--video",required=True); p.add_argument("--config"); p.add_argument("--report",required=True)
    p.add_argument("--frames-dir"); a=p.parse_args()
    try: report=check(a.manifest,a.video,read_json(a.config) if a.config else None,a.frames_dir)
    except Exception as e:
        report=dict(passed=False,errors=[f"{type(e).__name__}: {e}"],full_decode="not confirmed")
    write_json(a.report,report); print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report["passed"]: raise SystemExit(1)

if __name__=="__main__": main()
