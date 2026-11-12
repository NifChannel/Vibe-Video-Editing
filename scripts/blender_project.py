"""Run inside Blender: --background --python-exit-code 1 --python this.py -- ..."""
from pathlib import Path
from fractions import Fraction
import argparse, json, math, os, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import load_manifest, read_json, prepare_output, write_json
import bpy

def strips(editor):
    return editor.strips if hasattr(editor,"strips") else editor.sequences

def duration(strip,n):
    if hasattr(strip,"duration"): strip.duration=n
    else: strip.frame_final_duration=n

def relative(path,base):
    try: return "//"+Path(os.path.relpath(path,base)).as_posix()
    except ValueError: return str(Path(path).resolve())

def create(a):
    d=load_manifest(a.manifest); config=read_json(a.config)
    paths=[c["path"] for c in d["clips"]]+list(d["audio"].values())+[a.manifest,a.config]
    if a.base: paths+=[a.base]
    dest=prepare_output(a.output,a.overwrite,paths)
    if a.base: bpy.ops.wm.open_mainfile(filepath=str(Path(a.base).resolve()))
    else: bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.data.scenes.new(a.scene)
    if bpy.context.window: bpy.context.window.scene=s
    s.render.resolution_x=d["width"]; s.render.resolution_y=d["height"]; s.render.resolution_percentage=100
    rate=Fraction(str(d["fps"])); s.render.fps=math.ceil(float(rate)); s.render.fps_base=s.render.fps/float(rate)
    s.frame_start=1; s.frame_end=d["total_frames"]; s.render.use_sequencer=True
    s.view_settings.view_transform="Standard"; s["video_editing_manifest_version"]=1
    st=strips(s.sequence_editor_create())
    for c in d["clips"]:
        v=st.new_movie(c.get("name",Path(c["path"]).stem),c["path"],channel=5,frame_start=c["start_frame"]+1)
        duration(v,c["frames"]); v.filepath=relative(c["path"],dest.parent)
    for key,ch in (("mix",1),("voice",2),("music",3),("sfx",4)):
        if not d["audio"].get(key): continue
        v=st.new_sound(key,d["audio"][key],channel=ch,frame_start=1)
        v.mute=key!="mix"; duration(v,min(d["total_frames"],v.duration if hasattr(v,"duration") else v.frame_final_duration))
        v.sound.filepath=relative(d["audio"][key],dest.parent)
    if d.get("subtitles"):
        if config["subtitles"]["mode"]=="none": raise ValueError("Config disables subtitles")
        if not a.font or not Path(a.font).is_file(): raise FileNotFoundError("Pass --font with a CJK-capable font")
        font=bpy.data.fonts.load(str(Path(a.font).resolve())); font.pack()
        ss=config["subtitles"]; scale=d["height"]/config["video"]["height"]
        for i,c in enumerate(d["subtitles"]):
            start=round(c["start"]*float(rate))+1
            end=max(start+1,round(c["end"]*float(rate))+1)
            end=min(end,s.frame_end+1)
            try: v=st.new_effect(f"字幕 {i+1:03}",type="TEXT",channel=7,frame_start=start,length=end-start)
            except TypeError: v=st.new_effect(f"字幕 {i+1:03}",type="TEXT",channel=7,frame_start=start,frame_end=end)
            v.text=c["text"]; v.font=font; v.font_size=ss["font_size"]*scale
            color=ss["color"].lstrip("#"); v.color=tuple(int(color[j:j+2],16)/255 for j in (0,2,4))+(1,)
            v.location=(.5,ss["margin_v"]/config["video"]["height"])
            v.alignment_x="CENTER"
            if hasattr(v,"anchor_x"): v.anchor_x="CENTER"; v.anchor_y="BOTTOM"
            v.use_shadow=True; v.shadow_color=(.005,.008,.015,1)
            if hasattr(v,"use_outline"): v.use_outline=True
            if hasattr(v,"outline_width"): v.outline_width=.025
    for c in d.get("chapters",[]): s.timeline_markers.new(c["name"],frame=c["frame"]+1)
    s.frame_set(min(30,s.frame_end))
    if hasattr(s.render.image_settings,"media_type"): s.render.image_settings.media_type="VIDEO"
    s.render.image_settings.file_format="FFMPEG"
    s.render.ffmpeg.format="MPEG4"; s.render.ffmpeg.codec="H264"; s.render.ffmpeg.audio_codec="AAC"
    s.render.filepath=relative(dest.with_suffix(".mp4"),dest.parent)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D": area.type="SEQUENCE_EDITOR"
    bpy.ops.wm.save_as_mainfile(filepath=str(dest))
    return dict(project=str(dest),frames=s.frame_end,shots=len(d["clips"]),captions=len(d.get("subtitles",[])))

def verify(a):
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.verify).resolve()))
    s=bpy.data.scenes.get(a.scene)
    if not s: raise ValueError(f"Scene not found: {a.scene}")
    if bpy.context.window: bpy.context.window.scene=s
    missing=[]; video=[]; sounds=[]; texts=[]
    for v in strips(s.sequence_editor):
        if v.type=="MOVIE":
            p=Path(bpy.path.abspath(v.filepath))
            if not p.is_file(): missing.append(str(p))
            video.append(dict(start=v.frame_final_start,end=v.frame_final_end,name=v.name))
        elif v.type=="SOUND":
            p=Path(bpy.path.abspath(v.sound.filepath))
            if not p.is_file(): missing.append(str(p))
            sounds.append(dict(name=v.name,mute=v.mute))
        elif v.type=="TEXT": texts.append(v.text)
    report=dict(frames=s.frame_end,missing=missing,shots=len(video),captions=len(texts),sounds=sounds,
                scenes=[x.name for x in bpy.data.scenes],preview=None)
    if a.manifest:
        d=load_manifest(a.manifest)
        if s.frame_end!=d["total_frames"] or len(video)!=len(d["clips"]):
            raise ValueError("Project timeline differs from manifest")
        if len(texts)!=len(d.get("subtitles",[])): raise ValueError("Caption count mismatch")
        for actual,c in zip(video,d["clips"]):
            if (actual["start"],actual["end"])!=(c["start_frame"]+1,c["start_frame"]+c["frames"]+1):
                raise ValueError("Strip boundaries mismatch")
    if a.preview and not missing:
        preview=prepare_output(a.preview,a.overwrite,[a.verify])
        if hasattr(s.render.image_settings,"media_type"): s.render.image_settings.media_type="IMAGE"
        s.render.image_settings.file_format="PNG"; s.render.filepath=str(preview)
        s.frame_set(max(1,min(a.frame,s.frame_end)))
        bpy.ops.render.render(write_still=True,scene=s.name); report["preview"]=str(preview)
    if a.report: write_json(a.report,report)
    if missing: raise FileNotFoundError(missing)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest"); p.add_argument("--config"); p.add_argument("--output"); p.add_argument("--font")
    p.add_argument("--base"); p.add_argument("--scene",default="Video_Edit")
    p.add_argument("--verify"); p.add_argument("--preview"); p.add_argument("--frame",type=int,default=30)
    p.add_argument("--report"); p.add_argument("--overwrite",action="store_true")
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    a=p.parse_args(argv)
    if not a.verify and not all((a.manifest,a.config,a.output)): p.error("create needs --manifest --config --output")
    report=verify(a) if a.verify else create(a)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
