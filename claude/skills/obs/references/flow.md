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
8. 走「資料夾膨脹檢查」流程（見下方）

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
6. 走「資料夾膨脹檢查」流程（見下方）

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

   | # | 檔案 | 分類 | 目標路徑 | 信心度 | 理由 |
   |---|------|------|---------|--------|------|
   | 1 | 需求.md | 資源/技術 | 30-資源/技術/ | 高 | 系統需求規格 |

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
     source_type: internal | external
     ---
     ```
   - `source_type` 判斷規則：第一人稱語氣 → internal；含 URL/引用/書名 → external；混合型 → external
   - 若筆記已有 `source_type`（由 compile 產生），不覆蓋
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

### `/obs compile [path]` — AI 編譯筆記

將原始筆記經 AI 處理後，轉換為結構化筆記並歸檔到 PARA 對應目錄。

**預設路徑**：`$VAULT/myWiki/00-收件匣`（排除 `daily/`、`til/` 子目錄）

**執行流程**：

1. **掃描**：
   ```
   VAULT="${OBSIDIAN_VAULT:-$(grep -E '^export OBSIDIAN_VAULT=' ~/.zshrc | sed 's/^export OBSIDIAN_VAULT=//' | tr -d '\"' | tr -d \"'\")}"
   TARGET_DIR = path 參數 || "$VAULT/myWiki/00-收件匣"
   Glob("*.md", path=TARGET_DIR)
   ```
   - 排除已編譯筆記（frontmatter 含 `compiled: true`）
   - 排除 `daily/`、`til/` 子目錄
   - 排除 `_` 開頭的系統檔
   - 每次最多處理 10 篇，避免超時

2. **逐筆編譯**：
   對每篇未編譯筆記：
   - Read 全文
   - 判斷 `source_type`（見啟發式規則）
   - **Step 2a — MLX 摘要**：呼叫 MLX 生成摘要與標籤建議
     ```bash
     bash ~/.claude/skills/scripts/mlx-chat.sh \
       -s "<compile system prompt>" \
       -t 0.3 -m 4096 \
       "<筆記全文（控制在 2000 字以內，超過則截斷並附摘要）>"
     ```
     - MLX 不可用時（exit code 2/3），由 Claude 直接執行 Step 2a + 2b
   - **Step 2b — Claude 決策**：根據 MLX 輸出，Claude 負責：
     - 確認/修正 `para_category` 和 `source_type`
     - 注入標準 frontmatter
     - 決定歸檔目標目錄

   **Compile System Prompt**（給 MLX）：
   ```
   You are a knowledge librarian. Compile the following raw note into a structured knowledge entry.

   Output as plain Markdown (NO code fences):

   # [Title]

   ## Summary
   2-3 sentence overview.

   ## Key Concepts
   - concept 1
   - concept 2

   ## Body
   Restructured content with clear sections.

   ## Classification
   - para_category: project | area | resource | sop | archive
   - source_type: internal | external
   - quality_score: 1-10 (personal insights get +1.5 bonus)
   - suggested_tags: tag1, tag2, tag3

   ## Connections
   - Topic A — why it relates
   - Topic B — why it relates

   Respond in the same language as the input. Be concise, preserve the original meaning.
   Do NOT add information that isn't in the original note.
   ```

3. **寫入編譯結果**：
   - 注入標準 frontmatter：
     ```yaml
     ---
     title: "筆記標題"
     compiled: true
     compiled_at: 2026-04-06
     source_type: internal | external
     quality_score: 7.5
     para_category: resource/技術
     tags: [kubernetes, deployment, devops]
     connections: [Docker, CI-CD, Infrastructure]
     original_path: "00-收件匣/raw-note.md"
     ---
     ```
   - 以 MLX 輸出取代原始內容
   - 原始內容保留在底部折疊區塊：
     ```markdown
     <details>
     <summary>原始筆記</summary>

     {原始全文}

     </details>
     ```

4. **歸檔**：
   - 根據 AI 判定的 `para_category` 決定目標目錄：
     | para_category | 目標目錄 |
     |---------------|---------|
     | project | `myWiki/10-專案/<推斷名稱>/` |
     | area | `myWiki/20-領域/` |
     | resource | `myWiki/30-資源/` 下適當子目錄 |
     | sop | `myWiki/40-標準流程/` |
     | archive | `myWiki/90-歸檔/` |
   - `git mv` 保留歷史（失敗則 `mv` + `git add`）
   - 若目標目錄有 `_index.md`，追加新條目

5. **呈報**：
   ```markdown
   ## 編譯完成 — 共 N 篇

   | # | 原始檔案 | 標題 | 分類 | 品質 | 來源 |
   |---|---------|------|------|------|------|
   | 1 | raw.md | Docker 部署指南 | resource/技術 | 8.0 | external |
   ```

6. **同步**：走 `/obs sync` 流程
   ```bash
   git -C "$VAULT" add -A
   git -C "$VAULT" commit -m "vault: compile — 編譯 N 篇筆記 $(date +%Y-%m-%d)"
   git -C "$VAULT" push
   ```

**source_type 啟發式判斷規則**（供 Claude 在 MLX 無法判定時使用）：

| 信號 | 判定 |
|------|------|
| 第一人稱語氣（「我覺得」「我認為」「今天發現」） | internal |
| 含 URL / 引用 / 書名 / 作者名 | external |
| daily 或 til 目錄來源 | internal |
| 會議記錄 | external（除非含個人反思） |
| 混合型 | external（保守判定） |

**範例**：
```
/obs compile                          # 編譯收件匣所有未編譯筆記
/obs compile "inbox/my-raw-note.md"   # 編譯單篇
```

---

### `/obs graph [--open] [--moc]` — 知識圖譜生成

從全庫建立知識圖譜，計算社群結構、核心節點、孤立筆記等指標，並生成互動式 HTML 視覺化。

**執行流程**：

1. **Vault 解析**（同上方規則）

2. **生成圖譜**：
   ```bash
   ~/.mlx-env/bin/python ~/.claude/skills/scripts/obs-graph.py \
     --vault "$VAULT/myWiki" \
     --output "$VAULT/.graph"
   ```
   - 若加 `--open`，追加 `--open` 參數（自動開啟 HTML）
   - 腳本產出三個檔案至 `$VAULT/.graph/`：
     - `knowledge-graph.graphml` — 圖結構
     - `knowledge-graph.html` — vis.js 互動圖譜
     - `graph-meta.json` — 指標摘要

3. **確保 .gitignore**：
   - 檢查 `$VAULT/.gitignore` 是否包含 `.graph/`
   - 若無，追加 `.graph/` 至 `.gitignore`

4. **讀取並呈報摘要**（敘事式簡報風格）：
   - 讀取 `$VAULT/.graph/graph-meta.json`
   - 呈報格式：
     ```markdown
     ## 知識圖譜概覽

     陛下的知識庫共 N 個節點、M 條連結，密度 0.xxxx。
     偵測到 K 個知識社群、C 個獨立連通區。

     ### 核心節點（God Nodes）
     | 筆記 | 分類 | 連結數 | 社群 |
     |------|------|--------|------|
     | Docker 容器化部署 | resource | 23 | #2 |

     ### 孤立筆記（Islands）
     共 N 篇筆記無任何連結。建議執行 `/obs link` 建立關聯。
     （列出前 10 篇）

     ### 跨域橋樑（Bridges）
     這些筆記連接不同的知識社群：
     - DevOps 概述 — 橋接社群 #0 和 #3（betweenness 0.15）

     ### PARA 重分類建議
     以下筆記的中心度很高，但分類可能不當：
     - Docker（目前: resource → 建議: area，理由: 中心度 0.89）
     ```

5. **自動 MOC 生成**（僅 `--moc` 時）：
   - 從 `graph-meta.json` 讀取 `communities`
   - 對每個 `size > 5` 的社群：
     1. 檢查該社群主要筆記所在目錄是否已有 `_index.md`
     2. 若無 `_index.md`：
        - 用 MLX 生成 MOC 筆記：
          ```bash
          bash ~/.claude/skills/scripts/mlx-chat.sh \
            -s "You are a knowledge librarian. Generate a Map of Content (MOC) for these related notes. Output Markdown with: title, context description (2-3 sentences), and a bullet list of notes with one-line descriptions. Respond in the same language as the input." \
            -t 0.3 -m 2048 \
            "<社群內筆記標題列表>"
          ```
        - MLX 不可用時，由 Claude 直接生成
        - 寫入對應目錄的 `_index.md`（標準 Topic Index 格式）
   - 走 `/obs sync` 流程

**範例**：
```
/obs graph                    # 生成圖譜（不開啟）
/obs graph --open             # 生成並開啟 HTML
/obs graph --moc              # 生成 + 自動產出 MOC
/obs graph --open --moc       # 全部功能
```

---

### `/obs link [path]` — 知識連結發現

對指定筆記進行語義連結發現，找出隱藏的知識關聯。

**預設範圍**：最近 7 天修改的已編譯筆記

**執行流程**：

1. **選定目標筆記**：
   - 若指定檔案路徑：處理該筆記
   - 若指定目錄：處理該目錄下所有已編譯筆記
   - 若無參數：找最近 7 天修改的已編譯筆記（`compiled: true`）
   - 每次最多處理 5 篇

1.5. **圖譜輔助候選發現**（若有圖譜資料）：
   - 檢查 `$VAULT/.graph/graph-meta.json` 是否存在
   - 若存在，檢查 `generated_at` 是否 < 7 天
   - 若過期（> 7 天），顯示：`> ⚠️ 圖譜資料已過期（N 天前生成），建議執行 /obs graph 重建`
   - 若有效，讀取 JSON 並提取圖譜候選：
     - 從 `god_nodes` 中找與目標筆記同社群的節點
     - 從 `bridges` 中找與目標筆記跨社群的橋樑節點
     - 從 `communities` 中找目標筆記所屬社群的 `top_notes`
   - 圖譜候選標記來源：`[graph]`
   - 若圖譜不存在，跳過此步驟（走純 Grep 流程）

2. **收集候選連結池**：
   對每篇目標筆記：
   - 從筆記內容提取 3-5 個核心概念（關鍵字）
   - 用 Grep 搜尋全庫（排除 `.obsidian/`、`.git/`、`templates/`、`.graph/`）
   - 收集匹配筆記的標題 + 前 5 行摘要
   - Grep 候選標記來源：`[grep]`
   - 合併 Step 1.5 的圖譜候選與 Grep 候選，去重
   - 最多收集 15 個候選

3. **呼叫 MLX 分析連結**：
   ```bash
   bash ~/.claude/skills/scripts/mlx-chat.sh \
     -s "<link analysis system prompt>" \
     -t 0.3 -m 2048 \
     "Target note: <title + content summary>
      Candidates:
      1. <candidate title>: <summary>
      2. ..."
   ```
   - 候選池控制在 15 個以內（prompt 控制在 2000 字以內，避免 OOM）
   - MLX 不可用時（exit code 2/3），由 Claude 直接根據候選池判斷連結類型

   **Link Analysis System Prompt**：
   ```
   You are a knowledge connector. Analyze the relationship between the target note and each candidate.

   For each candidate, determine:
   - Connection type: 🔗 Direct (same topic/domain), 🌀 Deep (shared underlying principle), 🎲 Unexpected (surprising cross-domain insight), 🌉 Bridge (cross-community link discovered via knowledge graph)
   - One-sentence explanation of WHY they connect
   - Skip candidates with no meaningful connection
   - For candidates marked [graph], prefer 🌉 Bridge type if they come from a different community

   Output format (one per line, plain text):
   🔗 [[Candidate Title]] — Reason
   🌀 [[Candidate Title]] — Reason
   🎲 [[Candidate Title]] — Reason
   🌉 [[Candidate Title]] — Reason (cross-community bridge)
   ```

4. **寫入連結區塊**：
   - 若筆記已有 `## 知識連結` 區塊，替換之
   - 若無，在筆記底部追加：
     ```markdown
     ## 知識連結
     > AI 語義分析 @ 2026-04-06

     - 🔗 [[Docker 容器化部署]] — 同屬 Infrastructure 主題，互為實踐補充
     - 🌀 [[函數式程式設計]] — 不可變性概念與容器 immutable image 理念相通
     - 🎲 [[料理的簡化原則]] — 減法思維與精簡部署同理
     ```

