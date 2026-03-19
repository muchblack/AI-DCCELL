# Obsidian 知識庫操作流程

## Vault 解析（優先順序）

1. **`--vault <path>` 旗標**（最高優先）：從 `$ARGUMENTS` 提取 `--vault <path>`，展開 `~`，使用該路徑作為 Vault 根目錄
2. **`$OBSIDIAN_VAULT` 環境變數**
3. **從 `~/.zshrc` 讀取**（fallback）：
   ```bash
   VAULT="${OBSIDIAN_VAULT:-$(grep -E '^export OBSIDIAN_VAULT=' ~/.zshrc | sed 's/^export OBSIDIAN_VAULT=//' | tr -d '\"' | tr -d \"'\")}"
   ```

**注意**：使用 `--vault` 時，路徑簡寫（`inbox/`、`projects/` 等）仍然生效，但基於指定的 Vault 根目錄。若該 Vault 沒有 `myWiki/` 結構，則直接以 Vault 根目錄為基礎解析相對路徑。

**解析引數時**：先從 `$ARGUMENTS` 中提取並移除 `--vault <path>`，剩餘部分按原有邏輯解析子命令和參數。

## 子命令

### `/obs new <type> [title]` — 建立新筆記

**支援模板類型**：`daily` / `meeting` / `project` / `sop` / `til`

**執行流程**：

1. 確定 Vault 路徑（使用上方環境變數解析方式）
2. 讀取模板：`Read("$VAULT/templates/<type>.md")`
3. 替換變數：
   - `{{title}}` → 使用者提供的標題（若無，提示輸入）
   - `<% tp.date.now("YYYY-MM-DD") %>` → 當前日期
   - `<% tp.date.now("YYYY-MM-DD ddd") %>` → 當前日期含星期
4. 決定輸出路徑：
   - `daily` → `$VAULT/myWiki/00-收件匣/daily/YYYY/YYYY-MM-DD.md`
   - `meeting` → `$VAULT/myWiki/00-收件匣/<title>.md`
   - `project` → `$VAULT/myWiki/10-專案/<title>/README.md`
   - `sop` → `$VAULT/myWiki/40-標準流程/<title>.md`
   - `til` → `$VAULT/myWiki/00-收件匣/til/YYYY-MM-DD-<title>.md`
5. 用 Write 工具寫入檔案
6. 回報建立路徑
7. 自動走 `/obs sync` 流程

**範例**：

```
/obs new daily
/obs new meeting "週會"
/obs new project "API 重構"
/obs new til "Go goroutine leak"
```

---

### `/obs search <query>` — 搜尋筆記

**執行流程**：

1. 確定 Vault 路徑
2. 使用 Grep 工具搜尋：
   ```
   Grep(pattern="<query>", path="$VAULT", glob="*.md", output_mode="content", -C=2, head_limit=50)
   ```
3. 排除 `.obsidian/`、`node_modules/` 等非筆記目錄
4. 以表格或列表格式回傳結果，包含：
   - 檔案路徑（相對於 Vault）
   - 匹配行與前後文
   - 修改時間

**進階搜尋**：

- `/obs search tag:#kubernetes` — 搜尋標籤
- `/obs search path:10-專案` — 限定目錄
- `/obs search "regex pattern"` — 正則搜尋

---

### `/obs read <path>` — 讀取筆記

**執行流程**：

1. 確定 Vault 路徑
2. 解析路徑：支援與 `/obs write` 相同的路徑簡寫
3. 若路徑精確（含 `.md` 後綴），直接 Read 檔案
4. 若路徑模糊（無 `.md` 後綴、僅關鍵字），用 Glob 模糊匹配：

   ```
   Glob("**/*<keyword>*.md", path="$VAULT/myWiki")
   ```

   - 若匹配到 1 個：直接讀取
   - 若匹配到多個：列出候選清單，請使用者選擇
   - 若匹配到 0 個：回報檔案不存在

5. 用 Read 工具讀取檔案完整內容
6. 呈現內容（含 frontmatter、標題、正文）

**路徑簡寫**：

- `inbox/xxx` → `$VAULT/myWiki/00-收件匣/xxx`
- `projects/xxx` → `$VAULT/myWiki/10-專案/xxx`
- `areas/xxx` → `$VAULT/myWiki/20-領域/xxx`
- `resources/xxx` → `$VAULT/myWiki/30-資源/xxx`
- `sop/xxx` → `$VAULT/myWiki/40-標準流程/xxx`

**範例**：

```
/obs read "resources/技術/Nginx 設定.md"
/obs read "areas/銀符之錘/創作靈感.md"
/obs read "銀符之錘"                        # 模糊匹配
```

---

### `/obs write <path> <content>` — 寫入筆記

**執行流程**：

1. 確定 Vault 路徑
2. 解析路徑：若為相對路徑，加上 `$VAULT/myWiki/` 前綴
3. 檢查檔案是否存在：
   - **存在**：`Read` 現有內容 → `Edit` 追加或修改指定段落
   - **不存在**：`Write` 建立新檔案
4. 確認寫入結果
5. 自動走 `/obs sync` 流程

**路徑簡寫**：

- `inbox/xxx` → `$VAULT/myWiki/00-收件匣/xxx`
- `projects/xxx` → `$VAULT/myWiki/10-專案/xxx`
- `areas/xxx` → `$VAULT/myWiki/20-領域/xxx`
- `resources/xxx` → `$VAULT/myWiki/30-資源/xxx`
- `sop/xxx` → `$VAULT/myWiki/40-標準流程/xxx`

**範例**：

