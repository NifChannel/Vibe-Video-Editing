"""Portable FFmpeg operations. Writes are explicit; existing outputs need --overwrite."""
from pathlib import Path
from fractions import Fraction
import argparse, json, math, os, re, shutil, tempfile
from common import (binary, ff, probe, read_json, write_json, fps_value,
                    prepare_output, load_manifest, inspect_clips)

def loudness(path, target=-16, peak=-1.5, lra=8):
    r=ff(["-nostats","-i",str(Path(path).resolve()),"-vn","-af",
          f"loudnorm=I={target}:TP={peak}:LRA={lra}:print_format=json","-f","null","-"],
         capture_output=True)
    found=re.findall(r'\{\s*"input_i".*?\}',r.stderr,re.S)
    if not found: raise RuntimeError("No loudnorm measurement returned")
    return json.loads(found[-1])

def normalize(source, output, target=-16, peak=-1.5, lra=8, overwrite=False):
    dest=prepare_output(output,overwrite,[source])
    stats=loudness(source,target,peak,lra)
    if any(not math.isfinite(float(stats[k])) for k in ("input_i","input_tp","input_lra","input_thresh","target_offset")):
        raise ValueError("Cannot master silent/non-finite input; inspect the audio")
    filt=(f"loudnorm=I={target}:TP={peak}:LRA={lra}:"
          f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
          f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
          f"offset={stats['target_offset']}:linear=true,aresample=48000")
    ff(["-y" if overwrite else "-n","-i",str(Path(source).resolve()),"-vn","-af",filt,
        "-ar","48000","-ac","2","-c:a","pcm_s24le",str(dest)],capture_output=True)
    return stats

def render_clip(a):
    cfg=read_json(a.config) if a.config else {}
    v=cfg.get("video",{})
    width=a.width or v.get("width",1920); height=a.height or v.get("height",1080)
    fps=fps_value(a.fps or v.get("fps",30))
    if width%2 or height%2 or min(width,height)<=0: raise ValueError("Positive even dimensions required")
    n=a.frames if a.frames is not None else round(a.duration*fps)
    if n<=0 or a.start<0 or not 0.5<=a.speed<=2: raise ValueError("Invalid clip range/speed")
    source=Path(a.input).resolve()
    dest=prepare_output(a.output,a.overwrite,[source])
    with tempfile.TemporaryDirectory(prefix="video-edit-") as td:
        filters=[f"setpts=(PTS-STARTPTS)/{a.speed}"]
        if a.stabilize:
            ff(["-y","-ss",str(a.start),"-i",str(source),"-t",str(float(n/fps)*a.speed),"-an",
                "-vf","vidstabdetect=shakiness=4:accuracy=9:result=motion.trf",
                "-f","null","-"],cwd=td,capture_output=True)
            filters.append("vidstabtransform=input=motion.trf:smoothing=6:maxshift=22:maxangle=0.025:optzoom=1")
        if a.fit=="cover":
            filters.extend([f"scale={width}:{height}:force_original_aspect_ratio=increase",
                            f"crop={width}:{height}"])
        else:
            filters.extend([f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"])
        if a.filter: filters.append(a.filter)
        filters.extend(["setsar=1",f"fps={fps}",f"trim=end_frame={n}",f"setpts=N/({fps}*TB)","format=yuv420p"])
        temp=Path(td)/"render.mp4"
        ff(["-y","-ss",str(a.start),"-i",str(source),"-vf",",".join(filters),
            "-frames:v",str(n),"-an","-c:v","libx264","-preset","medium","-crf",str(a.crf),
            "-pix_fmt","yuv420p","-r",str(fps),"-movflags","+faststart",str(temp)],
           cwd=td,capture_output=True)
        vp=next(s for s in probe(temp)["streams"] if s["codec_type"]=="video")
        if int(vp.get("nb_frames",-1))!=n: raise ValueError("Source too short for requested frame count")
        shutil.copyfile(temp,dest)
    return dict(output=str(dest),frames=n,seconds=float(n/fps))

def mix(a):
    cfg=read_json(a.config) if a.config else {}
    mus=cfg.get("music",{}); ex=cfg.get("export",{})
    duration=a.duration
    if duration<=0: raise ValueError("duration must be positive")
    sources=[a.voice]+[x for x in (a.music,a.sfx) if x]
    dest=prepare_output(a.output,a.overwrite,sources)
    target=a.target if a.target is not None else ex.get("target_lufs",-16)
    peak=a.peak if a.peak is not None else ex.get("true_peak_dbtp",-1.5)
    music_level=a.music_lufs if a.music_lufs is not None else mus.get("target_lufs",-25)
    duck=not a.no_duck and mus.get("ducking",True)
    inputs=["-i",str(Path(a.voice).resolve())]
    f=[f"[0:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration},asetpts=PTS-STARTPTS[v]"]
    labels=["[v]"]; idx=1
    if a.music:
        inputs+=["-stream_loop","-1","-i",str(Path(a.music).resolve())]
        fade=min(3.,duration/3)
        f.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS,"
                 f"loudnorm=I={music_level}:TP=-3:LRA=8,aresample=48000,"
                 f"afade=t=in:d={min(.6,duration/3)},afade=t=out:st={duration-fade}:d={fade}[m]")
        if duck:
            f[0]=f[0].replace("[v]","[v0]")
            f+=["[v0]asplit=2[v][side]","[m][side]sidechaincompress=threshold=0.035:ratio=4:attack=18:release=450[duck]"]
            labels+=["[duck]"]
        else: labels+=["[m]"]
        idx+=1
    if a.sfx:
        inputs+=["-i",str(Path(a.sfx).resolve())]
        f.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration},asetpts=PTS-STARTPTS[fx]")
        labels+=["[fx]"]
    f.append("".join(labels)+f"amix=inputs={len(labels)}:normalize=0:duration=longest,atrim=duration={duration}[mix]")
    with tempfile.TemporaryDirectory(prefix="video-mix-") as td:
        raw=Path(td)/"unmastered.wav"
        ff(["-y",*inputs,"-filter_complex",";".join(f),"-map","[mix]","-ar","48000",
            "-ac","2","-c:a","pcm_s24le",str(raw)],capture_output=True)
        stats=normalize(raw,dest,target,peak,ex.get("loudness_range",8),a.overwrite)
    return dict(output=str(dest),pass1=stats)