5. **孤立筆記處理**：
   - 若筆記沒有任何 `[[wikilink]]` 且不在任何 `_index.md` 中
   - 加大候選池範圍（搜尋全庫而非關鍵字匹配）
   - 在連結區塊標註 `> 此為孤立筆記，已擴大搜尋範圍`

6. **同步**：走 `/obs sync` 流程

**範例**：
```
/obs link                                    # 處理最近 7 天修改的筆記
/obs link "resources/技術/Docker 部署.md"     # 單篇連結發現
/obs link "resources/技術"                    # 批次處理目錄
```

---

### `/obs health` — 知識庫健康檢查

定期掃描全庫，產出健康報告。

**執行流程**：

1. **收集統計資料**：
   ```
   VAULT 解析（同上方規則）
   ```
   統計項目：
   - 各 PARA 目錄的 `.md` 檔案數量（遞迴）
   - 最近 30 天新增 / 修改數量（`git log --since="30 days ago" --name-only`）
   - 孤立筆記數量（無任何 `[[` outlink 且不被任何筆記 `[[` inlink）
   - 空筆記或過短筆記（< 50 字，排除 frontmatter）
   - 未編譯筆記數量（inbox 中無 `compiled: true`）

1.5. **圖譜健康指標**（若有圖譜資料）：
   - 檢查 `$VAULT/.graph/graph-meta.json` 是否存在
   - 若不存在：跳過此步驟，在報告中標註 `> 提示：尚未生成知識圖譜，執行 /obs graph 可獲得更深入的分析`
   - 若存在但 > 7 天：標註 `> ⚠️ 圖譜資料已過期（N 天前生成），指標可能不準確`
   - 若有效，讀取 JSON 並加入以下指標：

   **圖譜結構**：
   - 圖譜密度（density）
   - 連通區數（connected_components）
   - 最大連通區大小（largest_component_size）

   **God Nodes（核心節點，前 5）**：
   | 筆記 | 分類 | 連結數 | 所屬社群 |
   |------|------|--------|---------|
   | （從 god_nodes 取前 5） |

   **Islands（孤立筆記）**：
   - 列出前 10 篇無連結筆記（含 PARA 分類）
   - 建議：執行 `/obs link` 為孤立筆記建立連結

   **Bridges（跨域橋樑，前 3）**：
   - 這些筆記連接不同的知識社群
   - 含 betweenness score 和所橋接的社群 ID

   **PARA 重分類建議**：
   - 列出 `reclassification_suggestions`（高中心度但分類可能不當的筆記）

   **叢集概覽**：
   - 列出前 8 大社群（含 size 和 top_notes）

