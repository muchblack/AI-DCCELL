---
name: topic-pulse
description: >-
  跨區域輿情分析：查證話題真實性後，收集新聞媒體、中文（台港／中國）、英、日、韓社群的意見反應並產出摘要，
  附完整來源、原文引述、平台覆蓋狀況、擴散路徑、謠言與澄清。由 agy 原生工具鏈執行搜尋與查證，
  網址與數字經腳本稽核與抽查後產出報告。
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

搜尋熱度需設定環境變數 `SERPAPI_API_KEY`，每份報告約用 9 次 SerpApi 額度（四區各 2 次＋全球 1 次）。未設定或查詢失敗仍繼續產出報告。

## 產出目錄

`RUN = <cwd>/pulse/<slug>-<YYYYMMDD>/`（slug：英文小寫、連字號，例 `blue-archive-nexon`）

```
verify.json               階段 A 事件查證與關鍵字
trends.json               階段 A.5 搜尋熱度（含來源、比例尺、狀態與原因）
raw/<region>.json         階段 B 各區原始資料（地區 key：zh-tw, zh-cn, en, ja, ko, media）
check.md                  階段 C 查證與抽查紀錄
report.md / report.html   最終報告
```

腳本路徑：`S = ~/.gemini/config/skills/topic-pulse/scripts/pulse.py`

## 平台表

| 區域 | 遊戲／動漫 | 科技 | 時事／娛樂 |
|---|---|---|---|
| zh-tw（台港） | 巴哈姆特、PTT、YouTube、Plurk、Threads、Facebook | PTT、Mobile01、Dcard | PTT、Dcard、Threads、LIHKG |
| zh-cn | NGA、百度貼吧、Bilibili、微博 | 知乎、V2EX | 微博、小紅書、知乎 |
| en | Reddit、ResetEra、X、YouTube、Steam | Reddit、Hacker News | Reddit、X |
| ja | 5ch、X、YouTube、はてなブックマーク、Yahoo!リアルタイム検索 | はてなブックマーク | Yahoo!ニュース、X |
| ko | Ruliweb、DC Inside、Inven、YouTube | Clien | Naver、theqoo |
| media | 評分站（OpenCritic、Metacritic）＋各區主流媒體 | 同左 | 同左 |

已知封閉平台（多半 `partial`／`blocked`）：微博、小紅書、Plurk、Facebook、Threads、X。改走替代路線：搜尋引擎索引、媒體報導、轉貼到開放平台的內容。

YouTube 跨區：官方直播／PV 留言區常是第一手反應，留言**依語言歸區**，不依平台（日文留言 → `ja`）。中國區用 Bilibili 代替（YouTube 被牆）。

## 執行流程

### 0. 準備階段
1. 解析參數，決定 slug 與題材類別。
2. 建立目錄 `RUN/raw/`。

### A. 事件查證與關鍵字生成
1. 使用原生 `search_web` 尋找第一手官方消息（官方公告、直播、新聞稿、官方社群貼文）。
2. 判定事件真實性：`confirmed`｜`partial`（註明未證實部分）｜`not_found`。
3. 建立事件時間軸（日期、事件、來源網址）。
4. 建立各區搜尋關鍵字：官方譯名、常用簡稱／俗名、社群黑話。
5. 寫入 `RUN/verify.json`（UTF-8）：
   ```json
   {
     "status": "confirmed|partial|not_found",
     "status_note": "...",
     "event_date": "YYYY-MM-DD",
     "sources": [{"url": "...", "date": "...", "title": "...", "primary": true}],
     "timeline": [{"date": "...", "event": "...", "url": "..."}],
     "keywords": {"zh-tw": ["..."], "zh-cn": ["..."], "en": ["..."], "ja": ["..."], "ko": ["..."]}
   }
   ```
6. **檢查點**：
   - `status: not_found` → 中止流程，於 Session 回報查無此事與已查證來源，不進行階段 B。
   - `confirmed` / `partial` → 進入階段 B（`partial` 於報告第 2 節標明未證實部分）。

### A.5 搜尋熱度
1. 執行 `python3 S trends RUN`，數字由腳本直接抓取，不手抄。
2. 讀 `trends.json` 各區的 `rising`，挑出與話題相關的詞補進階段 B 的關鍵字。`rising` 是 `null`（來源不支援）就跳過；先看各區 `status`，失敗請求的 `[]` 不代表沒有搜尋結果。
3. `status: unavailable` 不中止，直接進 B，報告註明本次無資料；`partial` 保留成功資料並說明缺漏。

