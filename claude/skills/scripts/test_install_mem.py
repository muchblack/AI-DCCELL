import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[2]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home ' 測試"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1')

    def run_install(self):
        return subprocess.run(['python3', str(SCRIPTS / 'install-mem.py'), '--home', str(self.home)], env=self.env, capture_output=True, text=True)

    def test_merge(self):
        paths = ['.claude/settings.json', '.codex/hooks.json', '.gemini/config/hooks.json']
        originals = [
            {'theme': 'dark', 'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': 'old'}]}]}},
            {'extra': 42, 'hooks': {'SessionStart': [{'hooks': [{'command': 'old'}]}], 'Stop': []}},
            {'custom': {'SessionStart': [{'command': 'old'}]}, 'mem': {'Stop': [{'command': 'keep'}]}},
        ]
        for name, obj in zip(paths, originals):
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(obj))
        p = self.run_install()
        self.assertEqual(p.returncode, 0, p.stderr)
        contents = [(self.home / name).read_bytes() for name in paths]
        for i, content in enumerate(contents):
            obj = json.loads(content)
            if i < 2:
                self.assertEqual(obj['hooks']['SessionStart'][0], originals[i]['hooks']['SessionStart'][0])
                group = obj['hooks']['SessionStart'][-1]
                if i == 0:
                    self.assertEqual(group['matcher'], '^(startup|resume|clear|compact|fork)$')
                hook = group['hooks'][0]
                self.assertEqual(obj.get('theme', obj.get('extra')), 'dark' if i == 0 else 42)
            else:
                self.assertEqual(obj['custom'], originals[i]['custom'])
                self.assertEqual(obj['mem']['Stop'], originals[i]['mem']['Stop'])
                hook = obj['mem']['SessionStart'][0]
            import shlex
            expected = "bash '" + str(self.home / '.claude/skills/scripts/mem-recall.sh').replace("'", "'\"'\"'") + "' --format " + ['claude', 'codex', 'agy'][i]
            self.assertEqual(hook, {'type': 'command', 'command': expected, 'timeout': 5})
            self.assertEqual(shlex.split(hook['command'])[1], str(self.home / '.claude/skills/scripts/mem-recall.sh'))
        units = self.home / '.config/systemd/user'
        before = {p.name: p.read_bytes() for p in units.iterdir()}
        self.assertIn(b'OnCalendar=Mon..Fri 18:00', before['mem-digest.timer'])
        self.assertIn(b'Persistent=true', before['mem-digest.timer'])
        self.assertIn(b'Type=oneshot', before['mem-digest.service'])
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(contents, [(self.home / name).read_bytes() for name in paths])
        self.assertEqual(before, {p.name: p.read_bytes() for p in units.iterdir()})
        (self.home / paths[0]).write_text('{ invalid')
        p = self.run_install()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('settings.json', p.stderr)
        self.assertEqual((self.home / paths[0]).read_text(), '{ invalid')
        self.assertEqual(contents[1:], [(self.home / name).read_bytes() for name in paths[1:]])

    def test_shared_and_bootstrap(self):
        p = subprocess.run(['bash', str(REPO / 'scripts/sync-shared-skills.sh')], env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        for directory in ['.agents/skills', '.gemini/config/skills']:
            link = self.home / directory / 'mem'
            self.assertTrue(link.is_symlink(), directory)
            self.assertEqual(link.resolve(), REPO / 'claude/skills/mem')
        self.assertEqual(subprocess.run(['bash', '-n', str(REPO / 'bootstrap.sh')], capture_output=True).returncode, 0)
        bootstrap = (REPO / 'bootstrap.sh').read_text()
        self.assertIn('install-mem.py', bootstrap)
        self.assertRegex(bootstrap, r'if ! python3 "\$\{SOURCE_DIR\}/skills/scripts/install-mem\.py"; then\n\s+echo .*警告.*\nfi')
        for step in ['systemctl --user daemon-reload', 'systemctl --user enable --now mem-digest.timer', 'loginctl enable-linger']:
            self.assertIn(step, bootstrap)

    def test_preserve_modes_and_symlinks(self):
        regular = self.home / '.codex/hooks.json'
        regular.parent.mkdir()
        regular.write_text('{}')
        regular.chmod(0o644)
        target = self.home / 'shared-agy.json'
        target.write_text('{"custom": 42}')
        target.chmod(0o640)
        link = self.home / '.gemini/config/hooks.json'
        link.parent.mkdir(parents=True)
        link.symlink_to('../../shared-agy.json')
        original_link = os.readlink(link)
        p = self.run_install()
        self.assertEqual(p.returncode, 0, p.stderr)
        with self.subTest(check='regular-mode'):
            self.assertEqual(stat.S_IMODE(regular.stat().st_mode), 0o644)
        with self.subTest(check='symlink'):
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), original_link)
            self.assertIn('SessionStart', json.loads(target.read_text())['mem'])
            self.assertEqual(json.loads(target.read_text())['custom'], 42)
        with self.subTest(check='target-mode'):
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
        before = [regular.read_bytes(), target.read_bytes()]
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(before, [regular.read_bytes(), target.read_bytes()])

    def test_path_limited_commit(self):
        skill = (REPO / 'claude/skills/mem/SKILL.md').read_text()
        command = 'git -C "$VAULT" commit -m "記憶：更新" -- "myWiki/20-領域/AI協作記憶"'
        self.assertIn(command, skill)
        vault = self.home / 'vault'
        vault.mkdir()
        def git(*args):
            return subprocess.run(['git', '-C', str(vault), *args], check=True, capture_output=True, text=True).stdout
        git('init', '-q')
        git('config', 'user.email', 'test@example.invalid')
        git('config', 'user.name', '測試')
        git('commit', '--allow-empty', '-qm', '初始')
        (vault / 'other.md').write_text('其他筆記')
        memory = vault / 'myWiki/20-領域/AI協作記憶'
        memory.mkdir(parents=True)
        (memory / '使用習慣.md').write_text('記憶')
        git('add', '.')
        p = subprocess.run(['bash', '-c', command], env=dict(self.env, VAULT=str(vault)), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(git('diff', '--cached', '--name-only').strip(), 'other.md')
        self.assertNotIn('other.md', git('show', '--pretty=', '--name-only', 'HEAD'))


if __name__ == '__main__':
    unittest.main()
