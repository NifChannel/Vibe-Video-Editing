"""List/resolve/register styles without loading every detailed reference."""
from pathlib import Path
import argparse, copy, json, math, re, shutil, tempfile
from common import read_json, write_json, fps_value

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT
CATALOG = ROOT / "风格清单.json"
REQUIRED = {"schema_version","video","rhythm","transitions","subtitles","music",
            "sound_effects","voice","export","tools","extensions"}

def number(x, low=None, high=None):
    if type(x) not in (int,float) or not math.isfinite(x): raise ValueError("Finite number required")
    if low is not None and x < low or high is not None and x > high:
        raise ValueError(f"Number outside {low}..{high}")

def validate_config(d):
    if d.keys() - REQUIRED - {"_selection"}: raise ValueError("Unknown config keys; use extensions for custom parameters")
    if REQUIRED - d.keys(): raise ValueError(f"Missing fields: {sorted(REQUIRED-d.keys())}")
    if d["schema_version"] != 1: raise ValueError("Unsupported config schema_version")
    for key in ("width","height"):
        v=d["video"][key]
        if type(v) is not int or v <= 0 or v%2: raise ValueError(f"Invalid video.{key}")
    fps_value(d["video"]["fps"])
    for k in ("shot_seconds","intro_shot_seconds","hold_shot_seconds"):
        a=d["rhythm"][k]
        if not isinstance(a,list) or len(a)!=2: raise ValueError(f"{k}: expected [min,max]")
        number(a[0],0.01); number(a[1],a[0])
    number(d["rhythm"]["voice_speed"],0.5,2)
    for key in ("transitions","sound_effects"):
        if d[key]["density"] not in ("none","low","medium","high"):
            raise ValueError(f"Invalid {key}.density")
    number(d["transitions"]["duration_seconds"],0)
    if d["subtitles"]["mode"] not in ("none","full"): raise ValueError("Invalid subtitles.mode")
    for k in ("font_size","margin_h","margin_v","outline"): number(d["subtitles"][k],0)
    if not re.fullmatch("#[0-9a-fA-F]{6}",d["subtitles"]["color"]): raise ValueError("Invalid subtitle color")
    if type(d["subtitles"]["bold"]) is not bool or type(d["music"]["ducking"]) is not bool:
        raise ValueError("Boolean required")
    number(d["music"]["target_lufs"],-70,0)
    number(d["voice"]["duration_factor"],0.1,3)
    number(d["export"]["target_lufs"],-70,-5)
    number(d["export"]["true_peak_dbtp"],-9,0)
    number(d["export"]["loudness_range"],1,50)
    if not isinstance(d["extensions"],dict): raise ValueError("extensions must be an object")
    return d

def merge(base, override, prefix=""):
    out=copy.deepcopy(base)
    for k,v in override.items():
        if k not in out and not prefix.startswith("extensions"):
            raise ValueError(f"Unknown override: {prefix}{k}")
        if isinstance(v,dict) and isinstance(out.get(k),dict):
            out[k]=merge(out[k],v,prefix+k+".")
        else: out[k]=copy.deepcopy(v)
    return out

def entries():
    from library import sync
    return sync()['styles']

def refpath(relative):
    p=(REF/relative).resolve()
    if not p.is_relative_to(REF.resolve()) or not p.is_file(): raise ValueError(f"Invalid reference: {relative}")
    return p

def find(name, rows=None):
    matches=[x for x in (rows if rows is not None else entries())
             if name.casefold() in {s.casefold() for s in [x["id"],x["name"],*x["aliases"]]}]
    if len(matches)!=1: raise ValueError(f"Unknown/ambiguous style: {name}; run list")
    return matches[0]

def clean(data):
    return {k:v for k,v in data.items() if k != "_selection"}

