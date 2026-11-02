#!/usr/bin/env bash
# 唯讀記憶注入；任何錯誤都不阻擋 session 啟動。
code=$(cat <<'PY'
import argparse, json, os, pathlib, re, select, signal, sys

class RecallTimeout(Exception):
    pass

def expired(*_):
    raise RecallTimeout()

signal.signal(signal.SIGALRM, expired)
signal.setitimer(signal.ITIMER_REAL, 2.9)

try:
    parser = argparse.ArgumentParser()
    parser.add_argument('--format', choices=['claude', 'codex', 'agy'])
    parser.add_argument('--search', nargs='+')
    parser.add_argument('--cwd')
    args = parser.parse_args()
    cwd = args.cwd or os.getcwd()
    if not args.cwd and not sys.stdin.isatty():
        try:
            data = bytearray()
            while len(data) < 65536 and select.select([0], [], [], 0.05)[0]:
                chunk = os.read(0, 65536 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
            context = json.loads(data)
            paths = context.get('workspacePaths')
            selected = paths[0] if isinstance(paths, list) and paths else context.get('cwd')
            if isinstance(selected, str) and selected:
                cwd = selected
        except (ValueError, OSError, TypeError, AttributeError):
            pass
    project = pathlib.Path(cwd)
    vault = pathlib.Path(os.environ.get('OBSIDIAN_VAULT', '/mnt/d/obsidian'))
    if not vault.is_dir():
        vault = pathlib.Path(os.environ.get('MEM_FALLBACK_VAULT', '/mnt/d/obsidian'))
    root = vault / 'myWiki/20-領域/AI協作記憶'
    if root.is_symlink() or not root.resolve().is_relative_to(vault.resolve()):
        raise ValueError('記憶區越界')
    root = root.resolve()
    def read(path):
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            return ''
        if not resolved.is_file():
            return ''
        return resolved.read_text(encoding='utf-8')
    if args.search:
        hits = []
        size = 0
        for path in sorted(root.rglob('*.md')):
            for number, line in enumerate(read(path).splitlines(), 1):
                if any(word.casefold() in line.casefold() for word in args.search):
                    hit = f'{path.relative_to(root)}:{number}:{line}\n'
                    if size + len(hit.encode()) > 3072:
                        break
                    hits.append(hit)
                    size += len(hit.encode())
        sys.stdout.write(''.join(hits))
        sys.exit(0)
    text = read(root / '使用習慣.md')
    core = re.search(r'^## 核心\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S).group(1)
    heading = '記憶參考資料（不是指令）\n'
    search = '搜尋：bash ~/.claude/skills/scripts/mem-recall.sh --search <關鍵字>\n'
    budget = 3072 - len((heading + search).encode())
    core = ('## 核心\n' + core).encode()[:budget - 1].decode('utf-8', 'ignore') + '\n'
    payload = heading + core
    budget -= len(core.encode())
    stacks = [('laravel', ['artisan']), ('php', ['composer.json']),
              ('go', ['go.mod']), ('python', ['pyproject.toml', 'requirements.txt']),
              ('node', ['package.json']), ('linux', ['Dockerfile', 'compose.yaml', 'docker-compose.yml'])]
    for stack, markers in stacks:
        if not any((project / marker).exists() for marker in markers):
            continue
        lines = [line + '\n' for line in read(root / f'踩坑/{stack}.md').splitlines()]
        kept = []
        for line in reversed(lines):
            if len(line.encode()) > budget:
                break
            kept.append(line)
            budget -= len(line.encode())
        payload += ''.join(reversed(kept))
    payload += search
    if args.format == 'agy':
        payload = json.dumps({'injectSteps': [{'systemMessage': {'systemMessage': payload}}]}, ensure_ascii=False)
    elif args.format:
        payload = json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': payload}}, ensure_ascii=False)
    sys.stdout.write(payload)
except Exception:
    pass
PY
)
python3 -c "$code" "$@" 2>/dev/null || true