```
/obs write "resources/技術/docker-tips.md" "## Volume 掛載\n- 用 named volume 比 bind mount 穩定"
/obs write "inbox/quick-note.md" "今天發現 Go 1.22 的 range over func 很好用"
```

---

### `/obs sync [action]` — Git 同步

**動作**：

- `sync`（預設）：`pull` + `add -A` + `commit` + `push`
- `status`：顯示 `git status`
- `push`：僅 push
- `pull`：僅 pull
- `log`：顯示最近 10 筆 commit

**執行流程**：

```bash
VAULT="${OBSIDIAN_VAULT:-$(grep -E '^export OBSIDIAN_VAULT=' ~/.zshrc | sed 's/^export OBSIDIAN_VAULT=//' | tr -d '\"' | tr -d \"'\")}"

# /obs sync（預設）
git -C "$VAULT" pull --rebase
git -C "$VAULT" add -A
git -C "$VAULT" commit -m "vault: auto sync $(date +%Y-%m-%d\ %H:%M)"
git -C "$VAULT" push

# /obs sync status
git -C "$VAULT" status --short

# /obs sync log
git -C "$VAULT" log --oneline -10
```

---

### `/obs sort [path]` — 分類整理筆記

將收件匣或指定目錄中的筆記，依 PARA 架構分類至對應目錄。

**預設路徑**：`$VAULT/myWiki/00-收件匣`

**PARA 分類規則**：

| 分類          | 目標目錄                   | 判定標準                               |
| ------------- | -------------------------- | -------------------------------------- |
| 專案          | `myWiki/10-專案/<name>/`   | 活躍專案、有明確目標和交付物           |
| 領域          | `myWiki/20-領域/<name>/`   | 持續維護的責任領域（遊戲設計、金工等） |
| 資源/技術     | `myWiki/30-資源/技術/`     | 技術教學、框架指南、環境設定           |
| 資源/程式片段 | `myWiki/30-資源/程式片段/` | 程式碼片段、切版範例                   |
| 資源/閱讀     | `myWiki/30-資源/閱讀/`     | 閱讀摘要、書評                         |
| 標準流程      | `myWiki/40-標準流程/`      | 標準操作流程                           |
| 歸檔          | `myWiki/90-歸檔/`          | 過時、空檔、不再相關的內容             |

**執行流程**：

1. **掃描**：

   ```
   VAULT="${OBSIDIAN_VAULT:-$(grep -E '^export OBSIDIAN_VAULT=' ~/.zshrc | sed 's/^export OBSIDIAN_VAULT=//' | tr -d '\"' | tr -d \"'\")}"
   TARGET_DIR = path 參數 || "$VAULT/myWiki/00-收件匣"
   Glob("**/*.md", path=TARGET_DIR)
   ```

   - 排除 `.obsidian/`、`.git/`、`templates/` 目錄
   - 跳過 `_` 開頭的系統檔（如 `_slug-mapping.md`）
   - 跳過已有 `category` frontmatter tag 的檔案

2. **粗分類**（根據檔名）：
   - 對每個檔案，根據檔名判定 PARA 分類
   - 標記信心度：高 / 中 / 低
   - CJK 檔名資訊量大，多數可直接判定
   - 如 `Golang Gin 框架的路由結構實作指南.md` → 資源/技術（高）

3. **細讀**（僅低信心檔案）：
   - 對信心度「低」的檔案（如 `untitled.md`、`分析.md`），Read 前 50 行
   - 根據內容重新判定分類和信心度

4. **呈報**（Markdown 表格）：

   ```markdown
   ## 分類計劃 — 共 N 個檔案

   | #   | 檔案    | 分類      | 目標路徑      | 信心度 | 理由         |
   | --- | ------- | --------- | ------------- | ------ | ------------ |
   | 1   | 需求.md | 資源/技術 | 30-資源/技術/ | 高     | 系統需求規格 |

   ### 待確認項目（信心度「低」）

   - untitled.md — 內容不明，建議人工檢視
   ```

   - 若超過 30 個檔案，分批呈報（每批 ≤30）
   - 請陛下御覽：「照辦」/ 逐項修改 / 「跳過低信心項目」

5. **執行**（確認後）：

   ```bash
   # 建立目標目錄
   mkdir -p "$VAULT/<目標路徑>"

   # 移動檔案（保留 git 歷史）
   git -C "$VAULT" mv "<原路徑>" "<目標路徑>"
   ```

   - 移動後用 Edit 工具在檔案頂部補上或更新 frontmatter：
     ```yaml
     ---
     category: 資源/技術
     sorted: 2024-01-15
     ---
     ```
   - 若檔案已有 frontmatter，在現有區塊內追加欄位
   - 若 `git mv` 失敗（檔案未被 git 追蹤或含特殊字元），改用 `mv` + `git add`
   - 疑似重複檔案標記提醒，不自動處理

6. **同步**：走 `/obs sync` 流程
   ```bash
   git -C "$VAULT" add -A
   git -C "$VAULT" commit -m "vault: sort — 移動 N 個檔案至 PARA 分類 $(date +%Y-%m-%d)"
   git -C "$VAULT" push
   ```

**範例**：

```
/obs sort                      # 整理收件匣（預設）
/obs sort "myWiki/20-領域"     # 重新分類特定目錄
```

---

## 規則

1. 所有路徑操作都基於解析後的 Vault 根目錄（`--vault` > `$OBSIDIAN_VAULT` > `~/.zshrc`），絕不硬編碼路徑
2. 建立筆記時自動建立所需的中間目錄
3. 搜尋結果排除 `.obsidian/`、`.skills/`、`.git/` 目錄
4. 回報時使用相對於 Vault 的路徑，方便閱讀
5. 使用現代繁體中文溝通，語氣簡潔直接
