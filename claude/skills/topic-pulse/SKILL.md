---
name: topic-pulse
description: >-
  跨區域輿情分析：查證一個話題後，收集新聞媒體、中文（台港／中國）、英、日、韓社群的意見反應並摘要，
  附完整來源、原文引述、平台覆蓋狀況、擴散路徑、謠言與詐騙。搜尋派給 herdr 的 agy pane，
  網址與數字由主對話與腳本查證後才寫報告。
  Triggers on: 輿情, 輿論, 社群反應, 各地反應, 話題風向, 網路風向, 韓文社群反應, 日本玩家怎麼看, topic pulse, sentiment report.
  Examples: "/topic-pulse 蔚藍檔案日版移管 NEXON", "/topic-pulse 影之刃零 --regions=zh,en --quick",
  "/topic-pulse 空之軌跡 the 2nd 鐵盒延誤 --html", "/topic-pulse --update blue-archive-nexon".
metadata:
  short-description: 查證話題並整理媒體與中英日韓社群的反應
---

# topic-pulse

## 用法

```
/topic-pulse <話題> [--regions=zh,en,ja,ko] [--quick] [--html] [--since=YYYY-MM-DD]
/topic-pulse --update <slug>
```

| 參數 | 意思 |
|---|---|
| `--regions` | 要查的地區，預設 `zh,en,ja,ko`；`zh` 含台港與中國 |
| `--quick` | 只查媒體 + 每區 1–2 個主平台 |
| `--html` | 另產 `report.html` |
| `--since` | 只收此日之後的討論；預設＝事件日 |
| `--update <slug>` | 追蹤既有話題，見文末 |

## 產出

`RUN = <cwd>/pulse/<slug>-<YYYYMMDD>/`（slug：英文小寫、連字號，例 `blue-archive-nexon`）

```
brief-a.md / brief-b.md   派給 agy 的任務書（英文）
verify.json + verify.done 階段 A
raw/<region>.json + raw.done   階段 B（地區 key：zh-tw, zh-cn, en, ja, ko, media）
check.md                  階段 C 查證紀錄
report.md / report.html   最終報告
```

S = `~/.claude/skills/topic-pulse/scripts/pulse.py`
W = `~/.claude/skills/herdr-dev/scripts/wait-result.sh`

## 平台表

依題材挑平台寫進 brief。平台名要用下表寫法（`pulse.py` 依此比對網域；新平台可加，但要同步加進 `PLATFORM_DOMAINS`）。

| 區域 | 遊戲／動漫 | 科技 | 時事／娛樂 |
|---|---|---|---|
| zh-tw（台港） | 巴哈姆特、PTT、YouTube、Plurk、Threads、Facebook | PTT、Mobile01、Dcard | PTT、Dcard、Threads、LIHKG |
| zh-cn | NGA、百度貼吧、Bilibili、微博 | 知乎、V2EX | 微博、小紅書、知乎 |
| en | Reddit、ResetEra、X、YouTube、Steam | Reddit、Hacker News | Reddit、X |
| ja | 5ch、X、YouTube、はてなブックマーク、Yahoo!リアルタイム検索 | はてなブックマーク | Yahoo!ニュース、X |
| ko | Ruliweb、DC Inside、Inven、YouTube | Clien | Naver、theqoo |
| media | 評分站（OpenCritic、Metacritic）＋各區主流媒體 | 同左 | 同左 |

已知封閉平台（多半 `partial`／`blocked`）：微博、小紅書、Plurk、Facebook、Threads、X。改走替代路線：搜尋引擎索引、媒體報導、轉貼到開放平台的內容（例：Plurk 熱門內容常轉自 PTT）。

YouTube 跨區：官方直播／PV 留言區常是第一手反應，留言**依語言歸區**，不依平台（日文留言 → `ja`）。中國區用 Bilibili 代替（YouTube 被牆）。

## 流程

### 0. 準備（主對話）
1. 解析參數、決定 slug 與題材類別、建 `RUN/raw/`。
2. `herdr agent list` 找 `agent_status: idle` 的 agy pane，優先 cwd 相同者；路徑一律給絕對路徑。
   **沒有 idle agy** → 改由主對話用 WebSearch／WebFetch 照同一 brief 執行，產出同樣的檔案。
