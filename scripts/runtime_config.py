"""Resolve user-owned dependencies without installing or starting services."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'assets' / 'runtime.example.json'
DEFAULT_CONFIG = ROOT / 'runtime.local.json'
TOOLS = {'ffmpeg': 'FFMPEG_BIN', 'ffprobe': 'FFPROBE_BIN',
         'blender': 'BLENDER_BIN'}
DIRECTORIES = {'asr_model', 'aligner_model', 'remotion_project',
               'sfx_library', 'indextts_root'}
FILES = {'ffmpeg', 'ffprobe', 'blender', 'node', 'speech_python', 'font_file',
         'clap_python', 'clap_checkpoint'}
FEATURES = {
    'base': ('ffmpeg', 'ffprobe'),
    'speech': ('ffmpeg', 'ffprobe', 'speech_python', 'asr_model', 'aligner_model'),
    'captions': ('node', 'remotion_project'),
    'blender': ('blender', 'font_file'),
    'sfx': ('sfx_library',),
    'clap': ('clap_python', 'clap_checkpoint'),
    'tts': ('indextts_root',),
    'vision': ('vision_model',),
}


def load(path=None):
    explicit = path or os.environ.get('VIBE_VIDEO_CONFIG')
    config = Path(explicit).expanduser().resolve() if explicit else DEFAULT_CONFIG
    data = json.loads(EXAMPLE.read_text(encoding='utf-8'))
    if explicit or config.exists():
        raw = json.loads(config.read_text(encoding='utf-8-sig'))
        if not isinstance(raw, dict) or set(raw) - set(data):
            raise ValueError('Unknown configuration fields; see assets/runtime.example.json')
        if type(raw.get('schema_version')) is not int or raw['schema_version'] != 1:
            raise ValueError('runtime configuration requires schema_version: 1')
        data.update(raw)
    for key, value in data.items():
        if key != 'schema_version' and value is not None:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{key} must be a nonempty string or null')
    for key in FILES | DIRECTORIES:
        value = data[key]
        if value:
            candidate = Path(value).expanduser()
            data[key] = str((candidate if candidate.is_absolute() else config.parent / candidate).resolve())
    for key, env in TOOLS.items():
        if os.environ.get(env):
            data[key] = str(Path(os.environ[env]).expanduser().resolve())
        elif not data[key]:
            data[key] = shutil.which(key)
    if not re.fullmatch(r'cuda:\d+', data['speech_device'] or ''):
        raise ValueError('Stable Qwen adapter supports cuda:N (NVIDIA CUDA / AMD ROCm) only')
    for key in ('indextts_url', 'vision_url'):
        parsed = urlparse(data[key] or '')
        if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError(f'{key} must be a local HTTP endpoint without credentials')
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError(f'{key} has an invalid port') from exc
    return data


def doctor(data, features):
    checks = []
    for key in dict.fromkeys(key for feature in features for key in FEATURES[feature]):
        value = data[key]
        ok = bool(value)
        if key in FILES:
            ok = ok and Path(value).is_file()
        elif key in DIRECTORIES:
            ok = ok and Path(value).is_dir()
        detail = 'found' if ok else 'missing or not configured'
        if ok and key == 'remotion_project':
            package = Path(value) / 'package.json'
            if package.is_file():
                raw = json.loads(package.read_text(encoding='utf-8-sig'))
                deps = {**raw.get('dependencies', {}), **raw.get('devDependencies', {})}
                ok = 'remotion' in deps
            else:
                ok = False
            detail = 'Remotion declared; installation/render not verified' if ok else 'package.json must declare remotion'
        if ok and key in ('asr_model', 'aligner_model'):
            ok = (Path(value) / 'config.json').is_file()
            detail = 'config.json found; weights/inference not verified' if ok else 'model config.json missing'
        if ok and key == 'indextts_root':
            ok = (Path(value) / 'indextts').is_dir() and (Path(value) / 'pyproject.toml').is_file()
            detail = 'official project layout found; weights/inference not verified' if ok else 'official IndexTTS project layout missing'
        checks.append({'key': key, 'ok': bool(ok), 'detail': detail})
    return {'ready': all(item['ok'] for item in checks), 'features': features,
            'scope': 'configuration and file checks only; no downloads, model loads, service requests or rendering',
            'checks': checks}


def qwen_command(data, input_path, output_dir, language):
    result = doctor(data, ['speech'])
    if not result['ready']:
        missing = ', '.join(item['key'] for item in result['checks'] if not item['ok'])
        raise ValueError(f'Speech dependencies missing: {missing}; see 安装与外部依赖.md#speech')
    source = Path(input_path).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    if not source.is_file():
        raise ValueError('Input media does not exist')
    if output.exists():
        raise ValueError('Use a new output directory; existing output is protected')
    command = [data['speech_python'], str(ROOT / 'scripts' / 'qwen_transcribe.py'),
               '--input', str(source), '--output-dir', str(output),
               '--asr-model', data['asr_model'], '--aligner-model', data['aligner_model'],
               '--device', data['speech_device'], '--language', language, '--ffmpeg', data['ffmpeg']]
    if data['expected_gpu']:
        command += ['--expected-gpu', data['expected_gpu']]
    return command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='Local JSON file; overrides VIBE_VIDEO_CONFIG')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('show')
    check = commands.add_parser('doctor')
    check.add_argument('--features', nargs='+', choices=tuple(FEATURES), default=['base'])
    run = commands.add_parser('run-qwen')
    run.add_argument('--input', required=True)
    run.add_argument('--output-dir', required=True)
    run.add_argument('--language', default='Chinese')
    run.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        data = load(args.config)
        if args.command == 'show':
            result = data
        elif args.command == 'doctor':
            result = doctor(data, args.features)
        else:
            command = qwen_command(data, args.input, args.output_dir, args.language)
            if not args.dry_run:
                env = os.environ.copy()
                env['FFMPEG_BIN'] = data['ffmpeg']
                env['FFPROBE_BIN'] = data['ffprobe']
                raise SystemExit(subprocess.run(command, env=env).returncode)
            result = {'command': command, 'executed': False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == 'doctor' and not result['ready']:
            raise SystemExit(1)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