### B. 逐區收集輿情
依序處理各區：`media` → `zh-tw` → `zh-cn` → `en` → `ja` → `ko`。
1. 使用該地區語言關鍵字與 `search_web`（配合 `site:` 針對平台搜尋）。
2. 遭遇登入牆／反爬機制時不強制繞過，標註覆蓋狀態（`partial` / `blocked`），改採搜尋引擎摘要或轉載內容。
   不要只做關鍵字搜尋，以下第一手管道也要逐一查（常被漏掉）：
   - **官方／主辦網站**：逐篇列出所有公告／部落格貼文（列表頁、側欄、`sitemap.xml`），不只看搜尋引擎找得到的。記錄標題與發布日（JSON-LD `datePublished` 或頁面日期），留意活動結果、規則變更、售完或時程異動公告。
   - **官方帳號事件後的動態**：主辦、場地／合作方、創作者／公司在 X、Plurk、IG、FB、YouTube 社群與直播的貼文；有登入牆的走搜尋引擎索引。
   - **第一手心得**：用該區語言搜尋到場心得、評價、開箱（中文：心得、打卡、開箱、去了、吃了；日文：行ってきた、レポ；英文：went to、review）。
   - **頁面看似沒內容時**：WebFetch 會拿掉 `<script>`，先讀原始 HTML 內嵌的 JSON（YouTube `ytInitialPlayerResponse.videoDetails`、Plurk `plurk = {...}`、JSON-LD `datePublished`），再決定是否標「無法驗證」。
3. 每個地區產出 `RUN/raw/<region>.json`（UTF-8）：
   ```json
   {
     "region": "zh-tw",
     "platforms": [{"platform": "PTT", "coverage": "full|partial|blocked", "reason": "..."}],
     "items": [{
       "kind": "community|media",
       "platform": "PTT",
       "url": "<完整網址>",
       "date": "YYYY-MM-DD",
       "title": "...",
       "count": 796,
       "count_estimated": false,
       "count_note": "...",
       "claim": "<重點說明>",
       "quote_orig": "<原文引述>",
       "quote_zh": "<白話繁中翻譯>",
       "stance": "正面|負面|分歧|中立",
       "group": "老玩家"
     }],
     "diffusion": ["<擴散路徑與網址>"],
     "rumors": [{"rumor": "...", "clarification": "...", "url": "..."}],
     "scams": [{"description": "...", "url": "..."}],
     "queries": ["<所有執行的搜尋語法>"]
   }
   ```
4. **硬性規則**：
   - 僅收錄完整 URL，嚴禁省略號截斷；網域必須與標註平台吻合。
   - 社群條目必須附帶實際頁面上的原文引述（verbatim quote）。
   - 互動數量（推文數、回覆數、樓層）必須為頁面可見數值，無數據填 `null`，嚴禁虛構百分比。

### C. 數據稽核與查證
1. 執行檢查腳本：`python3 S check RUN --spot 5`。
2. 檢視輸出之 FAIL / WARN / SPOTCHECK 清單：
   - 若有 FAIL 或格式錯誤，直接修正對應的 `raw/<region>.json` 條目。
   - 針對抽查條目確認引述內容與頁面相符。
   - ⚠️ **抽查技巧**：WebFetch 等純文字抽取工具會過濾掉 `<script>` 標籤，看不到內容或數字時**不要直接判定為「需要 JS 才看得到」或「無法驗證」**。應先透過抓取原始 HTML，檢查內嵌之 JSON 資料包：
     - **YouTube**：讀取 `ytInitialPlayerResponse` 內的 `videoDetails.shortDescription`（說明欄全文）與 `viewCount`（觀看數）。
     - **Plurk**：讀取 `plurk = {...}` 物件內的 `favorite_count`（喜歡數）、`replurkers_count`（轉噗數）與 `response_count`（回應數）。
     - 兩者皆查無資料時，才標記為「無法驗證」。
3. 核對時間軸與數字邏輯。
4. 將稽核摘要與抽查結果記錄於 `RUN/check.md`。

### D. 產出報告
1. 依下方標準報告格式撰寫 `RUN/report.md`。
2. **語氣與語感規範**：
   - 全文使用**現代、流暢、通順的繁體中文**說明（去 AI 味、平實自然、專業清晰）。
   - 論點需有佐證：媒體觀點附評分或報導連結，社群觀點附原文引述與白話翻譯。
   - 數量只寫可查證的數字（加「約」），只描述「普遍／分歧／少數」，不使用臆測的百分比。