def export(d, output, ass=None, overwrite=False):
    signatures=inspect_clips(d)
    if len(set(signatures))!=1:
        raise ValueError("Normalize rendered clips to matching codec/profile/pix_fmt/fps/time_base first")
    if ass and any(c.get("captions_baked",False) for c in d["clips"]):
        raise ValueError("Refusing a second layer of burned captions")
    inputs=[c["path"] for c in d["clips"]]+list(d["audio"].values())+([ass] if ass else [])
    dest=prepare_output(output,overwrite,inputs)
    with tempfile.TemporaryDirectory(prefix="video-export-") as td:
        td=Path(td)
        # Safe ASCII staging names avoid concat-list quoting failures on Windows/Unicode paths.
        lines=[]
        for i,c in enumerate(d["clips"]):
            p=td/f"clip_{i:04}.mp4"
            try: os.link(c["path"],p)
            except OSError: shutil.copyfile(c["path"],p)
            lines.append(f"file '{p.name}'")
        (td/"concat.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
        picture=td/"picture.mp4"
        ff(["-y","-f","concat","-safe","0","-i","concat.txt","-map","0:v:0",
            "-an","-c:v","copy",str(picture)],cwd=td,capture_output=True)
        vf=[]
        if ass:
            shutil.copyfile(ass,td/"captions.ass"); vf.append("ass=captions.ass")
        args=["-y" if overwrite else "-n","-i",str(picture),"-i",d["audio"]["mix"]]
        if d.get("chapters"):
            lines=[";FFMETADATA1"]
            for i,c in enumerate(d["chapters"]):
                end=d["chapters"][i+1]["frame"] if i+1<len(d["chapters"]) else d["total_frames"]
                title=c["name"].replace("\\","\\\\").replace("\n"," ")
                for char in ("=",";","#"): title=title.replace(char,"\\"+char)
                lines.extend(["[CHAPTER]",f"TIMEBASE={d['fps_den']}/{d['fps_num']}",
                              f"START={c['frame']}",f"END={end}",f"title={title}"])
            meta=td/"chapters.ffmeta"; meta.write_text("\n".join(lines)+"\n",encoding="utf-8")
            args += ["-i",str(meta)]
        args += ["-map","0:v:0","-map","1:a:0"]
        if d.get("chapters"): args += ["-map_metadata","2","-map_chapters","2"]
        if vf: args+=["-vf",",".join(vf)]
        args+=["-frames:v",str(d["total_frames"]),"-t",str(d["duration"]),
               "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
               "-r",str(fps_value(d["fps"])),"-c:a","aac","-b:a","256k","-ar","48000","-ac","2",
               "-movflags","+faststart",str(dest)]
        ff(args,cwd=td,capture_output=True)
    return dict(output=str(dest),frames=d["total_frames"])

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("doctor")
    q=sub.add_parser("probe"); q.add_argument("input")
    q=sub.add_parser("render-clip"); q.add_argument("--input",required=True); q.add_argument("--output",required=True)
    q.add_argument("--start",type=float,default=0); g=q.add_mutually_exclusive_group(required=True)
    g.add_argument("--frames",type=int); g.add_argument("--duration",type=float)
    q.add_argument("--fps"); q.add_argument("--width",type=int); q.add_argument("--height",type=int)
    q.add_argument("--config"); q.add_argument("--speed",type=float,default=1)
    q.add_argument("--fit",choices=["cover","contain"],default="contain")
    q.add_argument("--filter"); q.add_argument("--stabilize",action="store_true"); q.add_argument("--crf",type=int,default=18)
    q.add_argument("--overwrite",action="store_true")
    q=sub.add_parser("mix"); q.add_argument("--voice",required=True); q.add_argument("--music"); q.add_argument("--sfx")
    q.add_argument("--duration",type=float,required=True); q.add_argument("--output",required=True)
    q.add_argument("--config"); q.add_argument("--music-lufs",type=float); q.add_argument("--no-duck",action="store_true")
    q.add_argument("--target",type=float); q.add_argument("--peak",type=float); q.add_argument("--overwrite",action="store_true")
    q=sub.add_parser("normalize"); q.add_argument("--input",required=True); q.add_argument("--output",required=True)
    q.add_argument("--target",type=float,default=-16); q.add_argument("--peak",type=float,default=-1.5)
    q.add_argument("--overwrite",action="store_true")
    q=sub.add_parser("export"); q.add_argument("manifest"); q.add_argument("--output",required=True)
    q.add_argument("--ass"); q.add_argument("--overwrite",action="store_true")
    a=p.parse_args()
    if a.cmd=="doctor":
        result={}
        for name in ("ffmpeg","ffprobe","blender"):
            try: result[name]=binary(name)
            except FileNotFoundError: result[name]=None
    elif a.cmd=="probe": result=probe(a.input)
    elif a.cmd=="render-clip": result=render_clip(a)
    elif a.cmd=="mix": result=mix(a)
    elif a.cmd=="normalize": result=normalize(a.input,a.output,a.target,a.peak,overwrite=a.overwrite)
    else: result=export(load_manifest(a.manifest),a.output,a.ass,a.overwrite)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
