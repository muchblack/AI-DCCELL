---
name: infinite-gratitude
description: 多 agent 平行研究：把主題拆成多個研究方向（GitHub、HuggingFace、論文、競品、最佳實踐等），平行派出 subagent 蒐集，彙整成報告，並依新發現的後續問題再派一輪。Triggers on: 無限貓報恩, infinite gratitude, 平行研究, 多 agent 研究, 幫我全面調查, 研究這個主題, multi-agent research. Examples: "/infinite-gratitude 寵物 AI 辨識", "/infinite-gratitude RAG best practices --depth deep", "/infinite-gratitude React state management --agents 3".
metadata:
  short-description: 多 agent 平行研究，可依後續問題多輪深入
---

# 無限貓報恩（Infinite Gratitude）

像貓咪一直叼禮物回家：派出多個 agent 平行研究同一個主題，帶回發現，再依新發現出門一輪。

## Usage

```
/infinite-gratitude <topic> [--depth quick|normal|deep] [--agents N]
```

| 參數 | 說明 | 預設 |
|------|------|------|
| `topic` | 研究主題（必填） | — |
| `--depth` | `quick`：只跑 1 輪、不追問；`normal`：最多 2 輪；`deep`：最多 4 輪 | `normal` |
| `--agents` | 每一輪平行的 agent 數量，1–10 | `5` |

沒給 `topic` 就先問使用者，不要自己猜。

## 成本提醒

每一輪會同時啟動 `--agents` 個 subagent。先告訴使用者本次設定（主題、輪數上限、每輪 agent 數），再開始派工。輪數上限是硬性上限，不因為「還有問題沒解決」而自動超過。

## Step 1: 拆研究方向

把 `{topic}` 拆成 N 個互不重疊的方向（N = `--agents`）。優先順序：

1. GitHub 專案
2. HuggingFace 模型 / 資料集
3. 論文與技術文章
4. 競品與現有產品
5. 最佳實踐與教學
6. 常見坑與失敗案例
7. Benchmark 與效能比較
8. 授權與成本
9. 社群討論（論壇、Reddit、Issue）
10. 實際案例研究

`--agents` 小於 5 時，取與主題最相關的前 N 個方向；主題明顯不適用某方向（例如純概念主題沒有 HuggingFace 模型）就換成清單中下一個。

## Step 2: 派出 agents

在**同一個 message** 中，用 Agent 工具一次發出 N 個 subagent，全部 `run_in_background: true`，`model: "haiku"`（省成本），`subagent_type` 用 `general-purpose`（需要網路搜尋能力）。每個 subagent 的 prompt：

```
Research the direction "{direction}" for the topic "{topic}".
{若是後續輪次：Focus on this follow-up question: "{question}". Already known: {前幾輪摘要，一兩句}}

Use web search. Find:
1. Top 3-5 recommendations (with URLs)
2. Pros and cons
3. Use cases
4. Key insights

Rules:
- Cite a source URL for every claim; do not invent projects, papers or numbers.
- If you cannot find reliable information, say so plainly.
- Output in Markdown, concise.
```

派出後回報一行狀態（例如「第 1 輪：5 隻貓出門了」）並結束這個 turn；agent 完成時會以通知回到 session。全部回來後再進入 Step 3，不要只靠部分結果就彙整。

## Step 3: 彙整

把所有 agent 的發現整理成：

```markdown
# {topic} 研究報告（第 {n} 輪）

## 總覽
- 時間：{timestamp}
- 本輪 agent 數：{count}

## 發現
### 1. {方向名稱}
{條列，每項附來源 URL}
（每個方向一節）

## 關鍵洞察
- 跨方向共通的結論、互相矛盾之處

## 後續問題
- 本輪發現衍生出、值得再查的問題
```

彙整時檢查：沒有來源的說法要標註「未驗證」；不同 agent 互相矛盾的地方明確列出，不要悄悄取其一。

## Step 4: 是否再跑一輪

- `--depth quick`，或已達輪數上限，或沒有後續問題 → 進入 Step 5。
- 否則列出後續問題，問使用者：「要針對這些問題再跑一輪嗎？（可指定要追哪幾題）」，一次一個決定。
  - 同意 → 用被選中的問題當各 agent 的方向，回到 Step 2（prompt 帶入「已知」摘要）。
  - 拒絕 → 進入 Step 5。

## Step 5: 最終報告

合併所有輪次的報告：去除重複、保留來源、最後給出「結論與建議」（3–5 點，可直接行動）。詢問使用者是否要存成檔案；要的話，路徑由使用者決定，不要自己選位置寫入。

## Notes

- 每輪的 agent 數量以 `--agents` 為準（最多 10）。
- 研究內容來自網路搜尋，可能過時或有誤；重要決策前請人工核對來源。
- 原始概念來自 [Washin Village](https://washinmura.jp)。
