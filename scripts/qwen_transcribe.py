"""Local Qwen3-ASR + ForcedAligner adapter for the speech F workflow.

Produces fresh source-time transcripts, raw chunks, GPU evidence and timings.
It does not decide edits, rewrite the customer's script or clean up audio.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import difflib
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import unicodedata


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def plain(value):
    if dataclasses.is_dataclass(value):
        return plain(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (str, float, int, bool, type(None))):
        return value
    if hasattr(value, 'item'):
        return value.item()
    return str(value)


def save(path, value):
    path.write_text(json.dumps(plain(value), ensure_ascii=False, indent=2), encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024**2):
            h.update(block)
    return h.hexdigest()


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


def tensors(value, torch):
    if isinstance(value, torch.Tensor):
        return {str(value.device)}
    values = value.values() if isinstance(value, dict) else value if isinstance(value, (list, tuple)) else []
    result = set()
    for v in values:
        result.update(tensors(v, torch))
    return result


class GPUTrace:
    def __init__(self, module, torch, device):
        self.expected = str(torch.device(device))
        self.parameter_devices = sorted({str(p.device) for p in module.parameters()})
        if self.parameter_devices != [self.expected]:
            raise RuntimeError(f'CPU/meta/offloaded parameters prohibited: {self.parameter_devices}')
        self.probes = {}
        candidates = [(name, m) for name, m in module.named_modules()
                      if isinstance(m, (torch.nn.Linear, torch.nn.Conv1d, torch.nn.Conv2d))]
        self.handles = []
        for name, child in dict(candidates[:2] + candidates[-1:]).items():
            state = {'calls': 0, 'inputs': set(), 'outputs': set()}
            self.probes[name] = state

            def hook(_module, args, output, state=state):
                state['calls'] += 1
                state['inputs'].update(tensors(args, torch))
                state['outputs'].update(tensors(output, torch))

            self.handles.append(child.register_forward_hook(hook))

    def result(self):
        observed = [p for p in self.probes.values() if p['calls']]
        if not observed:
            raise RuntimeError('No model GPU forward pass observed')
        if any(p['inputs'] != {self.expected} or p['outputs'] != {self.expected} for p in observed):
            raise RuntimeError('Non-GPU tensors observed in model forward pass')
        return {'parameter_devices': self.parameter_devices, 'gpu_forward_verified': True,
                'probes': {k: {'calls': v['calls'], 'inputs': sorted(v['inputs']),
                               'outputs': sorted(v['outputs'])} for k, v in self.probes.items()}}


def chunk_plan(audio, rate, core_seconds, context_seconds):
    import numpy as np
    from scipy.ndimage import uniform_filter1d
    duration = len(audio) / rate
    frame, hop = round(rate * .04), round(rate * .01)
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(audio, (0, frame)), frame)[::hop]
    db = 20 * np.log10(np.sqrt(np.mean(frames**2, axis=1) + 1e-16))
    smoothed = uniform_filter1d(db, size=9)
    times = np.arange(len(db)) * .01
    bounds = [0.]
    while duration - bounds[-1] > core_seconds + 2:
        lower, upper = bounds[-1] + max(2., core_seconds - 4), bounds[-1] + core_seconds + 1
        ids = np.where((times >= lower) & (times <= min(upper, duration)))[0]
        score = smoothed[ids] + .5 * np.abs(times[ids] - bounds[-1] - core_seconds)
        bounds.append(round(float(times[ids[np.argmin(score)]]), 2))
    bounds.append(duration)
    return [{'index': i, 'core_start': a, 'core_end': b,
             'audio_start': max(0., a - context_seconds),
             'audio_end': min(duration, b + context_seconds)}
            for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]


def stitch(previous, following, chunk):
    boundary = chunk['core_start']
    li = [i for i, w in enumerate(previous) if w['s'] >= chunk['audio_start'] - .4]
    ri = [i for i, w in enumerate(following) if w['e'] <= boundary + 2.]
    blocks = difflib.SequenceMatcher(None, [normalized(previous[i]['w']) for i in li],
                                     [normalized(following[i]['w']) for i in ri], autojunk=False)
    choices = []
    for match in blocks.get_matching_blocks():
        if match.size < 2:
            continue
        for k in range(match.size):
            x, y = li[match.a + k], ri[match.b + k]
            if abs(previous[x]['s'] - following[y]['s']) <= .9:
                score = abs((previous[x]['e'] + following[y]['e']) / 2 - boundary) - .06 * match.size
                choices.append((score, x, y, match.size))
    if choices:
        _, x, y, size = min(choices)
        return previous[:x + 1] + following[y + 1:], {
            'boundary': boundary, 'method': 'overlap_lexical_agreement', 'matched_units': size,
            'requires_review': False}
    return ([w for w in previous if (w['s'] + w['e']) / 2 < boundary]
            + [w for w in following if (w['s'] + w['e']) / 2 >= boundary]), {
                'boundary': boundary, 'method': 'quiet_core_midpoint_fallback', 'requires_review': True}


def segments(words):
    output, current = [], []
    for word in words:
        if current and (word['s'] - current[-1]['e'] > .4 or
                        current[-1].get('display', '').endswith(('。', '！', '？', ';', '!', '?', '.'))):
            output.append({'start': current[0]['s'], 'end': current[-1]['e'],
                           'text': ''.join(w.get('display', w['w']) for w in current), 'words': current})
            current = []
        current.append(word)
    if current:
        output.append({'start': current[0]['s'], 'end': current[-1]['e'],
                       'text': ''.join(w.get('display', w['w']) for w in current), 'words': current})
    return output


def run(args):
    source, output = args.input.resolve(), args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists():
        raise FileExistsError(f'Use a new output directory; refusing to reuse/overwrite {output}')
    if not re.fullmatch(r'cuda:\d+', args.device):
        raise ValueError('Explicit GPU device cuda:N required; CPU fallback is disabled')
    if args.start < 0 or (args.duration is not None and args.duration <= 0):
        raise ValueError('Invalid source window')
    if not 5 <= args.core_seconds <= 60 or not 0 <= args.context_seconds <= 5:
        raise ValueError('Invalid chunk settings')
    for model in [args.asr_model, args.aligner_model]:
        if not model.is_dir():
            raise FileNotFoundError(f'Local model directory required: {model}')
    output.mkdir(parents=True)
    (output / 'raw-chunks').mkdir()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    total_start = time.perf_counter()
    manifest = {'status': 'running', 'started_at': stamp(), 'source': str(source),
                'source_offset_seconds': args.start, 'device_requested': args.device,
                'cpu_fallback_allowed': False, 'language': args.language,
                'asr_model': str(args.asr_model.resolve()), 'aligner_model': str(args.aligner_model.resolve()),
                'core_seconds': args.core_seconds, 'context_seconds': args.context_seconds,
                'dtype': 'float16', 'batch_size': 1, 'asr_seconds': 0., 'alignment_seconds': 0.,
                'chunks': [], 'source_hash_seconds': None}
    try:
        import torch
        import soundfile as sf
        if not torch.cuda.is_available():
            raise RuntimeError('GPU unavailable; do not fall back to CPU or Whisper-small')
        index = int(args.device.split(':')[1])
        name = torch.cuda.get_device_name(index)
        if args.expected_gpu and args.expected_gpu.casefold() not in name.casefold():
            raise RuntimeError(f'GPU mismatch: expected {args.expected_gpu}, found {name}')
        torch.cuda.set_device(index)
        manifest.update({'gpu': name, 'torch': torch.__version__, 'hip': torch.version.hip,
                         'cuda_runtime': torch.version.cuda,
                         'packages': {p: importlib.metadata.version(p) for p in
                                      ('qwen-asr', 'transformers', 'accelerate', 'numpy')}})
        manifest['model_provenance'] = {}
        for label, folder in [('asr', args.asr_model), ('aligner', args.aligner_model)]:
            installed = folder / 'LOCAL_INSTALL_MANIFEST.json'
            manifest['model_provenance'][label] = {
                'config_sha256': sha(folder / 'config.json'),
                'local_install_manifest': json.loads(installed.read_text('utf-8')) if installed.is_file() else None}
        started = time.perf_counter()
        manifest['source_sha256'] = sha(source)
        manifest['source_hash_seconds'] = time.perf_counter() - started
        command = [args.ffmpeg, '-nostdin', '-hide_banner', '-v', 'error', '-n']
        if args.start:
            command += ['-ss', str(args.start)]
        command += ['-i', str(source), '-map', f'0:a:{args.audio_stream}', '-vn']
        if args.duration is not None:
            command += ['-t', str(args.duration)]
        command += ['-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(output / 'source16k.wav')]
        started = time.perf_counter()
        subprocess.run(command, check=True, capture_output=True)
        manifest['extraction_seconds'] = time.perf_counter() - started
        audio, rate = sf.read(output / 'source16k.wav', dtype='float32')
        if not len(audio):
            raise ValueError('Empty audio input')
        manifest['analysis_audio_sha256'] = sha(output / 'source16k.wav')
        manifest['source_window_duration_seconds'] = len(audio) / rate
        plan = chunk_plan(audio, rate, args.core_seconds, args.context_seconds)
        save(output / 'chunk-plan.json', plan)
        from qwen_asr import Qwen3ASRModel
        started = time.perf_counter()
        model = Qwen3ASRModel.from_pretrained(str(args.asr_model.resolve()), dtype=torch.float16,
            device_map=args.device, attn_implementation='eager', local_files_only=True,
            max_inference_batch_size=1, max_new_tokens=args.max_new_tokens,
            forced_aligner=str(args.aligner_model.resolve()),
            forced_aligner_kwargs=dict(dtype=torch.float16, device_map=args.device,
                                       attn_implementation='eager', local_files_only=True))
        traces = {'asr': GPUTrace(model.model, torch, args.device),
                  'aligner': GPUTrace(model.forced_aligner.model, torch, args.device)}
        torch.cuda.synchronize()
        manifest['model_load_seconds'] = time.perf_counter() - started
        torch.cuda.reset_peak_memory_stats(index)
        joined, boundaries = [], []
        for chunk in plan:
            samples = audio[round(chunk['audio_start'] * rate):round(chunk['audio_end'] * rate)]
            torch.cuda.synchronize(); started = time.perf_counter()
            with torch.inference_mode():
                recognized = model.transcribe(audio=(samples, rate), language=args.language,
                                              return_time_stamps=False)
            torch.cuda.synchronize(); asr_seconds = time.perf_counter() - started
            text = recognized[0].text
            started = time.perf_counter()
            with torch.inference_mode():
                aligned = model.forced_aligner.align(audio=(samples, rate), text=text,
                                                     language=args.language) if text.strip() else []
            torch.cuda.synchronize(); alignment_seconds = time.perf_counter() - started
            # Preserve raw outputs before any stitching, selection or proofreading.
            save(output / 'raw-chunks' / f'{chunk["index"]:04d}.json',
                 {'chunk': chunk, 'source_offset_seconds': args.start,
                  'recognition': recognized, 'alignment': aligned})
            absolute_chunk = {**chunk, **{k: chunk[k] + args.start for k in
                              ('core_start', 'core_end', 'audio_start', 'audio_end')}}
            words, cursor = [], 0
            for item in aligned[0] if aligned else []:
                position = text.find(item.text, cursor)
                display = item.text
                if position >= 0:
                    cursor = position + len(item.text)
                    while cursor < len(text) and text[cursor] in '，。、；：！？,.;:!?':
                        display += text[cursor]; cursor += 1
                words.append({'w': item.text, 'display': display,
                    's': float(item.start_time) + absolute_chunk['audio_start'],
                    'e': float(item.end_time) + absolute_chunk['audio_start'],
                    'confidence': None, 'chunk_index': chunk['index']})
            if joined:
                joined, decision = stitch(joined, words, absolute_chunk)
                boundaries.append(decision)
            else:
                joined = words
            manifest['asr_seconds'] += asr_seconds
            manifest['alignment_seconds'] += alignment_seconds
            manifest['chunks'].append({**absolute_chunk, 'asr_seconds': asr_seconds,
                'alignment_seconds': alignment_seconds, 'word_count': len(words),
                'empty_recognition': not bool(text.strip())})
            save(output / 'run-manifest.json', manifest)
            print(f'CHUNK {chunk["index"] + 1}/{len(plan)} ASR={asr_seconds:.3f}s ALIGN={alignment_seconds:.3f}s', flush=True)
        diagnostics = [b for b in boundaries if b['requires_review']]
        for i, word in enumerate(joined):
            word['id'] = f'w{i:06d}'
            if word['s'] < args.start or word['e'] < word['s'] or word['e'] > args.start + len(audio) / rate + .1:
                diagnostics.append({'type': 'invalid_word_bounds', 'word_id': word['id']})
            if word['e'] - word['s'] > max(.8, .55 * len(normalized(word['w']))):
                diagnostics.append({'type': 'long_word_may_hide_false_start', 'word_id': word['id'],
                                    'start': word['s'], 'end': word['e']})
            if i and word['s'] < joined[i-1]['e'] - .04:
                diagnostics.append({'type': 'word_overlap', 'word_ids': [joined[i-1]['id'], word['id']]})
        raw = {'source': str(source), 'source_sha256': manifest['source_sha256'],
            'source_offset_seconds': args.start, 'duration': len(audio) / rate,
            'time_domain': 'original input file seconds, including source offset',
            'words': joined, 'segments': segments(joined), 'boundaries': boundaries,
            'diagnostics': diagnostics, 'confidence_policy': 'Qwen exposes no calibrated per-word probability here; None is unknown',
            'raw_chunks_preserved': True, 'proofreading_completed': False}
        save(output / 'transcript.raw.json', raw)
        compatible_words = [{**w, 'p': -1.} for w in joined]
        save(output / 'transcript.json', {**raw, 'words': compatible_words,
            'segments': segments(compatible_words), 'p_minus_one_means_unknown': True})
        manifest.update({'status': 'completed', 'finished_at': stamp(),
            'total_wall_seconds': time.perf_counter() - total_start,
            'peak_gpu_allocated_bytes': torch.cuda.max_memory_allocated(index),
            'gpu_evidence': {name: trace.result() for name, trace in traces.items()},
            'word_count': len(joined), 'review_candidate_count': len(diagnostics)})
        save(output / 'run-manifest.json', manifest)
    except Exception:
        manifest.update({'status': 'failed', 'finished_at': stamp(),
            'total_wall_seconds': time.perf_counter() - total_start, 'error': traceback.format_exc()})
        save(output / 'run-manifest.json', manifest)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--asr-model', type=Path, required=True)
    parser.add_argument('--aligner-model', type=Path, required=True)
    parser.add_argument('--language', default='Chinese')
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--expected-gpu')
    parser.add_argument('--audio-stream', type=int, default=0)
    parser.add_argument('--start', type=float, default=0)
    parser.add_argument('--duration', type=float)
    parser.add_argument('--core-seconds', type=float, default=24)
    parser.add_argument('--context-seconds', type=float, default=1.5)
    parser.add_argument('--max-new-tokens', type=int, default=512)
    parser.add_argument('--ffmpeg', default=os.environ.get('FFMPEG_BIN', 'ffmpeg'))
    run(parser.parse_args())


if __name__ == '__main__':
    main()
