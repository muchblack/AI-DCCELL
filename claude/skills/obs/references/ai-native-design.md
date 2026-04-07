# AI-Native 知識庫整合設計文件

> 基於 Karpathy LLM Wiki + 周嘉恩 Personal Context Engineering + Vista Muse 系統
> 整合進現有 `/obs` skill 的 PARA 結構

## 設計原則

1. **AI 是圖書館員** — Obsidian 只是前端，AI 做分類、索引、上架、連結
2. **漸進式採用** — 新功能以子命令方式加入，不破壞現有 `/obs` 流程
3. **本地 MLX 優先** — 編譯、連結發現等重量級任務用 `mlx-chat.sh` 委派 Gemma 4，省 Claude token

---

## 新增子命令一覽

| 子命令 | 觸發 | 用途 |
|--------|------|------|
| `/obs compile [path]` | 手動 | 將 inbox 原始筆記 AI 編譯成結構化筆記 |
| `/obs link [path]` | 手動 | 對筆記做語義連結發現（3 層深度） |
| `/obs health` | 手動 / 排程 | 知識庫健康檢查，產出報告 |
| `/obs sort`（強化） | 現有 | 編譯時自動加 `source_type` frontmatter |

---

## 一、`/obs compile [path]`

### 目的

將 inbox 中的原始筆記（自由書寫、收藏文章、會議記錄等）經 AI 處理後，轉換為結構化筆記並歸檔到 PARA 對應目錄。

### 輸入

- `path`：預設 `$VAULT/myWiki/00-收件匣`，可指定其他目錄
- 支援路徑簡寫（`inbox/`、`resources/` 等）

### 執行流程

```
Step 1: 掃描目標目錄
  ├── Glob("*.md", path=TARGET_DIR)
  ├── 排除已編譯的筆記（frontmatter 含 `compiled: true`）
  ├── 排除 daily/ 和 til/ 子目錄（這些有自己的生命週期）
  └── 排除 `_` 開頭的系統檔

Step 2: 逐筆編譯（每次最多 10 篇，避免超時）
  ├── Read 原始筆記全文
  ├── 判斷 source_type（見下方啟發式規則）
  ├── 呼叫 MLX（mlx-chat.sh）進行編譯
  │   ├── system prompt: 編譯指令（見下方）
  │   └── user message: 原始筆記內容
  ├── 解析 MLX 回應
  └── 產出結構化筆記

Step 3: 寫入編譯結果
  ├── 以 MLX 輸出完全取代原始內容（AI 全權改寫）
  ├── 注入標準 frontmatter（見下方）
  └── 保留原始內容在底部折疊區塊（可選）

Step 4: 歸檔
  ├── 根據 AI 判定的 PARA 分類，移動到對應目錄
  ├── git mv 保留歷史
  └── 若目標目錄有 _index.md，更新索引條目

Step 5: 同步
  └── 走 /obs sync 流程
```

### 編譯 System Prompt（給 MLX）

```
You are a knowledge librarian. Compile the following raw note into a structured knowledge entry.

Output format (Markdown):
1. Title: Extract or generate a clear, descriptive title
2. Summary: 2-3 sentence overview
3. Key Concepts: Bullet list of main ideas
4. Body: Restructured content with clear sections and headers
5. Connections: Suggest 3-5 topics this note relates to (for later linking)
6. Classification:
   - PARA category: project / area / resource / sop / archive
   - source_type: internal (personal thought/opinion/epiphany) or external (article/book/reference)
   - quality_score: 1-10 (personal insights base +1.5 bonus)
   - suggested_tags: 3-5 tags

Respond in the same language as the input. Be concise, preserve the original meaning.
Do NOT add information that isn't in the original note.
```

### Frontmatter 結構

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
original_source: "00-收件匣/raw-note.md"  # 編譯前的路徑
---
```

### source_type 啟發式判斷規則

| 信號 | 判定 |
|------|------|
| 第一人稱語氣（「我覺得」「我認為」「今天發現」） | internal |
| 含 URL/引用/書名/作者名 | external |
| daily 或 til 目錄來源 | internal |
| 會議記錄 | external（除非含個人反思） |
| 混合型 | external（保守判定），在 body 中標註個人觀點段落 |

---

## 二、`/obs link [path]`

### 目的

對指定筆記（或全庫）進行語義連結發現，找出隱藏的知識關聯。

### 輸入

- `path`：指定筆記檔案，或目錄（批次處理）
- 無參數 = 處理最近 7 天修改的筆記

### 執行流程

```
Step 1: 讀取目標筆記內容

Step 2: 收集候選連結池
  ├── Grep 語義關鍵字（從目標筆記提取 3-5 個核心概念）
  ├── 搜尋範圍：全庫（排除 .obsidian/, .git/, templates/）
  └── 收集匹配筆記的標題 + 摘要（前 5 行）

