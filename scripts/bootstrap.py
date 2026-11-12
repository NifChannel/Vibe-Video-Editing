"""Install Windows x64 base/caption/speech dependencies and write machine configuration.

Default is read-only planning. --install downloads and runs package managers.
Windows uses checksum-verified portable tools and reuses the bootstrap Python.
Optional advanced modules are installed by Codex from 安装与外部依赖.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from urllib.parse import urlparse

from runtime_config import ROOT, EXAMPLE


def system_tag(system=None, machine=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if system != 'Windows' or machine not in ('amd64', 'x86_64'):
        raise ValueError(f'This release supports Windows x64 only: {system}/{machine}')
    return 'win-64'


def default_root():
    system_tag()
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'vibe-video-editing'


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def install(root, config, profiles, torch_index_url=None):
    host_tag = system_tag()
    if ROOT == root or ROOT in root.parents:
        raise ValueError('Keep downloaded runtimes outside the skill folder')
    if 'speech' in profiles:
        parsed = urlparse(torch_index_url or '')
        if (parsed.scheme != 'https' or parsed.netloc != 'download.pytorch.org'
                or not parsed.path.startswith('/whl/') or parsed.query or parsed.fragment
                or any(part in parsed.path for part in ('cpu', '..'))):
            raise ValueError('Codex must select an official CUDA/ROCm wheel index for this machine; '
                             'use --torch-index-url after checking PyTorch/ROCm support')
    root.mkdir(parents=True, exist_ok=True)
    lock = root / 'install.lock'
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError('Another install may be running; inspect install.lock before retrying') from exc
    os.close(lock_fd)
    log_path = root / 'install.log'
    receipt = {'started': dt.datetime.now(dt.timezone.utc).isoformat(), 'profiles': profiles,
               'platform': host_tag, 'commands': [], 'status': 'running'}
    def run(command, cwd=None, capture=False):
        receipt['commands'].append([str(value) for value in command])
        atomic_json(root / 'install-receipt.json', receipt)
        with log_path.open('a', encoding='utf-8') as log:
            log.write('\nCOMMAND ' + json.dumps(receipt['commands'][-1]) + '\n')
            result = subprocess.run([str(value) for value in command], cwd=cwd, env=env,
                stdout=subprocess.PIPE if capture else log, stderr=log, text=True, encoding='utf-8', timeout=900)
            if result.returncode:
                raise RuntimeError(f'Installer command failed ({result.returncode}); inspect {log_path}')
            return result.stdout if capture else None
    try:
        atomic_json(root / 'install-receipt.json', receipt)
        env = os.environ.copy()
        from windows_portable import provision
        tools = provision(root, profiles)
        receipt['base_provider'] = 'checksum-verified portable Windows distributions; existing Python reused'
        def executable(name):
            return tools[name]
        data = json.loads(EXAMPLE.read_text('utf-8'))
        if config.exists():
            raw = json.loads(config.read_text('utf-8-sig'))
            if not isinstance(raw, dict) or set(raw) - set(data) or raw.get('schema_version') != 1:
                raise ValueError('Existing runtime config is invalid; refusing to replace it')
            data.update(raw)
        data['ffmpeg'], data['ffprobe'] = str(executable('ffmpeg')), str(executable('ffprobe'))
        extra = [str(path.parent) for name, path in tools.items() if name != 'npm_cli']
        env['PATH'] = os.pathsep.join(extra + [env.get('PATH', '')])
        for key in ('ffmpeg', 'ffprobe'):
            run([data[key], '-version'])
        if 'captions' in profiles:
            project = root / 'remotion'
            project.mkdir(exist_ok=True)
            package_path = project / 'package.json'
            npm_cli = tools['npm_cli']
            npm = [executable('node'), npm_cli]
            if not package_path.exists():
                atomic_json(package_path, {'name': 'vibe-video-editing-runtime', 'private': True, 'version': '0.0.0'})
            owned_package = json.loads(package_path.read_text('utf-8-sig'))
            if owned_package.get('name') != 'vibe-video-editing-runtime' or owned_package.get('private') is not True:
                raise ValueError('Existing Remotion directory is not owned by this installer')
            if not (project / 'package-lock.json').is_file():
                # A resolved lockfile is retained. Existing installations use npm ci.
                run([*npm, 'install', '--save-exact', 'remotion', '@remotion/cli',
                     '@remotion/renderer', 'react', 'react-dom'], cwd=project)
            else:
                run([*npm, 'ci'], cwd=project)
            cli_package = project / 'node_modules/@remotion/cli/package.json'
            cli_bin = json.loads(cli_package.read_text('utf-8'))['bin']
            cli = cli_package.parent / (cli_bin['remotion'] if isinstance(cli_bin, dict) else cli_bin)
            run([executable('node'), cli, 'browser', 'ensure'], cwd=project)
            data['remotion_project'] = str(project)
            data['node'] = str(executable('node'))
        if 'speech' in profiles:
            speech = root / 'speech'
            if not speech.exists():
                run([executable('python'), '-m', 'venv', speech])
            python = speech / 'Scripts/python.exe'
            run([python, '-m', 'pip', 'install', 'torch', 'torchaudio', '--index-url', torch_index_url])
            gpu = json.loads(run([python, '-c', 'import json,torch; assert torch.cuda.is_available(), "GPU unavailable"; '
                'print(json.dumps({"name":torch.cuda.get_device_name(0),"version":torch.__version__}))'], capture=True))
            # Historical Qwen package compatibility baseline from the stable release.
            run([python, '-m', 'pip', 'install', 'qwen-asr==0.0.6', 'transformers==4.57.6',
                 'accelerate==1.12.0', 'huggingface-hub'])
            # Verify installation did not replace the selected GPU backend.
            run([python, '-c', 'import torch; assert torch.cuda.is_available(); '
                 'x=torch.ones(1,device="cuda:0"); print((x+1).item())'])
            for key, model in [('asr_model', 'Qwen3-ASR-1.7B'), ('aligner_model', 'Qwen3-ForcedAligner-0.6B')]:
                model_dir = root / 'models' / model
                code = 'import sys; from huggingface_hub import snapshot_download; snapshot_download(repo_id=sys.argv[1],local_dir=sys.argv[2])'
                run([python, '-c', code, 'Qwen/' + model, model_dir])
                data[key] = str(model_dir)
            data.update(speech_python=str(python), speech_device='cuda:0', expected_gpu=gpu['name'])
            receipt['gpu'] = gpu
            receipt['speech_validation'] = 'GPU tensor execution only; real ASR/alignment sample still required'
            run([python, '-m', 'pip', 'freeze'], capture=False)
        # Do not publish a partially installed configuration.
        from runtime_config import load
        candidate = config.with_name(config.name + '.candidate')
        atomic_json(candidate, data)
        load(candidate)
        candidate.replace(config)
        receipt.update(status='installed', config=str(config),
                       verification='tool versions and browser download; see module-specific smoke checks')
        atomic_json(root / 'install-receipt.json', receipt)
        return receipt
    except Exception as exc:
        receipt.update(status='failed', error=str(exc))
        atomic_json(root / 'install-receipt.json', receipt)
        raise
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=default_root())
    parser.add_argument('--config', type=Path, default=ROOT / 'runtime.local.json')
    parser.add_argument('--profiles', nargs='+', choices=('base', 'captions', 'speech'), default=['base', 'captions'])
    parser.add_argument('--torch-index-url', help='Codex selects official GPU wheel index after hardware inspection')
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    try:
        root, config = args.root.expanduser().resolve(), args.config.expanduser().resolve()
        if args.install:
            result = install(root, config, args.profiles, args.torch_index_url)
        else:
            provider = ['official FFmpeg-linked Gyan ZIP (SHA256 checked)', 'existing compatible Python']
            result = {'mode': 'plan', 'platform': system_tag(), 'root': str(root), 'config': str(config),
                'profiles': args.profiles, 'downloads': [*provider,
                *(['Node 22 / Remotion / rendering browser'] if 'captions' in args.profiles else []),
                *(['compatible GPU PyTorch / Qwen packages / two Hugging Face model repositories'] if 'speech' in args.profiles else [])],
                'system_changes': 'no system PATH, drivers, existing Python environments or services changed',
                'executed': False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
