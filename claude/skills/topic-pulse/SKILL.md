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

搜尋熱度需設定環境變數 `SERPAPI_API_KEY`，每份報告約用 9 次 SerpApi 額度（四區各 2 次＋全球 1 次），沒有省額度開關。未設定或查詢失敗仍繼續產出報告。
腳本用法：`python3 S trends RUN [--provider serpapi|google]`，預設 `serpapi`；`google` 目前只會寫出尚未實作的狀態。

## 產出

`RUN = <cwd>/pulse/<slug>-<YYYYMMDD>/`（slug：英文小寫、連字號，例 `blue-archive-nexon`）

```
brief-a.md / brief-b.md   派給 agy 的任務書（英文）
verify.json + verify.done 階段 A
trends.json              階段 A.5 搜尋熱度（含來源、比例尺、狀態與原因）
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
- `confirmed`／`partial` → 不打擾皇上，直接進 A.5。`partial` 要在報告第 2 節寫明哪部分未證實。

### A.5 搜尋熱度（主對話）
1. 執行 `python3 S trends RUN`，數字由腳本直接抓取，不交給 agy 抄錄。
2. 讀 `trends.json` 各區的 `rising`，挑出和話題相關的詞補進 brief-b 關鍵字表，不全部照抄。`rising` 是 `null`（來源不支援）就跳過；先檢查各區 `status`，失敗請求的 `[]` 不代表沒有搜尋結果。
3. `status: unavailable` 不用停下來，直接進 B；報告註明本次無資料。`partial` 則保留成功資料並說明缺漏。

`trends.json` 寫出就 exit 0（包含 `unavailable`）；只有無法寫檔才回非 0。期間為事件日前 30 天至今天，事件日缺漏或無法解析時用最近 3 個月。

### B. 逐平台收集（agy，各區依序）
寫 `brief-b.md`（範本 B：填入地區、平台、關鍵字、since），等 `raw.done`。

### C. 查證（主對話）
1. `python3 S check RUN --spot 5` → FAIL／WARN／SPOTCHECK 清單。
2. 對每條 SPOTCHECK 用 WebFetch 開網址，確認引述（或其意思）確實在頁面上。打不開（登入牆）記「無法驗證」，不算造假。
   WebFetch 轉文字時會拿掉 `<script>`，看不到內容或數字時，不要直接當成「需要 JS 才看得到」：先 `curl -sL -A "Mozilla/5.0" <url>` 抓原始 HTML，讀頁面內嵌的 JSON。YouTube 讀 `ytInitialPlayerResponse` 的 `videoDetails.shortDescription`（說明欄）和 `viewCount`（觀看數）；Plurk 讀 `plurk = {...}` 的 `favorite_count`、`replurkers_count`、`response_count`。兩條路都查不到，才記「無法驗證」。
3. 自己核算 `verify.json` 時間軸與各條目的日期、期間、數字（例：「一年以上緩衝期」要真的算一次）。
4. 有 FAIL、抽查對不上、算錯 → 列清單寫 `brief-fix1.md` 退回同一 agy pane，**只退一次**；修完重跑第 1 步。仍不合格的條目在報告標「⚠️ 未證實」並列入附錄，不刪除。
5. 結果寫 `check.md`：check 輸出摘要、抽查結果（每條：網址／是否相符）、算錯更正。

### D. 寫報告（主對話）
照下方報告格式寫 `report.md`，白話繁體中文，不用 agy 的「阿斯拉／遙測／駕駛員」語彙。
報告會分享給其他人：不寫「皇上／臣」等稱謂，也不寫只針對皇上個人的建議（要給就在對話裡說）。
- 每個論點附來源連結；社群論點附原文引述＋譯文。
- `--html` 依固定寫法把各節轉成版面元件，照下列寫法才會套用（不符就原樣輸出，不會出錯）：
  - 事件查證：清單項目寫成「標籤：內容」（標籤 2–10 字）→ 欄位表；未證實寫成 `⚠️ 未證實：` 加清單 → 黃色提示框；行內 `⚠️ 未證實`／`⚠️ 無法驗證` → 標籤。
  - 時間軸：`| 日期 | 事件 | 來源 |` 表格 → 時間軸列表。
  - 媒體／社群引文：一條一句，寫成 `- 來源（平台）：「原文」[連結](url)` → 引用卡片。
  - 族群分析：`- **族群**：說明` → 卡片。擴散路徑：一段 `A（日期）→ B（日期）→ …。補充` → 流程圖。
  - 待觀察事項：`- YYYY-MM-DD：事項` → 日期列表。附錄：`### 來源清單` → 可收合區塊。
