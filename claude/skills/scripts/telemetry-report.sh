#!/usr/bin/env bash
# telemetry-report.sh — Telemetry 彙整報告
# 用法: telemetry-report.sh [--days N]
#   --days N: 只統計最近 N 天 (預設 30)
# 輸出: 結構化報告（per-skill + per-provider 統計）

set -uo pipefail

TELEMETRY_FILE="${TELEMETRY_FILE:-$HOME/.claude/skills/memory/telemetry.jsonl}"
DAYS="${2:-30}"

if [ "${1:-}" = "--days" ]; then
  DAYS="$2"
fi

if [ ! -f "$TELEMETRY_FILE" ]; then
  echo "No telemetry data found."
  exit 0
fi

export TELEMETRY_FILE DAYS
python3 << 'PYEOF'
import json, os, sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

telemetry_file = os.environ["TELEMETRY_FILE"]
days = int(os.environ.get("DAYS", "30"))
cutoff = datetime.now(timezone.utc) - timedelta(days=days)

entries = []
with open(telemetry_file, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
            if ts >= cutoff:
                entries.append(e)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

if not entries:
    print(f"No telemetry data in the last {days} days.")
    sys.exit(0)

# Per-skill stats
skill_stats = defaultdict(lambda: {"total": 0, "ok": 0, "passable": 0, "garbage": 0, "error": 0, "timeout": 0, "fallback": 0, "durations": []})
provider_stats = defaultdict(lambda: {"total": 0, "ok": 0, "error": 0, "timeout": 0, "fallback": 0, "durations": []})

for e in entries:
    skill = e.get("skill", "unknown")
    provider = e.get("provider", "unknown")
    result = e.get("result", "unknown")
    duration = e.get("duration_ms", 0)
    fallback = e.get("fallback", False)

    s = skill_stats[skill]
    s["total"] += 1
    if result in s:
        s[result] += 1
    if fallback:
        s["fallback"] += 1
    if duration > 0:
        s["durations"].append(duration)

    p = provider_stats[provider]
    p["total"] += 1
    if result == "ok" or result == "passable":
        p["ok"] += 1
    elif result == "error":
        p["error"] += 1
    elif result == "timeout":
        p["timeout"] += 1
    if fallback:
        p["fallback"] += 1
    if duration > 0:
        p["durations"].append(duration)

def avg(lst):
    return int(sum(lst) / len(lst)) if lst else 0

def pct(n, total):
    return f"{n/total*100:.0f}%" if total > 0 else "N/A"

print(f"# Telemetry Report (last {days} days)")
print(f"Total invocations: {len(entries)}")
print()

print("## Per Skill")
print(f"{'Skill':<20} {'Total':>6} {'OK%':>6} {'Err%':>6} {'FB%':>6} {'Avg ms':>8}")
print("-" * 55)
for skill in sorted(skill_stats.keys()):
    s = skill_stats[skill]
    ok_count = s["ok"] + s["passable"]
    print(f"{skill:<20} {s['total']:>6} {pct(ok_count, s['total']):>6} {pct(s['error']+s['timeout'], s['total']):>6} {pct(s['fallback'], s['total']):>6} {avg(s['durations']):>8}")

print()
print("## Per Provider")
print(f"{'Provider':<15} {'Total':>6} {'OK%':>6} {'Err%':>6} {'FB%':>6} {'Avg ms':>8}")
print("-" * 50)
for provider in sorted(provider_stats.keys()):
    p = provider_stats[provider]
    print(f"{provider:<15} {p['total']:>6} {pct(p['ok'], p['total']):>6} {pct(p['error']+p['timeout'], p['total']):>6} {pct(p['fallback'], p['total']):>6} {avg(p['durations']):>8}")
PYEOF
