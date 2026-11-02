import json
import fcntl
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().with_name('mem-digest.py')
END = 1800000000000


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.state = self.home / '.local/share/mem-review'
        self.vault = self.home / 'vault'
        self.vault.mkdir()
        (self.vault / 'note.md').write_text('不得改動')
        self.fake = self.home / 'fake'
        self.fake.write_text('#!/usr/bin/env python3\nimport json,os,pathlib,sys\nhome=pathlib.Path(os.environ["HOME"])\nif "-p" in sys.argv:\n (home/"prompt").write_text(sys.stdin.read())\n (home/"claude-args").write_text(json.dumps(sys.argv[1:]))\n print(os.environ.get("FAKE_OUTPUT", "{\\"items\\":[]}"))\n sys.exit(int(os.environ.get("FAKE_EXIT", "0")))\nelse:\n (home/"notification").write_text(json.dumps(sys.argv[1:]))\n sys.exit(int(os.environ.get("NOTIFY_EXIT", "0")))\n')
        self.fake.chmod(0o700)
        self.env = dict(os.environ, HOME=str(self.home), OBSIDIAN_VAULT=str(self.vault), MEM_DIGEST_CLAUDE_BIN=str(self.fake), MEM_DIGEST_HERDR_BIN=str(self.fake), PYTHONDONTWRITEBYTECODE='1')

    def history(self, name, entries):
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else item for item in entries) + '\n')

    def seed(self):
        self.history('.claude/history.jsonl', [{'display': '偏好繁中', 'timestamp': END-1000, 'project': 'alpha'}])

    def run_cli(self, *args, end=END):
        # 只固定時鐘；仍透過 argparse 和公開 CLI 執行。
        wrapper = 'import runpy,sys,time; now=float(sys.argv.pop(1)); time.time=lambda:now; script=sys.argv.pop(1); sys.argv[0]=script; runpy.run_path(script,run_name="__main__")'
        return subprocess.run([sys.executable, '-B', '-c', wrapper, str(end / 1000), str(SCRIPT), '--home', str(self.home), *args], env=self.env, capture_output=True, text=True, timeout=10)

    def item(self, habit='繁中', count=1, forever=False):
        return {'habit': habit, 'evidence': ['原話 ~/.claude/projects/private/log.jsonl /mnt/d/user/.claude/projects/private/log.jsonl'], 'source_project': '去識別化專案', 'repeat_count': count, 'explicit_forever': forever}

    def drafts(self):
        return sorted(self.state.glob('*.md'))

    def test_sources(self):
        self.history('.claude/history.jsonl', [
            {'display':'Claude 親自輸入 [Pasted text #1 +9 lines]', 'pastedContents': {'1':'機密貼文'}, 'project':'php', 'timestamp':END-1500},
            {'display':'  dispatch_id: worker', 'timestamp':END-1000},
            {'display':'[mem-digest] 自己的 prompt', 'timestamp':END-1000},
            {'display':'[Pasted text #2 +10 lines]', 'timestamp':END-1000},
            {'display':'舊資料', 'timestamp':END-86400001},
            {'display':'未來資料', 'timestamp':END}, 'broken JSON'])
        self.history('.codex/history.jsonl', [
            {'text':'Codex 輸入', 'session_id':'known', 'ts':(END-1000)//1000},
            {'text':'無對應 session', 'session_id':'missing', 'ts':(END-1000)//1000},
            {'text':'無效 session', 'session_id':[], 'ts':(END-1000)//1000},
            {'text':'無效時間', 'ts':10**1000}])
        self.history('.codex/sessions/2026/rollout-known.jsonl', [{'type':'session_meta', 'payload':{'id':'known', 'cwd':'node'}}])
        self.history('.gemini/antigravity-cli/history.jsonl', [{'display':'agy 輸入', 'workspace':'go', 'timestamp':END-500}])
        before = {str(p.relative_to(self.home)): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        p = self.run_cli('--dry-run')
        self.assertEqual(p.returncode, 0, p.stderr)
        entries = json.loads(p.stdout)
        self.assertEqual(len(entries), 4)
        self.assertEqual({e['project'] for e in entries}, {'php', 'node', 'go', '未知'})
        self.assertEqual({e['source'] for e in entries}, {'claude', 'codex', 'agy'})
        self.assertTrue(all(END-86400000 <= e['timestamp'] < END for e in entries))
        self.assertNotIn('Pasted', p.stdout)
        self.assertNotIn('機密貼文', p.stdout)
        self.assertEqual(before, {str(p.relative_to(self.home)): p.read_bytes() for p in self.home.rglob('*') if p.is_file()})

    def test_overlap(self):
        self.seed()
        self.state.mkdir(parents=True)
        with (self.state / 'digest.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            p = self.run_cli()
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertFalse((self.home / 'prompt').exists())
            self.assertFalse((self.state / 'cursor.json').exists())
            self.assertFalse(self.drafts())

    def test_cursor(self):
        self.seed()
        self.history('.codex/history.jsonl', [{'text':'同秒', 'ts':END//1000, 'session_id':'unknown'}])
        self.env['FAKE_OUTPUT'] = json.dumps({'items':[self.item()]})
        self.assertEqual(self.run_cli(end=END+999).returncode, 0)
        self.assertNotIn('同秒', (self.home / 'prompt').read_text())
        self.assertEqual(json.loads((self.state / 'cursor.json').read_text()), END)
        self.assertEqual(self.run_cli(end=END+1000).returncode, 0)
        self.assertIn('同秒', (self.home / 'prompt').read_text())
        self.assertEqual(len(self.drafts()), 2)
        previous = (self.home / 'prompt').read_bytes()
        self.assertEqual(self.run_cli(end=END+2000).returncode, 0)
        self.assertEqual(previous, (self.home / 'prompt').read_bytes())
        self.assertEqual(len(self.drafts()), 2)
        self.history('.claude/history.jsonl', [{'display':'失敗重試', 'timestamp':END+2000}])
        cursor = (self.state / 'cursor.json').read_bytes()
        for output, code in [('not JSON', '0'), ('{"items":[]}', '1'), ('{"items":[{"habit":"不完整"}]}', '0')]:
            self.env.update(FAKE_OUTPUT=output, FAKE_EXIT=code)
            p = self.run_cli(end=END+3000)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual((self.state / 'cursor.json').read_bytes(), cursor)
            self.assertEqual(len(self.drafts()), 2)

    def test_empty(self):
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertEqual(json.loads((self.state / 'cursor.json').read_text()), END)
        self.assertFalse(self.drafts())
        self.assertFalse((self.home / 'notification').exists())
        self.assertFalse((self.home / 'prompt').exists())
        self.history('.claude/history.jsonl', [{'display':'新資料', 'timestamp':END}])
        self.assertEqual(self.run_cli(end=END+1000).returncode, 0)
        self.assertEqual(json.loads((self.state / 'cursor.json').read_text()), END+1000)
        self.assertFalse(self.drafts())
        self.assertFalse((self.home / 'notification').exists())

    def test_classification(self):
        self.seed()
        self.env['FAKE_OUTPUT'] = json.dumps({'items':[self.item('單次'), self.item('重複', 2), self.item('永遠', 1, True)]})
        self.env['NOTIFY_EXIT'] = '1'
        p = self.run_cli()
        self.assertEqual(p.returncode, 0, p.stderr)
        text = self.drafts()[0].read_text()
        observations = text.split('## 觀察')[1]
        candidates = text.split('## 候選')[1].split('## 觀察')[0]
        self.assertIn('單次', observations)
        self.assertNotIn('單次', candidates)
        self.assertIn('重複', candidates)
        self.assertIn('永遠', candidates)
        self.assertNotIn('.claude/projects', text)
        self.assertIn('原話', text)
        prompt = (self.home / 'prompt').read_text()
        self.assertTrue(prompt.startswith('[mem-digest]'))
        self.assertIn('資料', prompt)
        self.assertIn('忽略', prompt)
        self.assertIn('```', prompt)
        self.assertEqual(json.loads((self.home / 'claude-args').read_text()), ['-p', '--model', 'sonnet'])
        args = json.loads((self.home / 'notification').read_text())
        self.assertEqual(args[:2], ['notification', 'show'])
        self.assertIn(str(self.drafts()[0]), args[-1])
        self.assertIn('3', args[-1])
        self.assertNotIn('單次', args[-1])
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)
        for path in self.state.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600, str(path))

    def test_vault_unchanged(self):
        self.seed()
        self.env['FAKE_OUTPUT'] = json.dumps({'items':[self.item()]})
        before = {str(p.relative_to(self.vault)): p.read_bytes() for p in self.vault.rglob('*') if p.is_file()}
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertTrue(self.drafts())
        self.assertEqual(before, {str(p.relative_to(self.vault)): p.read_bytes() for p in self.vault.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
