# Obsidian AI 知識操作

只在處理 `compile`、`link` 或 `health` 時讀取本文件。Vault 與路徑解析沿用 `SKILL.md`；需要基本路徑簡寫或同步細節時，再讀取 [core.md](core.md)。

## 共通 frontmatter

編譯後筆記使用：

```yaml
---
title: "筆記標題"
compiled: true
compiled_at: 2026-09-09
source_type: internal
quality_score: 7.5
para_category: resource/技術
tags: [tag1, tag2]
connections: [相關筆記]
original_path: "00-收件匣/raw-note.md"
---
```

`source_type` 判定：第一人稱反思、daily、TIL 通常為 `internal`；URL、引用、書籍、會議紀錄通常為 `external`；混合內容保守標為 `external`，並保留個人觀點段落。

## `compile [path]`

把原始筆記整理為結構化知識筆記並歸檔。

1. 預設掃描 `00-收件匣/` 當層，排除 `daily/`、`til/`、`_` 開頭檔案與 `compiled: true`。每批最多 10 篇。
2. 若使用者明確指定單篇，可直接處理；批次處理先列出候選並確認範圍。
3. 完整讀取每篇原文，產出標題、2–3 句摘要、關鍵概念、重整正文、分類、品質分數、標籤與可能連結。不得加入原文沒有的事實。
4. Codex 確認 PARA 與 `source_type`，再決定目標：

| 分類 | 目標 |
|---|---|
| `project` | `10-專案/<推斷名稱>/` |
| `area` | `20-領域/` 下適當目錄 |
| `resource` | `30-資源/` 下適當目錄 |
| `sop` | `40-標準流程/` |
| `archive` | `90-歸檔/` |

5. 以結構化內容取代正文，原文完整保留在底部：

```markdown
<details>
<summary>原始筆記</summary>

原始全文

</details>
```

6. 優先使用 `git mv` 歸檔。若目標檔已存在，停止並呈報衝突，不覆寫。
7. 更新目標目錄既有的 `_index.md`；若不存在且該目錄已有超過 5 篇筆記，可建立 Topic Index。
8. 回報原路徑、標題、分類、品質與來源。只有使用者已要求同步時才執行 `sync`。

## `link [path]`

為指定筆記尋找有意義的 Obsidian wikilink。未指定路徑時，處理最近 7 天修改且已編譯的筆記，每批最多 5 篇；批次修改前先確認候選範圍。

對每篇筆記：

1. 提取 3–5 個核心概念。
2. 搜尋全庫 Markdown，排除系統目錄，收集標題與短摘要，最多 15 個候選。
3. 若 `.graph/graph-meta.json` 存在且未超過 7 天，加入同社群核心節點與跨社群橋樑候選；過期時只提出重建建議。
4. 分析並保留真正有意義的候選：
   - `🔗`：同主題或直接補充。
   - `🌀`：共享深層原則。
   - `🎲`：合理但意外的跨域關聯。
   - `🌉`：圖譜發現的跨社群橋樑。
5. 替換既有的 `## 知識連結` 區塊，或在文末追加：

```markdown
## 知識連結
> AI 語義分析 @ 2026-09-09

- 🔗 [[候選筆記]] — 一句具體的關聯理由
```

不得建立不存在的 wikilink，除非明確標為待建立概念。只有使用者已要求同步時才執行 `sync`。

## `health`

掃描全庫並產出 `00-收件匣/health-report-YYYY-MM-DD.md`。這個動作本身授權建立或更新當日報告，但不授權修改其他筆記。

收集：

- 各 PARA 目錄筆記數。
- 最近 30 天新增或修改數。
- inbox 未編譯筆記。
- 無 inlink 與 outlink 的孤立筆記。
- 排除 frontmatter 後少於 50 字的淺薄筆記。
- 不存在目標的死連結。
- `_index.md` 與實際目錄不一致或超過 30 天未更新的索引。

最多抽樣 20 篇已編譯筆記，檢查必要 frontmatter、可能矛盾、重複或可合併內容。若未讀取足夠原文，將判斷標為候選，不宣稱已確認矛盾。

若有效的 `graph-meta.json` 存在，加入密度、連通區、核心節點、孤島、橋樑、社群與重分類建議；不存在時只提示可執行 `$obs graph`。

報告至少包含總覽、需要關注的項目、證據路徑與建議動作。只有使用者已要求同步時才執行 `sync`。

## Topic Index

`_index.md` 可包含 `title`、`type: topic-index`、`last_updated`、目錄語境、已編譯概念與待補強主題。

- `compile` 歸檔時可更新對應索引。
- 新建索引前確認目錄主題足夠一致。
- `health` 只報告索引問題，不自動修正，除非使用者另行要求。
