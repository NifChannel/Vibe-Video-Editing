"""Write synchronized SRT/ASS from the shared frame manifest."""
from pathlib import Path
import argparse
from common import load_manifest, read_json, prepare_output

def ts(t, ass=False):
    n=round(t*(100 if ass else 1000))
    if ass: return f"{n//360000}:{n//6000%60:02}:{n//100%60:02}.{n%100:02}"
    return f"{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}"

def outputs(d, config, srt, ass, overwrite=False):
    style=config["subtitles"]
    if style["mode"]=="none" and d.get("subtitles"):
        raise ValueError("Config disables subtitles; clear captions or explicitly override mode")
    captions=d.get("subtitles",[])
    paths=[c["path"] for c in d["clips"]]+list(d["audio"].values())
    srt=prepare_output(srt,overwrite,paths); ass=prepare_output(ass,overwrite,paths+[srt])
    color=style["color"].lstrip("#")
    ass_color="&H00"+color[4:6]+color[2:4]+color[0:2]
    sx=d["width"]/config["video"]["width"]; sy=d["height"]/config["video"]["height"]
    size=style["font_size"]*sy; mh=round(style["margin_h"]*sx); mv=round(style["margin_v"]*sy)
    header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: {d['width']}
PlayResY: {d['height']}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{style['font_family']},{size},{ass_color},{ass_color},&H00150C07,&H00000000,{-1 if style['bold'] else 0},0,0,0,100,100,0,0,1,{style['outline']*sy},0,2,{mh},{mh},{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    srt_text=[]; ass_text=[header]
    for i,c in enumerate(captions):
        srt_text.append(f"{i+1}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n")
        text=c["text"].replace("\\",r"\\").replace("{",r"\{").replace("}",r"\}").replace("\n",r"\N")
        ass_text.append(f"Dialogue: 0,{ts(c['start'],True)},{ts(c['end'],True)},Main,,0,0,0,,{text}\n")
    srt.write_text("\n".join(srt_text),encoding="utf-8")
    ass.write_text("".join(ass_text),encoding="utf-8")

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("manifest")
    p.add_argument("--config",required=True); p.add_argument("--srt",required=True); p.add_argument("--ass",required=True)
    p.add_argument("--overwrite",action="store_true"); a=p.parse_args()
    outputs(load_manifest(a.manifest),read_json(a.config),a.srt,a.ass,a.overwrite)
    print("SRT/ASS written")

if __name__=="__main__": main()
