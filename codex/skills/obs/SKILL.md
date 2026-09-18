---
name: obs
description: 操作 Obsidian vault，包括建立、讀取、搜尋、寫入、Git 同步、PARA 整理、AI 編譯、知識連結、圖譜與健康檢查。當使用者提到 Obsidian、vault、筆記、wiki、收件匣、知識庫，或要求 compile、link、graph、health 時使用。
metadata:
  short-description: Obsidian vault 操作
---

# Obsidian 知識庫操作

使用目前可用的檔案與 shell 工具操作 Obsidian vault。明確呼叫時使用 `$obs <動作> [參數]`；自然語言請求符合描述時也可啟用。

## 共通規則

1. 從使用者提示解析動作、參數與可選的 `--vault <path>`；不要依賴 Claude Code 的 `$ARGUMENTS`。
2. Vault 優先順序為 `--vault`、`$OBSIDIAN_VAULT`、`~/.zshrc` 中的 `OBSIDIAN_VAULT`。無法解析時先詢問路徑。
3. 先解析並驗證實際路徑，所有相對路徑必須留在 vault 內。不得將 `~`、未解析變數或廣泛 glob 當成寫入、移動或刪除目標。
4. 搜尋優先使用 `rg`；修改既有筆記前先讀取內容，並使用 `apply_patch`。建立目錄或執行專用腳本時可使用 shell。
5. 讀取、搜尋、狀態與分析可直接執行。建立、寫入、移動、改寫或產生報告，只能作用於使用者指定或該動作明確涵蓋的 vault 範圍。
6. `pull`、`commit`、`push` 只在使用者明確要求同步，或已明確同意該操作會自動同步時執行。推送前先呈報將提交的變更；遇到衝突或非預期變更時停止並說明。
7. `/mnt/d/company/company` 及其子目錄不用 Git 管理，永遠略過同步，不嘗試初始化 repository。
8. 以現代繁體中文簡潔回報，使用相對於 vault 的路徑，不使用固定稱謂。

## 動作路由

- `new`、`search`、`read`、`write`、`sync`、`sort`：讀取 [references/core.md](references/core.md)。
- `compile`、`link`、`health`：讀取 [references/knowledge.md](references/knowledge.md)。
- `graph`：讀取 [references/graph.md](references/graph.md)。

只讀取目前動作需要的 reference。若請求跨越多個動作，再載入相應檔案。
