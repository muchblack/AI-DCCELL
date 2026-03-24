# Obsidian 知識庫操作流程（Gemini CLI）

## 環境變數

- `$OBSIDIAN_VAULT`：Vault 根目錄路徑（預設 `~/code/obsidian`）
- 若未設定，使用 `~/code/obsidian` 作為 fallback

## 子命令

### `/obs new <type> [title]` — 建立新筆記

**支援模板類型**：`daily` / `meeting` / `project` / `sop` / `til`

**執行流程**：

1. 設定 Vault 路徑：
   ```bash
   VAULT="${OBSIDIAN_VAULT:-$HOME/code/obsidian}"
   ```
2. 讀取模板檔案：`cat "$VAULT/myWiki/templates/<type>.md"`
3. 用 `sed` 替換變數：
   ```bash
   DATE=$(date +%Y-%m-%d)
   DAY=$(date +%Y-%m-%d\ %a)
   sed -e "s/{{title}}/<title>/g" \
       -e "s/<% tp.date.now(\"YYYY-MM-DD\") %>/$DATE/g" \
       -e "s/<% tp.date.now(\"YYYY-MM-DD ddd\") %>/$DAY/g" \
       "$VAULT/myWiki/templates/<type>.md"
   ```
4. 決定輸出路徑：
   - `daily` → `$VAULT/myWiki/00-收件匣/daily/YYYY/YYYY-MM-DD.md`
   - `meeting` → `$VAULT/myWiki/00-收件匣/<title>.md`
   - `project` → `$VAULT/myWiki/10-專案/<title>/README.md`
   - `sop` → `$VAULT/myWiki/40-標準流程/<title>.md`
   - `til` → `$VAULT/myWiki/00-收件匣/til/YYYY-MM-DD-<title>.md`
5. `mkdir -p` 建立中間目錄，然後寫入檔案
6. 回報建立路徑
7. 自動走 `/obs sync` 流程

**範例**：
```
/obs new daily
/obs new meeting "週會"
/obs new project "API 重構"
```

---

### `/obs search <query>` — 搜尋筆記

**執行流程**：

```bash
VAULT="${OBSIDIAN_VAULT:-$HOME/code/obsidian}"
rg --type md -C 2 --ignore-file <(echo -e ".obsidian\n.skills\n.git") "<query>" "$VAULT" | head -50
```

**進階搜尋**：
- `/obs search tag:#kubernetes` — 搜尋標籤
- `/obs search path:10-專案` — 限定目錄：`rg ... "$VAULT/myWiki/10-專案"`

---

### `/obs read <path>` — 讀取筆記

**執行流程**：

1. 設定 Vault 路徑：
   ```bash
   VAULT="${OBSIDIAN_VAULT:-$HOME/code/obsidian}"
   ```
2. 解析路徑：支援與 `/obs write` 相同的路徑簡寫
3. 若路徑精確（含 `.md` 後綴），直接 `cat` 檔案
4. 若路徑模糊（無 `.md` 後綴、僅關鍵字），用 `find` 模糊匹配：
   ```bash
   find "$VAULT/myWiki" -name "*<keyword>*.md" -not -path "*/.obsidian/*" -not -path "*/.git/*"
   ```
   - 匹配 1 個：直接讀取
   - 匹配多個：列出候選清單，請使用者選擇
   - 匹配 0 個：回報檔案不存在
5. 呈現完整內容（含 frontmatter、標題、正文）

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

1. 解析路徑：
   ```bash
   VAULT="${OBSIDIAN_VAULT:-$HOME/code/obsidian}"
   # 簡寫展開
   # inbox/xxx → $VAULT/myWiki/00-收件匣/xxx
   # projects/xxx → $VAULT/myWiki/10-專案/xxx
   # areas/xxx → $VAULT/myWiki/20-領域/xxx
   # resources/xxx → $VAULT/myWiki/30-資源/xxx
   # sop/xxx → $VAULT/myWiki/40-標準流程/xxx
   ```
2. 檢查檔案是否存在
3. 存在 → 讀取後追加或修改；不存在 → 建立新檔
4. 確認寫入結果
5. 自動走 `/obs sync` 流程

---

### `/obs sync [action]` — Git 同步

```bash
VAULT="${OBSIDIAN_VAULT:-$HOME/code/obsidian}"

# /obs sync（預設：pull + add + commit + push）
git -C "$VAULT" pull --rebase
git -C "$VAULT" add -A
git -C "$VAULT" commit -m "vault: auto sync $(date +%Y-%m-%d\ %H:%M)"
git -C "$VAULT" push

# /obs sync status
git -C "$VAULT" status --short

# /obs sync pull
git -C "$VAULT" pull

# /obs sync log
git -C "$VAULT" log --oneline -10
```

---

### `/obs sort [path]` — 分類整理筆記

將收件匣或指定目錄中的筆記，依 PARA 架構分類至對應目錄。

**預設路徑**：`$VAULT/myWiki/00-收件匣`

**PARA 分類規則**：

| 分類 | 目標目錄 | 判定標準 |
|------|---------|---------|
| 專案 | `myWiki/10-專案/<name>/` | 活躍專案、有明確目標和交付物 |
| 領域 | `myWiki/20-領域/<name>/` | 持續維護的責任領域（遊戲設計、金工等） |
| 資源/技術 | `myWiki/30-資源/技術/` | 技術教學、框架指南、環境設定 |
| 資源/程式片段 | `myWiki/30-資源/程式片段/` | 程式碼片段、切版範例 |
| 資源/閱讀 | `myWiki/30-資源/閱讀/` | 閱讀摘要、書評 |
| 標準流程 | `myWiki/40-標準流程/` | 標準操作流程 |
| 歸檔 | `myWiki/90-歸檔/` | 過時、空檔、不再相關的內容 |

**執行流程**：

1. **掃描**：列出目標目錄下所有 `.md` 檔案，排除 `.obsidian/`、`.git/`、`templates/`、`_` 開頭的系統檔
2. **粗分類**：根據檔名判定 PARA 分類，標記信心度（高/中/低）
3. **細讀**：對信心度「低」的檔案讀取前 50 行，重新判定
4. **呈報**：以 Markdown 表格呈報分類計劃，請使用者確認
5. **執行**：確認後用 `git mv` 或 `mv` + `git add` 移動檔案，補上 frontmatter（`category`、`sorted` 日期）
6. **同步**：走 `/obs sync` 流程

**範例**：
```
/obs sort                      # 整理收件匣（預設）
/obs sort "myWiki/20-領域"     # 重新分類特定目錄
```

---

## 規則

1. 所有路徑操作都基於 `$OBSIDIAN_VAULT`，絕不硬編碼路徑
2. 建立筆記時自動 `mkdir -p` 建立中間目錄
3. 搜尋排除 `.obsidian/`、`.skills/`、`.git/`
4. 回報使用相對 Vault 路徑
5. 維持軍機處大臣溝通風格