Step 3: 呼叫 MLX 分析連結
  ├── 輸入：目標筆記 + 候選筆記清單
  ├── MLX 判斷每個候選的連結類型與強度
  └── 沿已有的 [[wikilink]] 走 2-3 層，尋找間接關聯

Step 4: 寫入連結區塊
  ├── 在筆記底部追加 `## 知識連結` 區塊
  ├── 使用標記：🔗 直接關聯 / 🌀 深層連結 / 🎲 意外發現
  └── 每個連結附一句理由
```

### 連結區塊格式

```markdown
## 知識連結
> AI 語義分析 @ 2026-04-06

- 🔗 [[Docker 容器化部署]] — 同屬 Infrastructure 主題，互為實踐補充
- 🌀 [[函數式程式設計]] — 不可變性概念與容器 immutable image 理念相通
- 🎲 [[料理的簡化原則]] — 減法思維：移除不必要的步驟/層，與 K8s 精簡部署同理
```

### 孤立筆記處理

若某篇筆記完全沒有 `[[wikilink]]` 且不在任何 index 中：
- 標記為孤立筆記
- `/obs health` 會將其列入報告
- `/obs link` 會優先嘗試為孤立筆記找連結

---

## 三、`/obs health`

### 目的

定期掃描全庫，產出健康報告，確保知識庫持續成長且自我修正。

### 執行流程

```
Step 1: 收集統計資料
  ├── 各 PARA 目錄的筆記數量
  ├── 最近 30 天新增/修改數量
  ├── 孤立筆記數量（無任何 inlink/outlink）
  ├── 空筆記或過短筆記（< 50 字）
  └── 未編譯筆記數量（inbox 中無 compiled: true）

Step 2: 品質掃描（抽樣，最多 20 篇）
  ├── 讀取筆記內容
  ├── 送 MLX 做品質評估：
  │   ├── 是否有矛盾資訊（與其他筆記衝突）
  │   ├── 是否過於淺薄（只有標題沒有實質內容）
  │   ├── frontmatter 完整性
  │   └── 連結健康度（死連結、缺連結）
  └── 收集評估結果

Step 3: 索引檢查
  ├── 掃描所有 _index.md 檔案
  ├── 檢查索引是否反映目錄實際內容
  └── 標記陳舊索引（最後更新 > 30 天）

Step 4: 產出報告
  └── 寫入 $VAULT/myWiki/00-收件匣/health-report-YYYY-MM-DD.md
```

### 報告格式

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

## 需要關注

### 孤立筆記（無任何連結）
- [[untitled-note.md]] — 建議執行 `/obs link`
- [[quick-idea.md]] — 內容過短，建議擴充或歸檔

### 可能矛盾
- [[Redis 快取策略]] vs [[資料庫查詢優化]] — 對 TTL 設定的建議互相矛盾

### 淺薄筆記（需擴充）
- [[GraphQL]] — 僅有標題和一行描述

### 陳舊索引
- `30-資源/技術/_index.md` — 最後更新 45 天前，目錄已新增 6 篇筆記

## 建議動作
1. 執行 `/obs compile` 處理 8 篇未編譯筆記
2. 執行 `/obs link` 為 5 篇孤立筆記建立連結
3. 考慮歸檔 3 篇空筆記
```

---

## 四、`/obs sort` 強化

### 變更點

在現有 sort 流程的 Step 5（執行移動）中，追加：

```yaml
# 追加到現有 frontmatter
source_type: internal | external  # AI 判定
sorted: 2026-04-06               # 已有
```

- 判定邏輯同 compile 的啟發式規則
- 若筆記已有 `source_type`（由 compile 產生），不覆蓋

---

## 五、Topic Index（_index.md）

### 結構

每個 PARA 子目錄可選擇性地維護一個 `_index.md`：

```markdown
---
title: "技術資源索引"
type: topic-index
last_updated: 2026-04-06
---

# 技術資源索引

## 語境描述
本目錄收錄軟體開發相關的技術筆記，涵蓋後端架構、DevOps、
資料庫、前端框架等主題。重點關注生產環境實踐而非理論。

## 已編譯概念
- [[Docker 容器化部署]]: 生產環境 Docker 設定與最佳實踐（quality: 8.0）
- [[Redis 快取策略]]: 快取失效策略與 TTL 設計（quality: 7.5）
- [[Nginx 反向代理]]: 負載均衡與 SSL 終止設定（quality: 6.0）

## 待補強主題
- Kubernetes 叢集管理（目前僅有淺薄筆記）
- 監控與告警（尚無相關筆記）
```

### 維護時機

- `/obs compile` 歸檔時自動更新對應目錄的 `_index.md`
- `/obs health` 檢查索引是否陳舊
- 手動執行 `/obs sort` 後更新

---

## 六、MLX 使用策略