3. **⚠️ 邊界隔離原則**：
   - 產出的報告檔案（`report.md` 與 `report.html`）屬於給真人讀者閱覽的客觀研析報告。
   - **嚴禁在報告內容中出現「阿斯拉」、「駕駛員」、「遙測」、「賽道分析」等 AI 角色名詞或專用語彙**。
   - 所有角色對話與狀態回報僅存在於對話終端 Session 內。
4. 若指定 `--html` 參數，執行 `python3 S html RUN/report.md --hue N` 產出 `report.html`。N 是配色色相（0–359），依話題主視覺挑一個：櫻花粉 335、抹茶綠 140、海藍 210、橘 25、紫 275；挑不出就省略（預設 210）。標題下方自動加總結卡片，搜尋熱度一節自動插入各區長條圖，數字都從 RUN 內檔案讀取。
5. `--html` 依固定寫法把各節轉成版面元件，照下列寫法才會套用（不符就原樣輸出）：
   - 事件查證：清單項目寫成「標籤：內容」（標籤 2–10 字）→ 欄位表；未證實寫成 `⚠️ 未證實：` 加清單 → 提示框；行內 `⚠️ 未證實`／`⚠️ 無法驗證` → 標籤。
   - 時間軸：`| 日期 | 事件 | 來源 |` 表格 → 時間軸列表。
   - 媒體／社群引文：一條一句，寫成 `- 來源（平台）：「原文」譯：譯文 [連結](url)` → 引用卡片（譯文可省）。
   - 族群分析：`- **族群**：說明` → 卡片。擴散路徑：一段 `A（日期）→ B（日期）→ …。補充` → 流程圖。
   - 待觀察事項：`- 日期：事項`（日期以數字開頭，或寫「未定」）→ 日期列表。附錄：`### 來源清單…`、`### 搜尋指令…` → 可收合區塊。
6. 搜尋熱度一節依 `trends.json` 撰寫：各區 `peak` 對照時間軸事件、`timeline` 說明走勢；`per_request_0_100` 要註明「0–100 是相對指數，地區之間不可比較」，並加上「中國無資料，韓國和日本的 Google 市佔偏低，只能當參考」；頂層 `unavailable` 時只寫一行原因。平台覆蓋表加一列 Google Trends（ok→full、partial→partial、unavailable→blocked）。

### E. 回報駕駛員
在終端對話 Session 中，以阿斯拉格式呈報：
- 一句話結論（話題核心現況）
- 遙測數據（條目數、驗證狀態、平台覆蓋、未證實項目）
- 報告檔案路徑（以 `file://` 連結點擊）
- 後續建議行動
- 完整報告全文不直接貼入對話，引導駕駛員開啟檔案閱覽。

## 報告格式

```markdown
# <話題> 輿論摘要分析（截至 YYYY-MM-DD）
1. 結論（先講事件本質與整體風向，可以不只一句）
2. 事件查證（第一手官方來源、屬實程度評估）
3. 事件發展時間軸
4. 搜尋熱度
5. 媒體觀點與專業評測（主流媒體報導角度、評分、主要論述）
6. 各地區社群反應（每區 2–3 個討論焦點，附原文引述與白話譯文）
7. 受眾族群分析（核心玩家／一般大眾／海外圈／二創圈…依題材劃分）
8. 跨區域對比與落差分析（媒體與社群落差、各地區關注點差異）
9. 擴散路徑梳理
10. 爭議、謠言與官方澄清
11. 平台覆蓋與觀測限制（full / partial / blocked 及原因）
12. 後續觀察重點（附預定日期或里程碑）
13. 行動建議（選用：針對關注此話題之決策或因應建議）
附錄：### 來源清單（完整 URL）、搜尋指令清單、`### 未證實條目（N）`（N 為條數，沒有就寫 0；`--html` 據此產生總結卡片）
```

## --update 追蹤模式

1. 尋找既有 `pulse/<slug>-*/` 中最新版本作為 PREV。
2. 建立新 RUN 目錄，沿用 PREV 的 `verify.json` 並查核有無最新官方動態以更新 timeline；同樣執行 A.5 重抓搜尋熱度。
3. 繼承 PREV `raw/*.json` 的 `queries`，`SINCE` 設為 PREV 報告日期。
4. 於新報告第 1 節後追加「與上次（YYYY-MM-DD）相比的變化」。

## 鐵則

- 沒有來源的論點不寫進報告；依賴 `pulse.py` 嚴格檢驗與抽查。
- 不嘗試繞過登入牆或反爬機制。
- 不臆測情緒百分比；不自動排程。
- 專屬於 agy 環境原生執行，不依賴外部 herdr 或跨 CLI 派工。
- 角色設定僅限於 Session 對話，不得滲透至報告實體檔案中。
