# Obsidian 知識圖譜

只在處理 `graph [--open] [--moc]` 時讀取本文件。Vault 解析沿用 `SKILL.md`；需要同步細節時再讀取 [core.md](core.md)。

## 前置檢查

圖譜 helper 預期位於 `~/.claude/skills/scripts/obs-graph.py`，HTML 模板位於同層的 `templates/graph-template.html`。

依序選擇可用的 Python：

1. 能成功 import `networkx`、`community`、`jinja2` 的 `python3`。

腳本、模板或依賴缺失時，回報具體缺項，不自行安裝套件。可以提供不依賴圖形套件的基本連結統計作為替代，但不得宣稱已完成 Louvain 或 centrality 分析。

## 生成圖譜

以筆記根目錄為輸入、vault 下的 `.graph/` 為輸出：

```text
<python> <obs-graph.py> --vault <筆記根目錄> --output <vault>/.graph
```

預期產物：

- `knowledge-graph.graphml`
- `knowledge-graph.html`
- `graph-meta.json`

確認 vault `.gitignore` 含 `.graph/`；缺少時使用 `apply_patch` 追加，避免生成物進入版控。

讀取 `graph-meta.json` 後回報節點、邊、密度、連通區、主要社群、核心節點、孤立筆記、跨域橋樑與重分類候選。將重分類視為建議，不直接移動筆記。

## `--open`

只有使用者指定 `--open` 時才開啟 HTML。開啟 GUI 或瀏覽器前依目前環境的權限流程取得批准；無 GUI 環境則回報 HTML 路徑。

## `--moc`

只有使用者指定 `--moc` 時才建立 Map of Content。

1. 從 `graph-meta.json` 讀取社群。
2. 只處理 size 大於 5 且沒有合適 `_index.md` 的社群。
3. 根據社群內實際存在的筆記產生語境描述與連結清單；不得憑空建立筆記標題。
4. 寫入前呈報預計建立的 `_index.md` 路徑；若多個目錄都合理，先詢問使用者。

只有使用者已要求同步時才執行 `sync`。