3. 每次派工給新 ID：`<slug>-a`、`<slug>-b`、`<slug>-fix1`。

派工方式（與 store-lookup 相同）：
- `herdr agent prompt <pane> "Read <RUN>/brief-x.md and execute it."`（**不加 `--wait`**）
- 背景等待：`bash W <pane> <RUN>/<x>.done <ID>`（`run_in_background`）。
- `RESULT_READY` 才往下；`SETTLED_NO_RESULT`／`BLOCKED`／`TIMEOUT` → `herdr agent read <pane>` 看畫面再決定。

### A. 事件查證 + 關鍵字表（agy）
寫 `brief-a.md`（範本 A），等 `verify.done`。

檢查點（主對話讀 `verify.json`）：
- `status: not_found` → 停，向皇上回報查無此事與已查來源，不跑 B。
- `confirmed`／`partial` → 不打擾皇上，直接進 B。`partial` 要在報告第 2 節寫明哪部分未證實。

### B. 逐平台收集（agy，各區依序）
寫 `brief-b.md`（範本 B：填入地區、平台、關鍵字、since），等 `raw.done`。

### C. 查證（主對話）
1. `python3 S check RUN --spot 5` → FAIL／WARN／SPOTCHECK 清單。
2. 對每條 SPOTCHECK 用 WebFetch 開網址，確認引述（或其意思）確實在頁面上。打不開（登入牆）記「無法驗證」，不算造假。
3. 自己核算 `verify.json` 時間軸與各條目的日期、期間、數字（例：「一年以上緩衝期」要真的算一次）。
4. 有 FAIL、抽查對不上、算錯 → 列清單寫 `brief-fix1.md` 退回同一 agy pane，**只退一次**；修完重跑第 1 步。仍不合格的條目在報告標「⚠️ 未證實」並列入附錄，不刪除。
5. 結果寫 `check.md`：check 輸出摘要、抽查結果（每條：網址／是否相符）、算錯更正。

### D. 寫報告（主對話）
照下方報告格式寫 `report.md`，白話繁體中文，不用 agy 的「阿斯拉／遙測／駕駛員」語彙。
報告會分享給其他人：不寫「皇上／臣」等稱謂，也不寫只針對皇上個人的建議（要給就在對話裡說）。
- 每個論點附來源連結；社群論點附原文引述＋譯文。
- 只寫「普遍／分歧／少數」，不寫百分比；數量只寫 `count` 有值者，估計值加「約」。
- `--html` → `python3 S html RUN/report.md`。

### E. 回報皇上
只回：一句話總結、報告路徑、抓不到的平台、未證實條目數。全文不貼進對話。

## 報告格式

```
# <話題> 輿論摘要（截至 YYYY-MM-DD）
1. 一句話總結
2. 事件查證（第一手來源、屬實程度）
3. 時間軸
4. 媒體觀點（評分、主要論點）
5. 各地區社群反應（每區 2–3 個重點，附原文引述）
6. 族群分析（老玩家／新玩家／海外玩家／二創圈…依話題而定）
7. 跨區域對比表；媒體與社群的落差
8. 擴散路徑
9. 謠言、澄清與詐騙
10. 平台覆蓋狀況（full / partial / blocked + 原因）
11. 待觀察事項（附預定日期）
附錄：取樣與來源清單（完整網址）、搜尋指令清單、未證實條目
```

## 範本 A（英文；填入 TOPIC / RUN / ID / REGIONS / CATEGORY）

