"""Read and save per-project speech preferences; standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

FILENAME = 'video-editing.delivery.json'
SPEECH_STYLES = ('auto', 'default', 'compact', 'relaxed')


def target(project):
    raw = str(project).strip()
    if not raw:
        raise ValueError('请提供本次工程文件夹的绝对路径。')
    folder = Path(raw).expanduser()
    if not folder.is_absolute() or not folder.is_dir():
        raise ValueError('工程路径必须为已存在文件夹的绝对路径。')
    return folder.resolve()


def defaults(project):
    return dict(schema_version=2, project_directory=str(target(project)), speech={'style': 'default'})


def validate(data, project):
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 2:
        raise ValueError('当前项目配置需要 schema_version: 2；请核对原文件后按当前格式重新生成。')
    if set(data) != {'schema_version', 'project_directory', 'speech'}:
        raise ValueError('项目配置字段不完整或含当前版本未支持的字段。')
    if data['project_directory'] != str(target(project)):
        raise ValueError('配置绑定的工程目录与本次任务不一致。')
    speech = data['speech']
    if not isinstance(speech, dict) or set(speech) != {'style'} or speech['style'] not in SPEECH_STYLES:
        raise ValueError('口播选择必须为 auto、default、compact 或 relaxed。')
    return data


def read(project):
    path = target(project) / FILENAME
    if not path.exists():
        return dict(exists=False, path=str(path), revision=None, config=defaults(project))
    if path.is_symlink():
        raise ValueError('配置文件不能是符号链接。')
    raw = path.read_bytes()
    config = validate(json.loads(raw.decode('utf-8-sig')), project)
    return dict(exists=True, path=str(path), revision=hashlib.sha256(raw).hexdigest(), config=config)


def write(project, data, revision):
    validate(data, project)
    current = read(project)
    if revision != current['revision']:
        raise ValueError('项目配置已被其他写入者修改，请重新读取后保存。')
    path = Path(current['path'])
    fd, temporary = tempfile.mkstemp(prefix='.project-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return read(project)


def resolve(project):
    current = read(project)
    return dict(config_found=current['exists'], config_path=current['path'],
                speech_style=current['config']['speech']['style'], config=current['config'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Absolute existing project directory')
    parser.add_argument('--output', type=Path, help='Optional resolved settings output')
    args = parser.parse_args()
    result = resolve(args.project)
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        if args.output.resolve() in (Path(result['config_path']).resolve(), Path(args.project).resolve()):
            parser.error('--output cannot overwrite project preferences or the project directory')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