2. **品質抽樣**（最多 20 篇）：
   - 從全庫隨機抽取已編譯筆記
   - 檢查 frontmatter 完整性（必要欄位：title, compiled, source_type）
   - 檢查死連結（`[[target]]` 但 target 檔案不存在）
   - 找矛盾或重複內容：用 MLX 對抽樣筆記做交叉比對
     ```bash
     bash ~/.claude/skills/scripts/mlx-chat.sh \
       -s "You are a knowledge auditor. Compare these notes and identify: 1) Contradictions 2) Duplicates 3) Notes that should be merged. Output plain text, be concise." \
       -t 0.3 -m 2048 \
       "<抽樣筆記摘要列表（控制在 2000 字以內）>"
     ```
   - MLX 不可用時，由 Claude 直接做交叉比對（跳過此步也可接受，統計資料本身已有價值）

3. **索引檢查**：
   - Glob 掃描所有 `_index.md`
   - 比對索引內容 vs 目錄實際檔案
   - 標記陳舊索引（最後更新 > 30 天且目錄有新增檔案）

4. **產出報告**：
   寫入 `$VAULT/myWiki/00-收件匣/health-report-YYYY-MM-DD.md`：

   ```markdown
   ---
   title: 知識庫健康報告
   type: health-report
   generated_at: 2026-04-06
   ---

   # 知識庫健康報告 — 2026-04-06

   ## 總覽
   | 指標 | 數值 |
   |------|------|
   | 總筆記數 | 156 |
   | 本月新增 | 12 |
   | 未編譯（inbox） | 8 |
   | 孤立筆記 | 5 |
   | 空/淺薄筆記 | 3 |
   | 死連結 | 2 |

   ## 需要關注

   ### 孤立筆記（無任何連結）
   - [[untitled-note.md]] — 建議執行 `/obs link`
   - [[quick-idea.md]] — 內容過短，建議擴充或歸檔

   ### 可能矛盾
   - [[Redis 快取策略]] vs [[資料庫查詢優化]] — 對 TTL 設定的建議不一致

   ### 淺薄筆記（< 50 字）
   - [[GraphQL]] — 僅有標題和一行描述

   ### 陳舊索引
   - `30-資源/技術/_index.md` — 最後更新 45 天前，目錄已新增 6 篇

   ### 死連結
   - [[已刪除的筆記]] ← 被 2 篇筆記引用

   ## 建議動作
   1. 執行 `/obs compile` 處理未編譯筆記
   2. 執行 `/obs link` 為孤立筆記建立連結
   3. 考慮歸檔空筆記至 `90-歸檔/`
   ```