```
Dispatch ID: ID
Task: verify that this event is real and build search keywords. Topic: TOPIC

1. Find PRIMARY sources (official announcement, livestream, press release, official account post).
   Record full URL, publish date, title. Secondary media only if no primary source exists (say so).
2. Decide status: confirmed | partial (state which part is unverified) | not_found.
3. Build a dated timeline of the event (YYYY-MM-DD, what happened, source URL).
4. Build keywords per region in REGIONS: official localized titles, common nicknames/abbreviations,
   platform slang. Search to confirm each localized title is really used (e.g. Korean title for a game).

Write RUN/verify.json (UTF-8):
{"status": "...", "status_note": "...", "event_date": "YYYY-MM-DD",
 "sources": [{"url": "...", "date": "...", "title": "...", "primary": true}],
 "timeline": [{"date": "...", "event": "...", "url": "..."}],
 "keywords": {"zh-tw": ["..."], "zh-cn": ["..."], "en": ["..."], "ja": ["..."], "ko": ["..."]}}
Rules: full URLs only, never shorten with "..."; never invent a source you did not open.
LAST step, only after verify.json is complete: write RUN/verify.done whose first line is exactly
"dispatch_id: ID". Then reply with one line: status + number of sources.
```

## 範本 B（英文；填入 TOPIC / RUN / ID / SINCE / 每區平台與關鍵字）

```
Dispatch ID: ID
Task: collect public reactions to TOPIC since SINCE. Event facts are in RUN/verify.json.
Process regions one at a time, in this order: <media, zh-tw, zh-cn, en, ja, ko>.
Per region: <region> → platforms: <...>; keywords: <...>

Search in the region's own language using its keywords; use site: queries per platform.
For a platform behind a login wall / anti-bot, do not try to bypass it: mark coverage, and look for
its content via search-engine index, media reports, or reposts on open platforms.

For each region write RUN/raw/<region>.json (UTF-8):
{"region": "...",
 "platforms": [{"platform": "<exact name>", "coverage": "full|partial|blocked", "reason": "..."}],
 "items": [{"kind": "community|media", "platform": "<exact name or outlet name>",
            "url": "<full URL>", "date": "YYYY-MM-DD", "title": "...",
            "count": <integer shown on the page, e.g. replies/pushes/floors, or null>,
            "count_estimated": false, "count_note": "...",
            "claim": "<the point, in Traditional Chinese>",
            "quote_orig": "<verbatim quote in original language>", "quote_zh": "<translation>",
            "stance": "正面|負面|分歧|中立", "group": "<audience group, e.g. 海外玩家, 老玩家, 二創圈>"}],
 "diffusion": ["<where it started -> where it spread, with URLs>"],
 "rumors": [{"rumor": "...", "clarification": "...", "url": "..."}],
 "scams": [{"description": "...", "url": "..."}],
 "queries": ["<every search query you ran for this region>"]}

Hard rules (machine-checked, then spot-checked by opening URLs):
- Full URLs only; never "..." or "…". The URL domain must belong to the named platform
  (a PTT thread is platform "PTT" even if you found it via Plurk; put that in diffusion).
- Quotes must be copied verbatim from a page you actually opened. No quote -> no community item.
- count: only numbers visible on the page. Estimates: count_estimated=true and explain in count_note.
- No percentages, no "most players" without quotes backing it.
- Media items: reviews/scores go in claim (e.g. "Eurogamer 3/5: Boss 血量過厚").
Aim for 3-8 items per platform with coverage full/partial; quality over volume.
LAST step, only after every region file is written: write RUN/raw.done whose first line is exactly
"dispatch_id: ID". Then reply with one line per region: item count + blocked platforms.
```

修正回合 `brief-fix1.md`：列出 check.md 的問題條目（檔名#索引、問題），要求只改這些條目、其餘不動，完成後寫 `RUN/raw.done`（`dispatch_id: <slug>-fix1`）。

## --update 追蹤模式

1. 找 `pulse/<slug>-*/` 最新一份為 PREV。
2. 新建 RUN；跳過 A（沿用 PREV 的 `verify.json`，但 brief-b 要求先查有無新官方公告並更新 timeline）。
3. brief-b 帶入 PREV `raw/*.json` 的 `queries`，`SINCE` = PREV 的報告日期。
4. 報告第 1 節之後插入「與上次（YYYY-MM-DD）相比的變化」：新事件、風向轉變、新謠言、已澄清事項。

## 鐵則

- 沒有來源的論點不寫進報告；查證由 `pulse.py` 與主對話負責，不採信 agy 自稱完成查證。
- 不登入、不繞過登入牆或反爬機制。
- 不算情緒百分比；不自動排程（要定期追蹤用 `/loop` 包 `--update`）。
- 第一版不拆多 pane 平行跑。
