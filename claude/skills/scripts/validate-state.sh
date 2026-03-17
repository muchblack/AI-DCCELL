#!/usr/bin/env bash
# validate-state.sh — .ccb/state.json schema validation + auto-repair
# 用法: validate-state.sh [STATE_FILE]
#   預設: .ccb/state.json
# 功能:
#   1. 驗證必要欄位存在
#   2. 偵測孤兒 cursor（指向不存在的 step/substep）
#   3. 自動修復可修復的問題
#   4. 修復前自動備份（checkpoint）
# 輸出: JSON { valid, errors[], warnings[], repaired[] }
# Exit: 0=valid, 1=repaired, 2=unrecoverable

set -uo pipefail

STATE_FILE="${1:-.ccb/state.json}"
CHECKPOINT_DIR="$(dirname "$STATE_FILE")/.checkpoints"
MAX_CHECKPOINTS=10

if [ ! -f "$STATE_FILE" ]; then
  echo '{"valid":false,"errors":["state file not found"],"warnings":[],"repaired":[]}'
  exit 2
fi

# 確保有 python3 或 jq
if ! command -v python3 >/dev/null 2>&1 && ! command -v jq >/dev/null 2>&1; then
  echo '{"valid":false,"errors":["neither python3 nor jq available"],"warnings":[],"repaired":[]}'
  exit 2
fi

# Python 實作（jq 做不好複雜修復邏輯）
export STATE_FILE_PY="$STATE_FILE"
python3 << 'PYEOF'
import json, sys, os, shutil, glob
from datetime import datetime

state_file = os.environ["STATE_FILE_PY"]
checkpoint_dir = os.path.join(os.path.dirname(state_file) or ".", ".checkpoints")
max_checkpoints = 10

errors = []
warnings = []
repaired = []

try:
    with open(state_file, "r") as f:
        state = json.load(f)
except json.JSONDecodeError as e:
    print(json.dumps({"valid": False, "errors": [f"invalid JSON: {e}"], "warnings": [], "repaired": []}))
    sys.exit(2)
except Exception as e:
    print(json.dumps({"valid": False, "errors": [str(e)], "warnings": [], "repaired": []}))
    sys.exit(2)

needs_write = False

# --- 必要欄位檢查 ---
required_top = ["taskName", "objective", "steps", "current"]
for field in required_top:
    if field not in state:
        if field == "taskName":
            state["taskName"] = "unnamed"
            repaired.append(f"added missing field: {field}")
            needs_write = True
        elif field == "objective":
            state["objective"] = {"goal": "", "nonGoals": "", "doneWhen": ""}
            repaired.append(f"added missing field: {field}")
            needs_write = True
        elif field == "steps":
            errors.append(f"missing critical field: {field}")
        elif field == "current":
            state["current"] = {"type": "none", "stepIndex": None, "subIndex": None}
            repaired.append(f"added missing field: {field}")
            needs_write = True

if "objective" in state:
    obj = state["objective"]
    for f in ["goal", "nonGoals", "doneWhen"]:
        if f not in obj:
            obj[f] = ""
            repaired.append(f"added missing objective.{f}")
            needs_write = True

# --- steps 結構驗證 ---
if "steps" in state:
    steps = state["steps"]
    if not isinstance(steps, list):
        errors.append("steps is not an array")
    else:
        for i, step in enumerate(steps):
            # 必要欄位
            if "index" not in step:
                step["index"] = i
                repaired.append(f"step[{i}]: added missing index")
                needs_write = True
            if "title" not in step:
                warnings.append(f"step[{i}]: missing title")
            if "status" not in step:
                step["status"] = "todo"
                repaired.append(f"step[{i}]: added missing status (default: todo)")
                needs_write = True
            if "attempts" not in step:
                step["attempts"] = 0
                repaired.append(f"step[{i}]: added missing attempts")
                needs_write = True
            if "substeps" not in step:
                step["substeps"] = []
                repaired.append(f"step[{i}]: added missing substeps")
                needs_write = True

            # substeps 結構
            if isinstance(step.get("substeps"), list):
                for j, sub in enumerate(step["substeps"]):
                    if "status" not in sub:
                        sub["status"] = "todo"
                        repaired.append(f"step[{i}].substep[{j}]: added missing status")
                        needs_write = True

# --- 孤兒 cursor 偵測 ---
if "current" in state and "steps" in state and isinstance(state["steps"], list):
    cur = state["current"]
    steps = state["steps"]
    step_count = len(steps)

    if cur.get("type") == "step":
        si = cur.get("stepIndex")
        if si is None or not isinstance(si, int) or si < 0 or si >= step_count:
            # 找第一個非 done 的 step
            fixed = False
            for idx, s in enumerate(steps):
                if s.get("status") != "done":
                    cur["stepIndex"] = idx
                    cur["subIndex"] = None
                    repaired.append(f"orphan cursor: stepIndex {si} → {idx}")
                    needs_write = True
                    fixed = True
                    break
            if not fixed:
                cur["type"] = "none"
                cur["stepIndex"] = None
                cur["subIndex"] = None
                repaired.append("orphan cursor: all steps done, set type=none")
                needs_write = True

    elif cur.get("type") == "substep":
        si = cur.get("stepIndex")
        subi = cur.get("subIndex")
        if si is None or not isinstance(si, int) or si < 0 or si >= step_count:
            repaired.append(f"orphan cursor: invalid stepIndex {si} for substep")
            cur["type"] = "step"
            cur["stepIndex"] = 0
            cur["subIndex"] = None
            needs_write = True
        elif subi is not None:
            substeps = steps[si].get("substeps", [])
            if not isinstance(subi, int) or subi < 0 or subi >= len(substeps):
                repaired.append(f"orphan cursor: subIndex {subi} out of range")
                cur["subIndex"] = 0 if substeps else None
                if not substeps:
                    cur["type"] = "step"
                needs_write = True

# --- 額外欄位（optional） ---
if "constraints" not in state:
    warnings.append("missing optional field: constraints")
if "finalDone" not in state:
    warnings.append("missing optional field: finalDone")
if "context" not in state:
    warnings.append("missing optional field: context")

# --- 寫回修復 ---
if needs_write and not errors:
    # checkpoint 備份
    os.makedirs(checkpoint_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cp_path = os.path.join(checkpoint_dir, f"state_{ts}.json")
    shutil.copy2(state_file, cp_path)

    # FIFO: 保留最新 MAX_CHECKPOINTS 份
    cps = sorted(glob.glob(os.path.join(checkpoint_dir, "state_*.json")))
    while len(cps) > max_checkpoints:
        os.remove(cps.pop(0))

    # 寫回
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")

# --- 結果 ---
has_errors = len(errors) > 0
has_repairs = len(repaired) > 0

result = {
    "valid": not has_errors and not has_repairs,
    "errors": errors,
    "warnings": warnings,
    "repaired": repaired
}

print(json.dumps(result, ensure_ascii=False))

if has_errors:
    sys.exit(2)
elif has_repairs:
    sys.exit(1)
else:
    sys.exit(0)
PYEOF