5. **同步**：走 `/obs sync` 流程

**範例**：
```
/obs health                    # 全庫健康檢查
```

---

### Topic Index（`_index.md`）維護

每個 PARA 子目錄可維護一個 `_index.md`，由 `/obs compile` 歸檔時自動更新。

**結構**：
```markdown
---
title: "技術資源索引"
type: topic-index
last_updated: 2026-04-06
---

# 技術資源索引

## 語境描述
本目錄收錄軟體開發相關的技術筆記，涵蓋後端架構、DevOps、
資料庫、前端框架等主題。重點關注生產環境實踐。

## 已編譯概念
- [[Docker 容器化部署]]: 生產環境 Docker 設定與最佳實踐（quality: 8.0）
- [[Redis 快取策略]]: 快取失效策略與 TTL 設計（quality: 7.5）
```

**維護規則**：
- `/obs compile` 歸檔時：若目標目錄有 `_index.md`，追加新條目
- `/obs compile` 歸檔時：若目標目錄無 `_index.md` 且檔案數 > 5，自動建立
- `/obs health` 檢查時：標記內容與目錄不一致的索引
- `_index.md` 的「語境描述」由 AI 根據目錄內容生成，首次建立時撰寫

---

## 資料夾膨脹檢查

在 `/obs new` 和 `/obs write` 完成後自動執行。當目標資料夾中的 `.md` 檔案數量超過閾值時，觸發重新分類。

