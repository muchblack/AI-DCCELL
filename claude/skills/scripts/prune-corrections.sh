#!/usr/bin/env bash
# prune-corrections.sh — Corrections pool 剪枝
# 用法: prune-corrections.sh [CORRECTIONS_FILE]
#   預設: ~/.claude/skills/memory/corrections.jsonl
# 規則:
#   1. severity=critical → 永久保留
#   2. severity=minor 超過 90 天 → 標記過期移除
#   3. 總量上限 100 筆（FIFO 淘汰，critical 豁免）
# 輸出: JSON { total_before, total_after, pruned, kept_critical }
# Exit: 0

set -uo pipefail

CORRECTIONS_FILE="${1:-$HOME/.claude/skills/memory/corrections.jsonl}"

if [ ! -f "$CORRECTIONS_FILE" ]; then
  echo '{"total_before":0,"total_after":0,"pruned":0,"kept_critical":0}'
  exit 0
fi

export CORRECTIONS_FILE_PY="$CORRECTIONS_FILE"
python3 << 'PYEOF'
import json, sys, os
from datetime import datetime, timedelta, timezone

corrections_file = os.environ["CORRECTIONS_FILE_PY"]

entries = []
with open(corrections_file, "r") as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass

total_before = len(entries)
now = datetime.now(timezone.utc)
cutoff = now - timedelta(days=90)
max_total = 100

# Step 1: remove minor entries older than 90 days
kept = []
pruned_expired = 0
for e in entries:
    ts_str = e.get("timestamp", "")
    severity = e.get("severity", "minor")

    if severity == "critical":
        kept.append(e)
        continue

    if severity == "minor" and ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts < cutoff:
                pruned_expired += 1
                continue
        except (ValueError, TypeError):
            pass

    kept.append(e)

# Step 2: FIFO cap at max_total (critical exempt)
critical = [e for e in kept if e.get("severity") == "critical"]
non_critical = [e for e in kept if e.get("severity") != "critical"]

if len(critical) + len(non_critical) > max_total:
    allowed_non_critical = max_total - len(critical)
    if allowed_non_critical < 0:
        allowed_non_critical = 0
    pruned_fifo = len(non_critical) - allowed_non_critical
    non_critical = non_critical[-allowed_non_critical:] if allowed_non_critical > 0 else []
else:
    pruned_fifo = 0

final = critical + non_critical
# Sort by timestamp
final.sort(key=lambda e: e.get("timestamp", ""), reverse=False)

total_after = len(final)
total_pruned = total_before - total_after

# Write back
with open(corrections_file, "w") as f:
    for e in final:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

result = {
    "total_before": total_before,
    "total_after": total_after,
    "pruned": total_pruned,
    "kept_critical": len(critical)
}
print(json.dumps(result))
PYEOF
