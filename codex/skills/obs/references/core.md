# Obsidian 基本操作

只在處理 `new`、`search`、`read`、`write`、`sync` 或 `sort` 時讀取本文件。

## Vault 與路徑解析

依序解析 vault：

1. 使用者提示中的 `--vault <path>`。
2. `OBSIDIAN_VAULT` 環境變數。
3. `~/.zshrc` 中明確宣告的 `OBSIDIAN_VAULT`。

展開 `~` 後取得絕對路徑，確認目錄存在。若 `<vault>/myWiki` 存在，以它作為筆記根目錄；否則直接以 vault 根目錄為筆記根目錄。

路徑簡寫：

| 簡寫 | `myWiki` 結構中的位置 |
|---|---|
| `inbox/` | `00-收件匣/` |
| `projects/` | `10-專案/` |
| `areas/` | `20-領域/` |
| `resources/` | `30-資源/` |
| `sop/` | `40-標準流程/` |

若 vault 沒有 `myWiki` 結構，不套用簡寫，直接從 vault 根目錄解析相對路徑。寫入或移動前確認解析後的路徑仍位於 vault 內。

## `new <type> [title]`

支援 `daily`、`meeting`、`project`、`sop`、`til`。

1. 讀取 `<vault>/templates/<type>.md`。模板不存在時回報缺少的路徑，不自行發明模板。
2. 替換 `{{title}}`、`<% tp.date.now("YYYY-MM-DD") %>` 與 `<% tp.date.now("YYYY-MM-DD ddd") %>`。
3. 建立必要的中間目錄並寫入：

| 類型 | 目標路徑 |
|---|---|
| `daily` | `00-收件匣/daily/YYYY/YYYY-MM-DD.md` |
| `meeting` | `00-收件匣/<title>.md` |
| `project` | `10-專案/<title>/README.md` |
| `sop` | `40-標準流程/<title>.md` |
| `til` | `00-收件匣/til/YYYY-MM-DD-<title>.md` |

若必要標題缺失，先用繁體中文詢問。檔案已存在時不得直接覆寫；先呈報衝突並詢問要追加、改名或取消。

完成後執行「資料夾膨脹檢查」。只有使用者已要求同步時才接續 `sync`。

## `search <query>`

優先使用 `rg` 搜尋 Markdown，排除 `.obsidian/`、`.git/`、`.graph/`、`.skills/`、`node_modules/` 與 `templates/`。

- 一般文字或 regex：搜尋 `*.md` 內容並提供最多 50 組結果及少量上下文。
- `tag:<tag>`：搜尋 frontmatter tags 與正文 hashtag。
- `path:<path>`：把搜尋範圍限制在解析後的 vault 子目錄。

回報相對路徑、匹配行、上下文與修改時間。使用者輸入應當作搜尋參數傳遞，不可拼接成未引用的 shell 程式碼。

## `read <path>`

1. 套用路徑簡寫。
2. 精確路徑存在時讀取完整 Markdown，包括 frontmatter。
3. 模糊名稱使用 `rg --files` 找 `*<keyword>*.md`：唯一匹配直接讀取，多筆則列出候選，零筆則回報不存在。

## `write <path> <content>`

套用路徑簡寫並確認目標位於 vault 內。

- 新檔：建立必要目錄後寫入。
- 既有檔：先讀取，再依請求追加或修改指定段落；若意圖不清且不同解讀會覆蓋內容，先詢問。
- 不得用會截斷既有檔案的 shell redirection。

完成後驗證結果並執行「資料夾膨脹檢查」。只有使用者已要求同步時才接續 `sync`。

## `sync [action]`

若 vault 等於或位於 `/mnt/d/company/company`，回報「此 vault 不用 Git 管理，略過同步」，不執行任何 Git 指令。

支援：

- `status`：`git status --short`
- `log`：`git log --oneline -10`
- `pull`：`git pull --rebase`
- `push`：只推送既有 commit
- `sync`：pull、檢視變更、stage、commit、push

`status`、`log` 是唯讀操作，可直接執行。`pull`、commit 與 `push` 會改變本地或遠端狀態；依 `SKILL.md` 的授權規則處理。

完整同步時：

1. 確認目標是 Git repository，並檢查 status、branch、remote。
2. `git pull --rebase`；發生衝突立即停止，不自動丟棄任何變更。
3. 檢視 vault 中待提交的所有變更，避免夾帶非預期檔案。
4. `git add -A`，使用繁體中文 commit message，例如 `vault：同步筆記 2026-09-09 14:30`。沒有變更時略過 commit。
5. 推送目前 branch，回報 commit 與 remote。

## `sort [path]`

預設掃描 `00-收件匣/`，或使用者指定的 vault 子目錄。排除系統目錄、`_` 開頭檔案，以及已有 `category` frontmatter 的筆記。

PARA 判定：

| 分類 | 目標 |
|---|---|
| 專案 | `10-專案/<name>/` |
| 領域 | `20-領域/<name>/` |
| 資源／技術 | `30-資源/技術/` |
| 資源／程式片段 | `30-資源/程式片段/` |
| 資源／閱讀 | `30-資源/閱讀/` |
| 標準流程 | `40-標準流程/` |
| 歸檔 | `90-歸檔/` |

先根據檔名分類；只細讀低信心筆記。呈報來源、目標、信心度與理由，最多每批 30 筆。移動檔案前取得使用者確認；可讓使用者逐項修改或跳過低信心項目。

執行時優先使用 `git mv` 保留歷史，未追蹤檔案則使用一般移動並 stage。更新 frontmatter：

```yaml
category: 資源/技術
sorted: 2026-09-09
source_type: internal | external
```

保留既有欄位；已有 `source_type` 時不覆蓋。疑似重複檔案只標記，不自動合併或刪除。

## 資料夾膨脹檢查

`new` 或 `write` 後，計算目標資料夾當層的 `.md` 檔案數，不遞迴。超過 10 篇且尚無明顯子分類時，提示：

```text
這個資料夾已有 N 篇筆記，建議重新分類。要現在整理嗎？
```

只有使用者同意才執行 `sort`。
