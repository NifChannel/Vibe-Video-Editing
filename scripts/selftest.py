"""Integration smoke tests using tiny synthetic media in a new, isolated directory."""
from pathlib import Path
import argparse, copy, json, os, shutil, subprocess, sys
from common import ff, probe, run, write_json, read_json, load_manifest, binary

SCRIPTS=Path(__file__).resolve().parent
SKILL=SCRIPTS.parent

def cli(script,*args,ok=True):
    r=subprocess.run([sys.executable,str(SCRIPTS/script),*map(str,args)],capture_output=True,
                     text=True,encoding="utf-8",errors="replace",env={**os.environ,'PYTHONUTF8':'1'})
    if (r.returncode==0)!=ok:
        raise RuntimeError(f"{script} exit {r.returncode}\n{r.stdout[-2000:]}\n{r.stderr[-4000:]}")
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--workdir",required=True)
    a=p.parse_args(); w=Path(a.workdir).resolve()
    if w.is_relative_to(SKILL): raise ValueError("Keep verification artifacts outside the Skill folder")
    if w.exists(): raise FileExistsError("Use a new workdir to preserve previous evidence")
    w.mkdir(parents=True); checks=[]
    def passed(name): checks.append(name); print("PASS",name,flush=True)
    try:
        # Resolve and register using an isolated Skill copy, never alter the installed catalog.
        testskill=w/"skill-copy"; shutil.copytree(SKILL,testskill,ignore=shutil.ignore_patterns("__pycache__"))
        st=testskill/"scripts/style.py"
        # A synthetic fixture lives only in the isolated test copy, never in Styles.
        fixture=testskill/'Styles/smoke-baseline'; fixture.mkdir(parents=True)
        fixture_config=dict(schema_version=1,video=dict(width=640,height=360,fps=30),
            rhythm=dict(shot_seconds=[6,10],intro_shot_seconds=[1,2],hold_shot_seconds=[2,4],voice_speed=1),
            transitions=dict(type='cut',density='none',duration_seconds=0),
            subtitles=dict(mode='full',font_family='sans-serif',font_size=22,bold=False,
                           margin_h=24,margin_v=18,outline=1.5,color='#FFFFFF'),
            music=dict(mood='test',target_lufs=-25,ducking=True),sound_effects=dict(density='none'),
            voice=dict(engine='source',voice='source',duration_factor=1),
            export=dict(target_lufs=-16,true_peak_dbtp=-1.5,loudness_range=8),
            tools=dict(editor='ffmpeg'),extensions={})
        write_json(fixture/'style.json',fixture_config)
        write_json(fixture/'module.json',dict(id='smoke-baseline',name='Smoke baseline',
            description='Synthetic test fixture only.',aliases=['smoke-fixture'],cues='test only'))
        (fixture/'SKILL.md').write_text('---\nname: video-style-smoke-baseline\n'
            'description: Synthetic fixture for isolated media checks only.\n---\n\n'
            + 'Use this synthetic configuration only in the isolated smoke test. '*3,encoding='utf-8')
        def style(*args,ok=True):
            r=subprocess.run([sys.executable,str(st),*map(str,args)],capture_output=True,text=True,encoding="utf-8",
                             env={**os.environ,'PYTHONUTF8':'1'})
            if (r.returncode==0)!=ok: raise RuntimeError(r.stdout+r.stderr)
            return r
        override=w/"overrides.json"; config=w/"settings.json"
        write_json(override,dict(video=dict(width=640,height=360),subtitles=dict(font_size=22,margin_h=24,margin_v=18),
                                 rhythm=dict(shot_seconds=[3,5]),transitions=dict(density="medium")))
        style("resolve","--style","smoke-fixture","--overrides",override,"--output",config)
        settings=read_json(config)
        assert settings["rhythm"]["shot_seconds"]==[3,5] and settings["subtitles"]["font_size"]==22
        assert settings["_selection"]["id"]=="smoke-baseline"
        original=read_json(fixture/'style.json')
        assert original["rhythm"]["shot_seconds"]==[6,10]
        write_json(w/"bad-override.json",{"rhythm":{"shot_second":[1,2]}})
        style("resolve","--style","smoke-fixture","--overrides",w/"bad-override.json",ok=False)
        passed("alias routing and override isolation; typo rejected")
        spec=w/"new-style.md"
        spec.write_text("# 新风格验证\n\n"+("保留真实语音，正文硬切，低音效密度，字幕可读，按实际音频定时。"*8),encoding="utf-8")
        style("register","--id","test-maker","--name","测试手作","--alias","手作","--spec",spec,"--config",config)
        style("resolve","--style","手作","--output",w/"new-resolved.json")
        style("register","--id","another","--name","冲突测试","--alias","smoke-fixture","--spec",spec,"--config",config,ok=False)
        style("validate")
        passed("new style registered and resolved; alias collision rejected")
        source=w/"素材 O'Brien.mp4"
        ff(["-y","-f","lavfi","-i","testsrc2=size=800x450:rate=30",
            "-f","lavfi","-i","sine=frequency=440:sample_rate=48000","-t","7",
            "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
            "-c:a","aac","-shortest",str(source)],capture_output=True)
        for i,fit in enumerate(("contain","cover")):
            cli("ffmpeg_ops.py","render-clip","--input",source,"--start",i,
                "--frames",90,"--config",config,"--fit",fit,"--output",w/f"shot{i}.mp4")
        cli("ffmpeg_ops.py","render-clip","--input",source,"--frames",90,"--config",config,
            "--output",w/"shot0.mp4",ok=False)
        cli("ffmpeg_ops.py","render-clip","--input",source,"--frames",400,"--config",config,
            "--output",w/"too-short.mp4",ok=False)
        assert not (w/"too-short.mp4").exists()
        cli("ffmpeg_ops.py","render-clip","--input",source,"--frames",25,"--fps","25",
            "--width",180,"--height",320,"--fit","cover","--output",w/"portrait25.mp4")
        v=next(s for s in probe(w/"portrait25.mp4")["streams"] if s["codec_type"]=="video")
        assert (v["width"],v["height"],v["r_frame_rate"],int(v["nb_frames"]))==(180,320,"25/1",25)
        passed("real trims/contain/cover/portrait25fps; output protection; short input rejected")
        for name,hz in (("voice",330),("music",220),("sfx",880)):
            ff(["-y","-f","lavfi","-i",f"sine=frequency={hz}:sample_rate=48000","-t","6",
                "-ac","2","-c:a","pcm_s16le",str(w/f"{name}.wav")],capture_output=True)
        cli("ffmpeg_ops.py","mix","--voice",w/"voice.wav","--music",w/"music.wav","--sfx",w/"sfx.wav",
            "--duration",6,"--config",config,"--output",w/"mix.wav")
        passed("music ducking, stems and two-pass loudness")
        d=dict(schema_version=1,fps=30,width=640,height=360,
            clips=[dict(path=f"shot{i}.mp4",frames=90,name=f"镜头{i}") for i in range(2)],
            audio={k:k+".wav" for k in ("mix","voice","music","sfx")},
            subtitles=[dict(start=.2,end=2.5,text="中文测试：型号 ≈ 80℃"),
                       dict(start=3.2,end=5.8,text="现场声与配乐，字幕可编辑")],
            chapters=[dict(frame=0,name="开场"),dict(frame=90,name="解释")])
        manifest=w/"manifest.json"; write_json(manifest,d)
        bad=copy.deepcopy(d); bad["subtitles"][1]["start"]=2
        write_json(w/"overlap.json",bad)
        cli("subtitles.py",w/"overlap.json","--config",config,"--srt",w/"bad.srt","--ass",w/"bad.ass",ok=False)
        bad=copy.deepcopy(d); bad["clips"][0]["captions_baked"]=True; write_json(w/"baked.json",bad)
        cli("subtitles.py",w/"baked.json","--config",config,"--srt",w/"bad.srt","--ass",w/"bad.ass",ok=False)
        bad=copy.deepcopy(d); bad["clips"][0]["path"]="missing.mp4"; write_json(w/"missing.json",bad)
        cli("subtitles.py",w/"missing.json","--config",config,"--srt",w/"bad.srt","--ass",w/"bad.ass",ok=False)
        cli("subtitles.py",manifest,"--config",config,"--srt",w/"字幕.srt","--ass",w/"字幕.ass")
        cli("ffmpeg_ops.py","export",manifest,"--ass",w/"字幕.ass","--output",w/"测试成片.mp4")
        ch=json.loads(run([binary("ffprobe"),"-v","error","-show_chapters","-of","json",w/"测试成片.mp4"],capture_output=True).stdout)["chapters"]
        assert len(ch)==2 and [x["tags"]["title"] for x in ch]==["开场","解释"]
        assert abs(float(ch[1]["start_time"])-3)<.001
        cli("qa.py",manifest,"--video",w/"测试成片.mp4","--config",config,
            "--report",w/"qa.json","--frames-dir",w/"frames")
        bad=copy.deepcopy(d); bad["clips"][0]["frames"]+=1; write_json(w/"wrong-frames.json",bad)
        cli("qa.py",w/"wrong-frames.json","--video",w/"测试成片.mp4","--config",config,
            "--report",w/"qa-negative.json",ok=False)
        passed("Chinese SRT/ASS and real MP4 full decode/frames/audio; invalid captions/media/timeline rejected")
        try: blender=binary("blender")
        except FileNotFoundError: blender=None
        from runtime_config import load as runtime_config
        font=runtime_config().get('font_file')
        if not font or not Path(font).is_file(): blender=None
        if blender:
            args=[blender,"--background","--python-exit-code","1","--python",SCRIPTS/"blender_project.py","--"]
            log=run(args+["--manifest",manifest,"--config",config,"--font",font,
                          "--output",w/"工程.blend"],capture_output=True)
            (w/"blender-create.log").write_text(log.stdout+log.stderr,encoding="utf-8")
            log=run(args+["--verify",w/"工程.blend","--manifest",manifest,"--report",w/"blender-check.json",
                          "--preview",w/"blender-preview.png","--frame","35"],capture_output=True)
            (w/"blender-verify.log").write_text(log.stdout+log.stderr,encoding="utf-8")
            report=read_json(w/"blender-check.json")
            assert report["shots"]==2 and report["captions"]==2 and report["frames"]==180
            assert not report["missing"] and sum(not x["mute"] for x in report["sounds"])==1
            # Reopen after the complete delivery directory has been copied to a new location.
            moved=w/"relocated"; moved.mkdir()
            for name in ("工程.blend","shot0.mp4","shot1.mp4","mix.wav","voice.wav","music.wav","sfx.wav"):
                shutil.copyfile(w/name,moved/name)
            log=run(args+["--verify",moved/"工程.blend","--report",moved/"check.json",
                          "--preview",moved/"preview.png","--frame","120"],capture_output=True)
            assert not read_json(moved/"check.json")["missing"]
            passed("Blender build/reopen/render; captions, stems, frame bounds and relocated paths")
        else: print("SKIP Blender runtime not available",flush=True)
        write_json(w/"selftest.json",dict(passed=True,checks=checks,workdir=str(w)))
    except Exception as e:
        write_json(w/"selftest.json",dict(passed=False,checks=checks,error=f"{type(e).__name__}: {e}"))
        raise
    print(json.dumps(dict(passed=True,checks=checks),ensure_ascii=False,indent=2))

if __name__=="__main__": main()