- 只寫「普遍／分歧／少數」，不寫百分比；數量只寫 `count` 有值者，估計值加「約」。
- `--html` → `python3 S html RUN/report.md --hue N`。N 是配色色相（0–359），依話題主視覺挑一個：櫻花粉 335、抹茶綠 140、海藍 210、橘 25、紫 275；挑不出就省略（預設 210）。標題下方自動加總結卡片（查證狀態、取樣數、平台覆蓋、未證實數），第 4 節自動插入各區熱度長條圖（虛線＝verify.json 時間軸事件），數字都從 RUN 內檔案讀取。

### E. 回報皇上
只回：一句話總結、報告路徑、抓不到的平台、未證實條目數。全文不貼進對話。

## 報告格式

```
# <話題> 輿論摘要（截至 YYYY-MM-DD）
1. 一句話總結
2. 事件查證（第一手來源、屬實程度）
3. 時間軸
4. 搜尋熱度
5. 媒體觀點（評分、主要論點）
6. 各地區社群反應（每區 2–3 個重點，附原文引述）
7. 族群分析（老玩家／新玩家／海外玩家／二創圈…依話題而定）
8. 跨區域對比表；媒體與社群的落差
9. 擴散路徑
10. 謠言、澄清與詐騙
11. 平台覆蓋狀況（full / partial / blocked + 原因）
12. 待觀察事項（附預定日期）
附錄：取樣與來源清單（完整網址）、搜尋指令清單、`### 未證實條目（N）`（N 為條數；`--html` 據此產生總結卡片，沒有未證實條目就寫 0）
```

第 4 節依 `trends.json` 撰寫：
- 各區用 `peak` 寫高峰日期，對照第 3 節時間軸事件；用 `timeline` 說明走勢，不把高峰值當成目前熱度。`peak: null` 就說明沒有可用高峰。
- 列出 `worldwide.top_countries` 全球熱度排名前幾名國家、值得注意的 `rising`，各區附 `explore_url`，註明資料來源 `source`。`rising`／`top`／`top_countries` 為 `null` 表示來源不支援，跳過該項；`[]` 需先看所屬單位 `status`，失敗與沒有結果分開說明。
- 依 `scale` 註記：`per_request_0_100` 寫「0–100 是相對指數，地區之間不可比較」，不同請求之間亦不可直接比較；`consistent` 依來源實際支援範圍說明能比較哪些資料。兩者都加上「中國無資料，韓國和日本的 Google 市佔偏低，只能當參考」。
- 頂層 `unavailable` 時本節只寫一行「本次無法取得 Google Trends 資料（原因；來源：source）」。

第 11 節的平台覆蓋表加上一列 Google Trends：`ok` → `full`、`partial` → `partial`、`unavailable` → `blocked`，附上原因。

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

Do not stop at keyword searches. Also cover these first-hand channels (they are often missed):
1. Official / organizer site: enumerate EVERY news/blog post (list page, sidebar, sitemap.xml), not just
   the ones search engines surface. Record title + publish date (JSON-LD "datePublished" or the page's
   own date). Look for outcome reports, rule changes, sold-out / schedule notices.
2. Official accounts' own timelines after the event date (organizer, venue/partner, creator/company):
   X, Plurk, IG, FB, YouTube community/streams. Use search-engine index for login-walled ones.
3. First-hand reports: search the region's words for visit reports / reviews / unboxing
   (zh-tw e.g. 心得, 打卡, 開箱, 去了, 吃了; ja e.g. 行ってきた, レポ; en e.g. "went to", review).
4. Pages where text seems missing: WebFetch strips <script>. Read embedded JSON in the raw HTML before
   marking anything unverifiable: YouTube ytInitialPlayerResponse.videoDetails (shortDescription,
   viewCount); Plurk "plurk = {...}" (favorite_count, replurkers_count, response_count); JSON-LD datePublished.

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
2. 新建 RUN，先將 `PREV/verify.json` 複製為 `RUN/verify.json`，再執行 A.5；跳過 A，brief-b 要求先查有無新官方公告並更新 timeline。
3. 一樣執行 A.5 重抓搜尋熱度，再將相關上升搜尋補進 brief-b；brief-b 帶入 PREV `raw/*.json` 的 `queries`，`SINCE` = PREV 的報告日期。
4. 報告第 1 節之後插入「與上次（YYYY-MM-DD）相比的變化」：新事件、風向轉變、新謠言、已澄清事項，以及搜尋熱度比較（高峰日期、目前熱度相對於上次高峰的變化）。`scale: per_request_0_100` 時，兩次期間不同、各自正規化，數值不能直接相減，只比較高峰日期與走勢方向；缺資料就說明無法比較。

## 鐵則

- 沒有來源的論點不寫進報告；查證由 `pulse.py` 與主對話負責，不採信 agy 自稱完成查證。
- 不登入、不繞過登入牆或反爬機制。
- 不算情緒百分比；不自動排程（要定期追蹤用 `/loop` 包 `--update`）。
- 第一版不拆多 pane 平行跑。
