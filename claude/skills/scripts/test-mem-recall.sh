#!/usr/bin/env bash
set -euo pipefail
python3 - "$(dirname "$0")" "${1:-basic}" <<'PY'
import json, os, pathlib, subprocess, sys, tempfile, time
script = pathlib.Path(sys.argv[1]).resolve() / 'mem-recall.sh'
case = sys.argv[2]
with tempfile.TemporaryDirectory() as tmp:
    base = pathlib.Path(tmp)
    root = base / 'vault/myWiki/20-領域/AI協作記憶'
    root.mkdir(parents=True)
    (root / '踩坑').mkdir()
    (root / '使用習慣.md').write_text('## 核心\n核心「引號」 " \\ 測試\n## 其他\n不注入\n')
    (root / '踩坑/php.md').write_text('PHP 經驗\n')
    project = base / 'project'
    project.mkdir()
    (project / 'composer.json').touch()
    env = dict(os.environ, HOME=str(base), OBSIDIAN_VAULT=str(base / 'vault'), MEM_FALLBACK_VAULT=str(base / 'absent'))
    def run(*args, data='', cwd=project):
        return subprocess.run(['bash', str(script), *args], input=data, text=True, capture_output=True, env=env, cwd=cwd, timeout=4)
    if case == 'basic':
        p = run()
        assert p.returncode == 0 and not p.stderr, p
        assert all(s in p.stdout for s in ['參考資料', '不是指令', '## 核心', 'PHP 經驗', '--search']), p.stdout
        assert '不注入' not in p.stdout
    elif case == 'budget':
        (root / '使用習慣.md').write_text('## 核心\n' + '繁體中文字' * 2000 + '\n')
        (root / '踩坑/php.md').write_text('過期\n' * 2000 + '最新\n')
        p = run()
        assert p.stdout and len(p.stdout.encode()) <= 3072 and '--search' in p.stdout, p.stdout
        assert p.stdout.splitlines()[-1].startswith('搜尋：'), '搜尋指令必須獨立成最後一行'
        (root / '使用習慣.md').write_text('## 核心\n短句\n')
        p = run()
        assert '最新' in p.stdout and '過期\n' in p.stdout and len(p.stdout.encode()) <= 3072
    elif case == 'errors':
        for content in ['沒有核心', '### 核心\n不是核心區段', '## 核心\n秘密']:
            f = root / '使用習慣.md'
            f.write_text(content)
            if content.startswith('## 核心'): f.chmod(0)
            p = run()
            assert (p.stdout, p.stderr, p.returncode) == ('', '', 0), p
            f.chmod(0o600)
        env['OBSIDIAN_VAULT'] = str(base / 'bad')
        p = run()
        assert (p.stdout, p.stderr, p.returncode) == ('', '', 0), p
    elif case == 'formats':
        plain = run().stdout
        assert plain
        for fmt in ['claude', 'codex', 'agy']:
            p = run('--format', fmt)
            obj = json.loads(p.stdout)
            context = obj['injectSteps'][0]['systemMessage']['systemMessage'] if fmt == 'agy' else obj['hookSpecificOutput']['additionalContext']
            assert context == plain
    elif case == 'containment':
        outside = base / 'outside.md'
        outside.write_text('外部機密\n')
        (root / '踩坑/php.md').unlink()
        (root / '踩坑/php.md').symlink_to(outside)
        (root / 'leak.md').symlink_to(outside)
        assert '外部機密' not in run().stdout
        assert run('--search', '外部機密').stdout == ''
        (root / '工具環境.md').write_text('Alpha beta\n繁體中文字\n')
        p = run('--search', 'ALPHA', '繁體')
        assert '工具環境.md:1:Alpha beta' in p.stdout and '工具環境.md:2:' in p.stdout, p
    elif case == 'stdin':
        other = base / 'other'
        other.mkdir()
        for data in [json.dumps({'workspacePaths':[str(project)]}), json.dumps({'cwd':str(project)})]:
            assert 'PHP 經驗' in run(data=data, cwd=other).stdout
            assert 'PHP 經驗' not in run('--cwd', str(other), data=data).stdout
        for data in ['', 'bad json']:
            assert 'PHP 經驗' in run(data=data).stdout
        fifo = root / '踩坑/php.md'
        fifo.unlink()
        os.mkfifo(fifo)
        start = time.monotonic()
        assert run().returncode == 0
        assert time.monotonic() - start < 3.7
    elif case == 'stdin-delay':
        other = base / 'other'
        other.mkdir()
        with subprocess.Popen(['bash', str(script)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=env, cwd=other) as process:
            time.sleep(0.2)
            out, err = process.communicate(json.dumps({'workspacePaths':[str(project)]}), timeout=2)
            assert process.returncode == 0 and not err and 'PHP 經驗' in out, (out, err)
    elif case == 'stdin-closed':
        p = subprocess.run(['bash', '-c', 'bash "$1" <&-', 'recall', str(script)],
                           capture_output=True, text=True, env=env, cwd=project, timeout=2)
        assert p.returncode == 0 and not p.stderr and 'PHP 經驗' in p.stdout, p
    elif case == 'stdin-idle':
        with subprocess.Popen(['bash', str(script)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=env, cwd=project) as process:
            start = time.monotonic()
            process.wait(timeout=1)
            elapsed = time.monotonic() - start
            out, err = process.communicate(timeout=1)
            assert elapsed < 1 and process.returncode == 0 and not err and 'PHP 經驗' in out, (elapsed, out, err)
    else:
        raise AssertionError(case)
print('PASS recall ' + case)
PY
if [[ $# == 0 ]]; then
    for slice in budget errors formats containment stdin stdin-delay stdin-closed stdin-idle; do
        bash "$0" "$slice"
    done
fi