**閾值**：10 篇（僅計算當層 `.md` 檔案，不含子資料夾中的檔案）

**執行流程**：

1. **計數**：計算寫入檔案所在資料夾的 `.md` 檔案數量（不遞迴）
   ```
   Glob("*.md", path="<寫入檔案所在的資料夾>")
   ```

2. **判定**：
   - 檔案數 ≤ 10 → 不做任何事
   - 檔案數 > 10 → 進入步驟 3

3. **提示使用者**：
   ```
   ⚠️ 資料夾 <folder_name> 已有 N 篇文章（超過 10 篇閾值）。
   建議重新分類。

   A) 立即分類（執行 /obs sort "<folder_path>"）
   B) 稍後再說
   ```

4. **使用者選 A**：直接走 `/obs sort <folder_path>` 流程（見上方 sort 子命令）
5. **使用者選 B**：結束，不做任何事

**注意**：
- 此檢查僅針對寫入檔案的「直接所在資料夾」，不檢查父層或子層
- 若寫入的目標資料夾本身就是 sort 的結果（已有子資料夾結構），不重複觸發
- 判斷方式：若資料夾內已有子資料夾且子資料夾中也有 `.md` 檔案，視為「已分類」，跳過檢查

---

## MLX 使用注意事項

### 模型：Gemma 4 26B-A4B（MoE，4-bit 量化）

- **推理模型**：回應分為 `reasoning`（思考鏈）和 `content`（最終答案），需足夠 `max_tokens`（建議 ≥ 512）讓模型完成思考並產出 content
- **OOM 風險**：24GB M4 Pro 上，單次 prompt 超過 ~5000 tokens 可能觸發 Metal GPU OOM。每批 prompt 控制在 2000 字以內
- **呼叫方式**：統一用 `~/.claude/skills/scripts/mlx-chat.sh`

### MLX 不可用時的降級策略

若 `mlx-chat.sh` 回傳 exit code 2（server 不可達）或 3（請求失敗）：
- **compile**：由 Claude 直接執行編譯（省略 MLX 呼叫，Claude 自行生成摘要、分類、frontmatter）
- **link**：由 Claude 直接根據 Grep 候選池判斷連結類型（不呼叫 MLX）
- **health**：品質抽樣的矛盾/重複檢查改由 Claude 執行（統計部分不依賴 MLX）
- 降級時在輸出中標註 `> ⚠️ MLX 不可用，由 Claude 直接處理`

### MLX 使用策略

| 操作 | 是否用 MLX | 理由 |
|------|-----------|------|
| compile（編譯） | 是 | 重量級改寫，省 Claude token |
| link（連結發現） | 是 | 需要語義理解，適合本地推理 |
| health（品質評估） | 是 | 批次分析，不需即時互動 |
| sort（分類） | 否（Claude 直接做） | 輕量判斷，現有邏輯已足夠 |

---

## 規則

1. 所有路徑操作都基於解析後的 Vault 根目錄（`--vault` > `$OBSIDIAN_VAULT` > `~/.zshrc`），絕不硬編碼路徑
2. 建立筆記時自動建立所需的中間目錄
3. 搜尋結果排除 `.obsidian/`、`.skills/`、`.git/` 目錄
4. 回報時使用相對於 Vault 的路徑，方便閱讀
5. 使用現代繁體中文溝通，語氣簡潔直接
