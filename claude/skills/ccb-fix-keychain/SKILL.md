---
name: ccb-fix-keychain
description: >-
  Fix "no keychain found" error when running /login inside a CCB agent pane.
  Creates Library/Keychains symlinks in each claude and agy agent's isolated HOME so macOS
  Keychain is accessible during OAuth login. Also fixes codex auth isolation: sets
  inherit_auth: false and clears stale shared auth.json so each codex agent gets its own token.
  Triggers on: ccb-fix-keychain, keychain, 鑰匙圈, login failed, no keychain, ccb login error.
  Examples: "/ccb-fix-keychain".
---

# CCB Fix Keychain

## 問題 1：macOS Keychain 找不到

CCB 為每個 agent 建立隔離 HOME，若 `Library/Keychains/` 不存在，任何呼叫 macOS Keychain API 的動作都會失敗：
- **claude** agent（`provider-state/claude/home/`）：`/login` 找不到 `login.keychain-db`
- **agy** agent（`provider-runtime/agy/home/`）：儲存 antigravity 憑證時跳出「找不到鑰匙圈來儲存antigravity」

## 問題 2：Codex refresh_token 衝突

codex 使用 OAuth refresh_token（單次有效）。CCB 預設 `inherit_auth: true`，啟動時把 `~/.codex/auth.json`
複製到每個 codex agent 的隔離 HOME，導致多個 agent 共用同一個 refresh_token。
第一個 agent 刷新後，其餘 agent 的 token 即失效，出現：
> "Your access token could not be refreshed because your refresh token was already used."

## Provider 適用範圍

| Provider | Keychain 修復 | Auth 隔離 | 隔離 HOME 路徑 |
|----------|:------------:|:---------:|---------------|
| `claude` | ✅ | — | `provider-state/claude/home/` |
| `agy`    | ✅ | — | `provider-runtime/agy/home/`  |
| `codex`  | ❌ | ✅ | `provider-state/codex/home/`  |
| `gemini` | ❌ | — | 純檔案機制 |

## 執行步驟

1. 用 `dscl` 取得真實用戶家目錄（`$HOME` 在 CCB session 內可能是隔離 HOME，不可直接用）
2. 掃描 `.ccb/agents/*/agent.json`，依 provider 各別處理：
   - `claude` / `agy`：建立 `Library/Keychains` → `{REAL_HOME}/Library/Keychains` symlink
   - `codex`：將 `agent.json` 中 `inherit_auth` 改為 `false`，並清除隔離 HOME 內的舊 `auth.json`
3. 告知用戶 codex agent 需在各自 pane 內執行 `/login`

## 實作

```bash
REAL_HOME=$(dscl . -read /Users/$(id -un) NFSHomeDirectory 2>/dev/null | awk '{print $2}')
[ -z "$REAL_HOME" ] && REAL_HOME="/Users/$(id -un)"

CCB_ROOT="$(pwd)/.ccb"

if [ ! -d "$CCB_ROOT/agents" ]; then
  echo "⚠️  .ccb/agents/ 尚未初始化。請先執行 ccb 啟動一次，再重新執行 /ccb-fix-keychain。"
  exit 0
fi

CODEX_AGENTS=()

for agent_json in "$CCB_ROOT"/agents/*/agent.json; do
  [ -f "$agent_json" ] || continue
  agent_dir="$(dirname "$agent_json")"
  agent_name="$(basename "$agent_dir")"
  provider="$(python3 -c "import json; print(json.load(open('$agent_json')).get('provider',''))" 2>/dev/null)"

  case "$provider" in
    claude)
      home_path="$agent_dir/provider-state/claude/home"
      lib="$home_path/Library"
      mkdir -p "$lib"
      ln -sfn "$REAL_HOME/Library/Keychains" "$lib/Keychains"
      echo "🔑 $agent_name ($provider) → $(readlink "$lib/Keychains")"
      ;;
    agy)
      home_path="$agent_dir/provider-runtime/agy/home"
      lib="$home_path/Library"
      mkdir -p "$lib"
      ln -sfn "$REAL_HOME/Library/Keychains" "$lib/Keychains"
      echo "🔑 $agent_name ($provider) → $(readlink "$lib/Keychains")"
      ;;
    codex)
      # 將 inherit_auth 改為 false（防止 CCB 覆蓋隔離的 auth.json）
      python3 - "$agent_json" <<'PYEOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    d = json.load(f)
if d.get('provider_profile', {}).get('inherit_auth') != False:
    d['provider_profile']['inherit_auth'] = False
    with open(path, 'w') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print(f"  ✎ {path}: inherit_auth → false")
else:
    print(f"  ✓ {path}: inherit_auth 已是 false")
PYEOF
      # 清除隔離 HOME 內的共享舊 auth.json（單次 refresh_token 已失效）
      isolated_auth="$agent_dir/provider-state/codex/home/auth.json"
      if [ -f "$isolated_auth" ]; then
        rm "$isolated_auth"
        echo "  🗑  $agent_name: 已清除舊 auth.json"
      fi
      CODEX_AGENTS+=("$agent_name")
      ;;
  esac
done

if [ ${#CODEX_AGENTS[@]} -gt 0 ]; then
  echo ""
  echo "⚠️  以下 codex agent 需在各自 pane 內重新登入："
  for name in "${CODEX_AGENTS[@]}"; do
    echo "    $name pane → /login"
  done
fi
```

## 注意

- **不可用 `$HOME`** 取 Keychains 路徑：Claude Code session 內 `$HOME` 已被設為 agent 隔離 HOME，會建出循環 symlink。必須用 `dscl` 或 `/Users/$(id -un)` 取得真實路徑。
- symlink 必須用絕對路徑，不可用 `~`
- codex `inherit_auth: false` 設定後，CCB 重啟不會再覆蓋隔離的 `auth.json`，token 刷新各自獨立。
- CCB 每次重建 runtime（`ccb -n`）不會破壞 `provider-state/` 或 `provider-runtime/` 目錄，修復持久有效。