**模型**：Gemma 4 26B-A4B（MoE 架構，4-bit 量化，~15GB）
**特性**：推理模型，回應分 `reasoning`（思考鏈→stderr）和 `content`（最終答案→stdout）
**限制**：prompt 超過 ~5000 tokens 可能 OOM，每批控制在 2000 字以內

| 操作 | 是否用 MLX | 理由 |
|------|-----------|------|
| compile（編譯） | 是（摘要+標籤） | 重量級改寫，省 Claude token。Claude 做最終決策 |
| link（連結發現） | 是（語義配對） | 需要語義理解，適合本地推理 |
| health（品質評估） | 是（矛盾偵測） | 批次分析，不需即時互動 |
| sort（分類） | 否（Claude 直接做） | 輕量判斷，現有邏輯已足夠 |

MLX 呼叫方式統一用 `~/.claude/skills/scripts/mlx-chat.sh`。

**降級策略**：MLX 不可用時（exit code 2/3），由 Claude 直接執行對應步驟，並在輸出標註 `> ⚠️ MLX 不可用，由 Claude 直接處理`。

---

## 七、實作優先序

| 批次 | 功能 | 依賴 | 預估工程量 |
|------|------|------|-----------|
| P0 | `/obs compile` | mlx-chat.sh（已有） | 更新 flow.md + 測試 |
| P1 | `/obs link` | compile 的 frontmatter 結構 | 更新 flow.md + 測試 |
| P2 | `/obs health` | compile + link 的資料 | 更新 flow.md + 測試 |
| P3 | Topic Index 自動維護 | compile 流程整合 | 低，compile 時順帶更新 |
| P4 | sort 強化（source_type） | compile 的啟發式規則 | 極低，加幾行判斷 |

---

## 八、知識圖譜整合（2026-04-07 新增）

> 靈感來源：[Graphify](https://github.com/safishamsi/graphify)
> 架構決策：自建 `obs-graph.py`（NetworkX + Louvain），不依賴 Graphify（因其內部使用 Claude API 做概念萃取，成本過高）

### 架構

- **`obs-graph.py`**（`~/.claude/skills/scripts/obs-graph.py`）：Python 腳本
  - 掃描 vault .md 檔案，解析 wikilinks `[[...]]` + frontmatter（tags, connections）
  - 建立 NetworkX DiGraph（nodes=筆記, edges=連結）
  - 計算 degree centrality, betweenness centrality, connected components
  - Louvain 社群偵測（python-louvain，需轉無向圖）
  - 匯出 GraphML + vis.js HTML + JSON meta
  - 依賴：`~/.mlx-env/bin/python`（networkx, python-louvain, jinja2）

- **`graph-template.html`**（`~/.claude/skills/scripts/templates/`）：vis.js 互動圖譜
  - 節點顏色 = PARA 分類，大小 = degree centrality，邊框色 = 社群
  - 搜尋框、社群/PARA 篩選器、節點 tooltip

- **`.graph/` 目錄**：vault 內的圖譜資料儲存
  - `knowledge-graph.graphml` — 圖結構
  - `knowledge-graph.html` — 互動視覺化
  - `graph-meta.json` — 指標摘要（供 link/health 讀取）
  - 加入 `.gitignore`（生成物不需版控）

### 與現有功能的整合

| 功能 | 整合方式 |
|------|---------|
| `/obs graph` | 新子命令，呼叫 obs-graph.py 生成圖譜 |
| `/obs link` | Step 1.5 檢查 graph-meta.json，用圖譜拓撲擴展候選池 |
| `/obs health` | Step 1.5 讀取 graph-meta.json，加入圖譜健康指標區塊 |
| `/obs graph --moc` | 用 MLX 對密集社群自動生成 `_index.md` |

### 關鍵指標（graph-meta.json）

- **God Nodes**：degree centrality 最高的核心筆記
- **Islands**：degree=0 的孤立筆記
- **Bridges**：betweenness centrality 最高的跨社群橋樑
- **Communities**：Louvain 偵測的知識叢集
- **Reclassification Suggestions**：高 centrality 但 PARA 分類可能不當的筆記

### graph-meta.json 過期策略

- `/obs link` 和 `/obs health` 檢查 `generated_at`
- < 7 天：有效，使用圖譜資料
- > 7 天：標註過期警告，建議重建
- 不存在：跳過圖譜相關功能，走純 Grep 流程

---

## 九、不做的事

- **不建 RAG** — 用 Topic Index + Knowledge Graph 取代，更簡單、省 token
- **不自動重寫已編譯筆記** — compile 是一次性的，後續編輯由人工
- **不改現有 sort 核心邏輯** — 只追加 frontmatter 欄位
- **不建獨立的 daily free writing 入口** — 現有 `/obs new daily` 已夠用
- **不依賴 Graphify** — 其 Claude API 概念萃取成本太高，自建 NetworkX 方案足夠
- **不做 /obs query** — 留待未來版本，目前圖譜資料已可透過 link/health 消化
