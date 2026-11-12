"""Discover local modules and generate the AI/user catalogs from module.json."""
from pathlib import Path
from contextlib import contextmanager
import argparse, hashlib, json, os, re, tempfile, threading

ROOT = Path(__file__).resolve().parents[1]
KINDS = {'styles': ('Styles', '风格清单'), 'functions': ('Functional Skills', '功能清单')}
LOCK = threading.RLock()
FIELDS = {'id', 'name', 'description', 'aliases', 'cues'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic_text(path, text):
    path = Path(path)
    if path.exists() and path.read_text('utf-8-sig') == text:
        return
    fd, name = tempfile.mkstemp(prefix='.module-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def validate_meta(meta, folder_id):
    if not isinstance(meta, dict) or set(meta) != FIELDS:
        raise ValueError('module.json 字段必须为 id/name/description/aliases/cues。')
    if meta['id'] != folder_id or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', folder_id) or len(folder_id) > 50:
        raise ValueError('模块 ID 必须与目录名一致，使用不超过 50 字符的小写字母、数字和连字符。')
    for key in ('name', 'description', 'cues'):
        if not isinstance(meta[key], str) or not meta[key].strip():
            raise ValueError(f'{key} 不能为空。')
    if not isinstance(meta['aliases'], list) or any(not isinstance(x, str) or not x.strip() for x in meta['aliases']):
        raise ValueError('aliases 必须是非空字符串数组（可为空数组）。')
    return meta


def collect(kind):
    folder, _ = KINDS[kind]
    base = ROOT / folder
    # Git does not retain empty directories in a community checkout.
    if kind == 'styles':
        base.mkdir(exist_ok=True)
    rows, seen = [], set()
    for module in sorted(base.iterdir()):
        if not module.is_dir() or module.name.startswith('.'): continue
        if module.resolve().parent != base.resolve(): raise ValueError('模块目录必须位于库内。')
        meta = validate_meta(read_json(module / 'module.json'), module.name)
        spec = module / 'SKILL.md'
        text = spec.read_text('utf-8-sig')
        if not text.startswith('---\n') or not re.search(r'^name: .+$', text, re.M) or not re.search(r'^description: .+$', text, re.M):
            raise ValueError(f'{module.name} 缺少 skill 元数据。')
        for alias in {x.strip().casefold() for x in [meta['id'], meta['name'], *meta['aliases']]}:
            if alias in seen: raise ValueError(f'重复的名称或别名：{alias}')
            seen.add(alias)
        row = {**meta, 'reference': spec.relative_to(ROOT).as_posix(),
               'module': (module / 'module.json').relative_to(ROOT).as_posix()}
        if kind == 'styles':
            from style import validate_config
            validate_config(read_json(module / 'style.json'))
            row['config'] = (module / 'style.json').relative_to(ROOT).as_posix()
        rows.append(row)
    return rows


def sync():
    """Validate both libraries before writing any generated catalog."""
    with LOCK:
        catalogs = {kind: collect(kind) for kind in KINDS}
        for kind, rows in catalogs.items():
            _, title = KINDS[kind]
            atomic_text(ROOT / (title + '.json'), json_text({'schema_version': 1, kind: rows}))
            lines = [f'# {title}', '', '由模块自动生成。修改各模块的 `module.json` 可更新名称、简介和别名；修改 `SKILL.md` 可更新具体规范。由当前代理按用户要求维护模块。', '',
                     '运行 `python scripts/library.py sync` 刷新。不要直接修改本生成文件。', '',
                     '| 名称 | 模块 ID | 简介 / 适用线索 | 入口 |', '| --- | --- | --- | --- |']
            def cell(value): return str(value).replace('|', '\\|').replace('\n', ' ')
            for row in rows:
                href = row['reference'].replace(' ', '%20')
                lines.append(f"| {cell(row['name'])} | `{row['id']}` | {cell(row['description'])} | [SKILL.md]({href}) |")
            atomic_text(ROOT / (title + '.md'), '\n'.join(lines) + '\n')
        return catalogs


def locate(kind, module_id):
    if kind not in KINDS or not isinstance(module_id, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', module_id):
        raise ValueError('模块类型或 ID 无效。')
    folder = ROOT / KINDS[kind][0] / module_id
    if folder.resolve().parent != (ROOT / KINDS[kind][0]).resolve() or not folder.is_dir():
        raise ValueError('模块不存在。')
    return folder


def load(kind, module_id):
    with LOCK:
        folder = locate(kind, module_id)
        meta = validate_meta(read_json(folder / 'module.json'), module_id)
        spec = (folder / 'SKILL.md').read_text('utf-8-sig')
        config = read_json(folder / 'style.json') if kind == 'styles' else None
        payload = dict(metadata=meta, spec=spec, config=config)
        revision = hashlib.sha256(json_text(payload).encode('utf-8')).hexdigest()
        return dict(**payload, revision=revision)


def save(kind, module_id, metadata, spec, config, revision):
    with LOCK:
        folder = locate(kind, module_id)
        previous = load(kind, module_id)
        if revision != previous['revision']: raise ValueError('模块已被其他写入者修改，请重新读取。')
        validate_meta(metadata, module_id)
        if not isinstance(spec, str) or len(spec.strip()) < 80 or not spec.startswith('---\n'):
            raise ValueError('请保留有效的 SKILL.md 元数据和完整规范。')
        expected = 'video-style-' + module_id if kind == 'styles' else module_id
        if not re.search(r'^name: ' + re.escape(expected) + r'\s*$', spec, re.M):
            raise ValueError('请保留 SKILL.md 的模块标识 name。')
        if not re.search(r'^description: .+$', spec, re.M): raise ValueError('缺少 skill description。')
        if kind == 'styles':
            from style import validate_config
            validate_config(config)
        # Check aliases against other modules before touching files.
        wanted = {x.strip().casefold() for x in [module_id, metadata['name'], *metadata['aliases']]}
        for row in collect(kind):
            if row['id'] != module_id and wanted & {x.strip().casefold() for x in [row['id'], row['name'], *row['aliases']]}:
                raise ValueError('名称或别名与其他模块冲突。')
        changes = {'module.json': json_text(metadata), 'SKILL.md': spec.rstrip() + '\n'}
        if kind == 'styles': changes['style.json'] = json_text(config)
        originals = {name: (folder / name).read_text('utf-8-sig') for name in changes}
        try:
            for name, text in changes.items(): atomic_text(folder / name, text)
            sync()
        except Exception:
            for name, text in originals.items(): atomic_text(folder / name, text)
            sync()
            raise
        return load(kind, module_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sync', 'validate'])
    args = parser.parse_args()
    data = sync() if args.command == 'sync' else {k: collect(k) for k in KINDS}
    print(json_text({kind: len(rows) for kind, rows in data.items()}))


if __name__ == '__main__': main()
