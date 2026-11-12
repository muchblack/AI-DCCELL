#!/usr/bin/env python3
"""合併記憶 hook 並安裝排程定義（systemd 或 launchd）；不啟用服務。"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import stat
import sys
import tempfile

LAUNCHD_LABEL = 'local.mem-digest'


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


def is_mem_hook(entry):
    return isinstance(entry, dict) and 'mem-recall.sh' in str(entry.get('command', ''))


def without_mem_hooks(entries):
    """移除舊的記憶 hook，同一 group 內的其他 hook 保留。"""
    kept = []
    for entry in entries:
        hooks = entry.get('hooks') if isinstance(entry, dict) else None
        if isinstance(hooks, list) and any(map(is_mem_hook, hooks)):
            entry['hooks'] = [hook for hook in hooks if not is_mem_hook(hook)]
            if entry['hooks']:
                kept.append(entry)
        elif not is_mem_hook(entry):
            kept.append(entry)
    return kept


def launchd_plist(home):
    tools = [shutil.which(name) for name in ['claude', 'herdr']]
    dirs = [str(Path(tool).parent) for tool in tools if tool]
    dirs += [str(home / '.local/bin'), str(home / '.npm-global/bin'), '/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', '/bin']
    return plistlib.dumps({
        'Label': LAUNCHD_LABEL,
        'ProgramArguments': [sys.executable, str(home / '.claude/skills/scripts/mem-digest.py')],
        'EnvironmentVariables': {'PATH': ':'.join(dict.fromkeys(dirs))},
        'StartCalendarInterval': [{'Weekday': day, 'Hour': 18, 'Minute': 0} for day in range(1, 6)],
        'StandardErrorPath': str(home / 'Library/Logs/mem-digest.log'),
        'Umask': 0o077,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--vault', default=os.environ.get('OBSIDIAN_VAULT'), help='hook 讀不到 OBSIDIAN_VAULT 時使用的 vault')
    parser.add_argument('--scheduler', choices=['systemd', 'launchd'], default='launchd' if sys.platform == 'darwin' else 'systemd')
    args = parser.parse_args()
    home = args.home.resolve()
    script = str(home / '.claude/skills/scripts/mem-recall.sh').replace("'", "'\"'\"'")
    # hook 可能由 GUI 啟動、讀不到 shell 設定，故把安裝時的 vault 寫進指令
    prefix = f'MEM_FALLBACK_VAULT={shlex.quote(args.vault)} ' if args.vault else ''
    failed = False
    for filename, fmt in [('.claude/settings.json', 'claude'), ('.codex/hooks.json', 'codex'), ('.gemini/config/hooks.json', 'agy')]:
        path = home / filename
        try:
            obj = json.loads(path.read_text()) if path.exists() else {}
            hook = {'type': 'command', 'command': f"{prefix}bash '{script}' --format {fmt}", 'timeout': 5}
            container = obj.setdefault('mem' if fmt == 'agy' else 'hooks', {})
            entries = without_mem_hooks(container.setdefault('SessionStart', []))
            if fmt == 'agy':
                entries.append(hook)
            else:
                group = {'hooks': [hook]}
                if fmt == 'claude':
                    group['matcher'] = '^(startup|resume|clear|compact|fork)$'
                entries.append(group)
            container['SessionStart'] = entries
            atomic_write(path, (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode())
        except (OSError, ValueError, TypeError, AttributeError) as error:
            print(f'無法更新 {path}：{error}', file=sys.stderr)
            failed = True
    units = Path(__file__).resolve().parent / 'systemd'
    if args.scheduler == 'launchd':
        files = [(home / f'Library/LaunchAgents/{LAUNCHD_LABEL}.plist', launchd_plist(home))]
    else:
        files = [(home / '.config/systemd/user' / name, (units / name).read_bytes())
                 for name in ['mem-digest.service', 'mem-digest.timer']]
    for path, content in files:
        try:
            atomic_write(path, content)
        except OSError as error:
            print(f'無法安裝 {path.name}：{error}', file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
