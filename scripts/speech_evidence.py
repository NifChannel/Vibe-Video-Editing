"""Measure original audio and list speech/noise candidates; never decide cuts."""
from pathlib import Path
import argparse,json,re,time
import numpy as np
import soundfile as sf
from scipy.fft import rfft,irfft
from scipy.ndimage import binary_closing,binary_dilation


def runs(mask):
    return np.flatnonzero(np.diff(np.r_[False,mask,False].astype(int))).reshape(-1,2)


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio',required=True,type=Path)
    p.add_argument('--transcript',required=True,type=Path)
    p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--rms-threshold-db',type=float,default=-48)
    p.add_argument('--voicing-threshold',type=float,default=.43)
    p.add_argument('--breath-flatness',type=float,default=.12)
    a=p.parse_args();start=time.perf_counter()
    if a.output_dir.exists():raise FileExistsError('Use a new evidence output directory')
    transcript=json.loads(a.transcript.read_text(encoding='utf-8-sig'))
    words=transcript.get('words')
    if words is None:words=[w for s in transcript['segments'] for w in s['words']]
    offset=float(transcript.get('source_offset_seconds',0))
    audio,sr=sf.read(a.audio,dtype='float32')
    if sr!=16000 or audio.ndim!=1:raise ValueError('Use the same fresh mono 16k analysis audio as ASR')
    declared=transcript.get('duration')
    if declared is not None and abs(float(declared)-len(audio)/sr)>.05:
        raise ValueError('Transcript/audio duration mismatch')
    a.output_dir.mkdir(parents=True)
    frame,hop=640,160
    frames=np.lib.stride_tricks.sliding_window_view(np.pad(audio,(0,frame)),frame)[::hop][:int(np.ceil(len(audio)/hop))]
    db=20*np.log10(np.sqrt(np.mean(frames**2,axis=1)+1e-16))
    flat=[];harm=[];high=[];window=np.hanning(frame).astype(np.float32)
    freq=np.fft.rfftfreq(1024,1/sr)
    for i in range(0,len(frames),512):
        power=np.abs(rfft(frames[i:i+512]*window,n=1024,axis=1))**2+1e-12
        flat.extend((np.exp(np.log(power[:,8:400]).mean(1))/power[:,8:400].mean(1)).tolist())
        high.extend((power[:,freq>3500].sum(1)/power.sum(1)).tolist())
        ac=irfft(power,n=1024,axis=1)
        harm.extend((ac[:,40:240].max(1)/(ac[:,0]+1e-12)).tolist())
    flat=np.array(flat);harm=np.array(harm);high=np.array(high)
    tm=offset+np.arange(len(db))*.01+.02
    np.savez_compressed(a.output_dir/'acoustic-features.npz',time=tm,dbfs=db.astype('float32'),
                        harmonic=harm.astype('float32'),flatness=flat.astype('float32'),
                        high_frequency_ratio=high.astype('float32'))
    lexical=np.zeros(len(tm),bool)
    for w in words:
        if not re.fullmatch(r'\[[^]]+\]',w['w'].strip()):lexical|=(tm>=w['s']-.03)&(tm<=w['e']+.03)
    uncovered=binary_closing((~lexical)&(db>a.rms_threshold_db),iterations=3)
    candidates=[]
    for l,r in runs(uncovered):
        if (r-l)*.01<.08:continue
        fraction=float((harm[l:r]>a.voicing_threshold).mean())
        candidates.append({'id':f'sound-{len(candidates):04d}','start':float(tm[l]-.02),
            'end':float(tm[r-1]+.02),'peak_dbfs':float(db[l:r].max()),
            'voiced_fraction':fraction,'mean_flatness':float(flat[l:r].mean()),
            'kind':'uncovered_voiced_needs_review' if fraction>.4 else 'uncovered_sound_candidate',
            'action':'review_not_auto_delete'})
    # This independent pass also sees a breath hidden by an inaccurate word label.
    voiced=(db>a.rms_threshold_db-1)&(harm>.38)
    protected=binary_dilation(voiced,iterations=20)
    noise=(db>a.rms_threshold_db-3)&(harm<.24)&(flat>a.breath_flatness)&(~protected)
    noise=binary_closing(noise,iterations=2)
    breaths=[]
    for l,r in runs(noise):
        if (r-l)*.01<.09:continue
        start_s=max(offset,float(tm[l]-.10));end_s=min(offset+len(audio)/sr,float(tm[r-1]+.10))
        overlapping=[w.get('id') for w in words if w['s']<end_s and w['e']>start_s]
        breaths.append({'id':f'breath-{len(breaths):04d}','start':start_s,'end':end_s,
            'peak_dbfs':float(db[l:r].max()),'overlapping_word_ids':overlapping,
            'action':'review_candidate_including_word_alignment_if_overlapping',
            'reason':'sustained unvoiced high-flatness noise separated from detected voicing; not proof of a breath'})
    gaps=[{'left_word_id':l.get('id'),'right_word_id':r.get('id'),'start':l['e'],'end':r['s'],
           'duration_decision':'unreviewed','sound_decision':'unreviewed'}
          for l,r in zip(words,words[1:]) if r['s']-l['e']>.18]
    long_words=[{'word_id':w.get('id'),'start':w['s'],'end':w['e'],'text':w['w'],
        'action':'local_review_possible_hidden_false_start'} for w in words
        if w['e']-w['s']>max(.8,.55*len(re.sub(r'\W','',w['w'])))]
    save(a.output_dir/'sound-candidates.json',candidates)
    save(a.output_dir/'full-source-breath-candidates.json',breaths)
    save(a.output_dir/'gap-candidates.json',gaps)
    save(a.output_dir/'long-word-candidates.json',long_words)
    save(a.output_dir/'analysis-manifest.json',{'status':'measured_candidates_only',
        'source_audio':str(a.audio.resolve()),'transcript':str(a.transcript.resolve()),
        'source_offset_seconds':offset,'rms_threshold_db':a.rms_threshold_db,
        'voicing_threshold':a.voicing_threshold,'breath_flatness':a.breath_flatness,
        'thresholds_require_material_calibration':True,'automatic_cuts_or_gains_applied':False,
        'candidate_counts':{'sounds':len(candidates),'breaths':len(breaths),'gaps':len(gaps),'long_words':len(long_words)},
        'wall_seconds':time.perf_counter()-start})
    print(json.dumps({'sounds':len(candidates),'breaths':len(breaths),'gaps':len(gaps),'long_words':len(long_words)}))


if __name__=='__main__':main()