def validate_catalog():
    names=set()
    for x in entries():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",x["id"]) or len(x["id"])>63:
            raise ValueError("Invalid style id")
        for name in {s.casefold() for s in [x["id"],x["name"],*x["aliases"]]}:
            if name in names: raise ValueError(f"Duplicate name/alias: {name}")
            names.add(name)
        refpath(x["reference"])
        validate_config(read_json(refpath(x["config"])))
    return len(entries())

def register(args):
    from library import validate_meta, save, load, sync
    rows=entries()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",args.id) or len(args.id)>63:
        raise ValueError("Use a lowercase hyphenated id up to 63 characters")
    cfg=validate_config(clean(read_json(args.config)))
    spec=Path(args.spec).read_text(encoding="utf-8-sig")
    if len(spec.strip())<80: raise ValueError("Provide a substantive style specification")
    existing=[x for x in rows if x["id"]==args.id]
    if existing and not args.replace: raise FileExistsError("Style exists; --replace explicitly updates it")
    aliases=args.alias or []
    wanted={s.casefold() for s in [args.id,args.name,*aliases]}
    for x in rows:
        if x["id"]!=args.id and wanted & {s.casefold() for s in [x["id"],x["name"],*x["aliases"]]}:
            raise ValueError(f"Alias collision with {x['id']}")
    meta=dict(id=args.id,name=args.name,aliases=aliases,cues=args.cues or args.name,
              description=args.description or f"使用{args.name}风格制作或修改视频；适用于明确点名、复用或比较该风格的任务。{args.cues or ''}")
    validate_meta(meta,args.id)
    # Each saved style is a real child Skill; do not append to the parent entrypoint.
    body=re.sub(r'\A---\s*\n.*?\n---\s*\n', '', spec, count=1, flags=re.S)
    spec=(f"---\nname: video-style-{args.id}\ndescription: "+json.dumps(meta['description'],ensure_ascii=False)+
          '\n---\n\n执行前读取父技能 [vibe-video-editing](../../SKILL.md) 的共用约定；本次明确要求优先。默认参数见 [style.json](style.json)。\n\n'+body.rstrip()+'\n')
    dest=ROOT/'Styles'/args.id
    if existing:
        old=load('styles',args.id)
        save('styles',args.id,meta,spec,cfg,old['revision'])
    else:
        if dest.exists(): raise FileExistsError('Unregistered module folder already exists')
        with tempfile.TemporaryDirectory(prefix='.register-',dir=ROOT/'Styles') as temporary:
            staged=Path(temporary)/args.id; staged.mkdir()
            write_json(staged/'module.json',meta)
            write_json(staged/'style.json',cfg)
            (staged/'SKILL.md').write_text(spec,encoding='utf-8')
            staged.rename(dest)
        try: sync()
        except Exception:
            shutil.rmtree(dest)
            raise
    print(json.dumps(find(args.id),ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("list"); v=sub.add_parser("validate"); v.add_argument("--config")
    r=sub.add_parser("resolve"); r.add_argument("--style",required=True); r.add_argument("--overrides")
    r.add_argument("--output")
    r=sub.add_parser("register"); r.add_argument("--id",required=True); r.add_argument("--name",required=True)
    r.add_argument("--alias",action="append"); r.add_argument("--cues"); r.add_argument("--spec",required=True)
    r.add_argument("--config",required=True); r.add_argument("--replace",action="store_true"); r.add_argument("--description")
    a=p.parse_args()
    if a.command=="list":
        print(json.dumps([{k:x[k] for k in ("id","name","aliases","cues")} for x in entries()],ensure_ascii=False,indent=2))
    elif a.command=="validate":
        if a.config:
            validate_config(read_json(a.config)); print("Project config valid")
        else: print(f"{validate_catalog()} styles valid")
    elif a.command=="register": register(a)
    else:
        x=find(a.style); d=read_json(refpath(x["config"])); override=read_json(a.overrides) if a.overrides else {}
        d=validate_config(merge(d,override))
        d["_selection"]=dict(id=x["id"],name=x["name"],reference=str(refpath(x["reference"])),overrides=override)
        if a.output: write_json(a.output,d)
        else: print(json.dumps(d,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
