# CCB Init — Auth Fix（Keychain + Codex 隔離）

Runs automatically after config is written (Step 9 of config-flow).
Can also run standalone via `/ccb-fix-keychain` or `/ccb-init --skip-config`.

## 問題 1：macOS Keychain 找不到（claude / agy）

CCB 為每個 agent 建立隔離 HOME。若該 HOME 的 `Library/` 缺少 `Keychains/`，
任何呼叫 macOS Keychain API（儲存金鑰、認證憑證）的動作都會失敗：
- claude：`security find-generic-password` 找不到 `login.keychain-db`
- agy：嘗試儲存 antigravity 憑證時跳出「找不到鑰匙圈來儲存antigravity」

## 問題 2：Codex refresh_token 衝突（codex）

codex 使用 OAuth refresh_token（單次有效）。CCB 預設 `inherit_auth: true`，
啟動時把 `~/.codex/auth.json` 複製到每個 codex agent 的隔離 HOME，
導致多個 agent 共用同一個 refresh_token。第一個 agent 刷新後其餘均失效：
> "Your access token could not be refreshed because your refresh token was already used."

## Provider 適用範圍

| Provider | Keychain 修復 | Auth 隔離 | 隔離 HOME 路徑 |
|----------|:------------:|:---------:|---------------|
| `claude` | ✅ | — | `provider-state/claude/home/` |
| `agy`    | ✅ | — | `provider-runtime/agy/home/`  |
| `codex`  | ❌ | ✅ | `provider-state/codex/home/`  |
| `gemini` | ❌ | — | 純檔案機制 |

## 執行邏輯

```bash
REAL_HOME=$(dscl . -read /Users/$(id -un) NFSHomeDirectory 2>/dev/null | awk '{print $2}')
[ -z "$REAL_HOME" ] && REAL_HOME="/Users/$(id -un)"

CCB_ROOT="$(pwd)/.ccb"

if [ ! -d "$CCB_ROOT/agents" ]; then
  echo "⚠️  .ccb/agents/ 不存在，請先執行 ccb 啟動讓 agent 目錄初始化"
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
      # 清除隔離 HOME 內的舊 auth.json（共享 refresh_token 已失效）
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

## 注意事項

- **不可用 `$HOME`** 取 Keychains 路徑：Claude Code session 內 `$HOME` 可能已被設為 agent 隔離 HOME。
  必須用 `dscl` 或 `/Users/$(id -un)` 取得真實用戶家目錄。
- `.ccb/agents/` 目錄在 **第一次 `ccb` 啟動後** 才存在。
  若 ccb-init 後還沒啟動過 CCB → agent 目錄不存在 → 此修復無法執行。
  遇到此情況，告知用戶：先 `ccb` 啟動一次，再手動執行 `/ccb-fix-keychain`。
- codex `inherit_auth: false` 設定後，CCB 重啟不會再覆蓋隔離的 `auth.json`，各 agent token 刷新獨立。

## 輸出格式

成功：
```
🔑 main (claude)     → /Users/{user}/Library/Keychains
🔑 reviewer1 (agy)   → /Users/{user}/Library/Keychains
  ✎ .ccb/agents/reviewer2/agent.json: inherit_auth → false
  🗑  reviewer2: 已清除舊 auth.json
  ✎ .ccb/agents/worker1/agent.json: inherit_auth → false
  🗑  worker1: 已清除舊 auth.json

⚠️  以下 codex agent 需在各自 pane 內重新登入：
    reviewer2 pane → /login
    worker1 pane → /login
```

agent 目錄不存在：
```
⚠️  .ccb/agents/ 尚未初始化。請先執行 ccb 啟動一次，再執行 /ccb-fix-keychain。
```
