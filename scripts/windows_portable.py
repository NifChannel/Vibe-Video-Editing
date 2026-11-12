"""Download checksum-verified Windows tools from official distribution sources."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import subprocess
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen
import zipfile


def native_download(url, output):
    """Use Windows' trusted HTTPS stack if Python cannot build the certificate chain."""
    if os.name != 'nt':
        raise ValueError('Native HTTPS fallback is Windows-only')
    env = {**os.environ, 'VIBE_DOWNLOAD_URL': url, 'VIBE_DOWNLOAD_OUTPUT': str(output)}
    # The script is constant; URLs and paths are data in child-only variables.
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
        "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; "
        'Invoke-WebRequest -Uri $env:VIBE_DOWNLOAD_URL -OutFile $env:VIBE_DOWNLOAD_OUTPUT -UseBasicParsing'],
        env=env, capture_output=True, text=True, errors='replace', timeout=900)
    if result.returncode:
        raise RuntimeError('Windows HTTPS download failed: ' + result.stderr[-1200:])


def read_text(url):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'vibe-video-editing'}), timeout=60) as response:
            return response.read().decode('utf-8-sig')
    except (URLError, OSError):
        if os.name != 'nt':
            raise
        with tempfile.TemporaryDirectory(prefix='vibe-https-') as folder:
            output = Path(folder) / 'response.txt'
            native_download(url, output)
            return output.read_text('utf-8-sig')


def download(url, path, expected):
    if not re.fullmatch(r'[a-fA-F0-9]{64}', expected):
        raise ValueError('Missing valid archive SHA256')
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected.lower():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.part')
    try:
        with urlopen(Request(url, headers={'User-Agent': 'vibe-video-editing'}), timeout=60) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
    except (URLError, OSError):
        if os.name != 'nt':
            raise
        native_download(url, temporary)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected.lower():
        raise ValueError(f'Archive SHA256 mismatch: {path.name}')
    temporary.replace(path)


def unpack(archive, folder):
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        # Validate every entry before writing any file.
        entries = source.infolist()
        for item in entries:
            if not (folder / item.filename).resolve().is_relative_to(folder.resolve()):
                raise ValueError('Archive path escapes installation directory')
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Archive contains a symbolic link')
        for item in entries:
            destination = folder / item.filename
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source.open(item) as src, destination.open('wb') as dst:
                    shutil.copyfileobj(src, dst)


def provision(root, profiles):
    downloads, tools = root / 'downloads', root / 'portable'
    tools.mkdir(parents=True, exist_ok=True)
    records = []
    print('Preparing checksum-verified portable FFmpeg...', flush=True)
    ffmpeg_url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
    checksum = re.search(r'\b[a-fA-F0-9]{64}\b', read_text(ffmpeg_url + '.sha256'))
    if not checksum:
        raise ValueError('FFmpeg distribution did not provide a SHA256')
    archive = downloads / 'ffmpeg-essentials.zip'
    download(ffmpeg_url, archive, checksum.group())
    ffmpeg_folder = tools / checksum.group()[:12]
    if not (ffmpeg_folder / '.unpacked').is_file():
        unpack(archive, ffmpeg_folder)
        (ffmpeg_folder / '.unpacked').touch()
    ffmpeg = list(ffmpeg_folder.glob('*/bin/ffmpeg.exe'))
    ffprobe = list(ffmpeg_folder.glob('*/bin/ffprobe.exe'))
    if len(ffmpeg) != 1 or len(ffprobe) != 1:
        raise ValueError('Unexpected FFmpeg archive layout')
    result = {'python': Path(sys.executable), 'ffmpeg': ffmpeg[0], 'ffprobe': ffprobe[0]}
    records.append({'source': ffmpeg_url, 'sha256': checksum.group().lower()})
    if 'captions' in profiles:
        print('Preparing official portable Node 22...', flush=True)
        node_base = 'https://nodejs.org/dist/latest-v22.x/'
        sums = read_text(node_base + 'SHASUMS256.txt')
        entries = re.findall(r'^([a-f0-9]{64})\s+(node-v22\.[0-9.]+-win-x64\.zip)\s*$', sums, re.M)
        if len(entries) != 1:
            raise ValueError('Cannot select the official Node 22 x64 Windows ZIP')
        digest, filename = entries[0]
        archive = downloads / filename
        download(node_base + filename, archive, digest)
        folder = tools / filename.removesuffix('.zip')
        if not (folder / '.unpacked').is_file():
            unpack(archive, folder)
            (folder / '.unpacked').touch()
        binaries = list(folder.glob('*/node.exe'))
        if len(binaries) != 1:
            raise ValueError('Unexpected Node archive layout')
        result.update(node=binaries[0], npm_cli=binaries[0].parent / 'node_modules/npm/bin/npm-cli.js')
        records.append({'source': node_base + filename, 'sha256': digest})
    (root / 'portable-downloads.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    return result
