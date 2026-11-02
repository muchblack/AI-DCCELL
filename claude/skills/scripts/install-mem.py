#!/usr/bin/env python3
"""合併記憶 hook 與 user unit；不啟用服務。"""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


def atomic_write(path, content):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == content:
        return
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    args = parser.parse_args()
    home = args.home.resolve()
    script = str(home / '.claude/skills/scripts/mem-recall.sh').replace("'", "'\"'\"'")
    failed = False
    for filename, fmt in [('.claude/settings.json', 'claude'), ('.codex/hooks.json', 'codex'), ('.gemini/config/hooks.json', 'agy')]:
        path = home / filename
        try:
            obj = json.loads(path.read_text()) if path.exists() else {}
            hook = {'type': 'command', 'command': f"bash '{script}' --format {fmt}", 'timeout': 5}
            container = obj.setdefault('mem' if fmt == 'agy' else 'hooks', {})
            entries = container.setdefault('SessionStart', [])
            if fmt == 'agy':
                if hook not in entries:
                    entries.append(hook)
            else:
                group = {'hooks': [hook]}
                if fmt == 'claude':
                    group['matcher'] = '^(startup|resume|clear|compact|fork)$'
                if group not in entries:
                    entries.append(group)
            atomic_write(path, (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode())
        except (OSError, ValueError, TypeError, AttributeError) as error:
            print(f'無法更新 {path}：{error}', file=sys.stderr)
            failed = True
    units = Path(__file__).resolve().parent / 'systemd'
    for name in ['mem-digest.service', 'mem-digest.timer']:
        try:
            atomic_write(home / '.config/systemd/user' / name, (units / name).read_bytes())
        except OSError as error:
            print(f'無法安裝 {name}：{error}', file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
