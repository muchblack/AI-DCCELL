# topic-pulse：加入 Google Trends 搜尋熱度

## 背景

topic-pulse 目前只收集媒體報導與社群討論，沒有量化的「熱度走勢」。Google Trends 能補上三件事：

1. 話題熱度隨時間怎麼變化，高峰是否對得上時間軸上的事件
2. 各地區的相對熱度
3. 上升中的相關搜尋，可以補進階段 B 的關鍵字表

資料來源：第一版透過 SerpApi（`engine=google_trends`）取得。官方 Google Trends API（alpha）已提出申請，核准後再另開一張票實作。

## 設計原則

- **數字由腳本抓，不經過 agy。** `pulse.py` 自己呼叫 API 並寫入 `trends.json`，所以不需要另外查證 agy 抄來的數字。
- **抓不到也不能卡住流程。** 沒設定金鑰、額度用完、網路錯誤時，照樣寫出 `trends.json`，標記 `unavailable` 並附上原因，流程繼續往下跑，報告寫明「本次無資料」。
- **資料來源可以替換。** 每個來源是一個抓取函式，都回傳同一種格式，用 dict 選擇。不做外掛架構。來源之間的差異（比例尺、支援的功能）記在 `trends.json` 裡，報告依這些欄位決定怎麼寫，不寫死。
- **不加第三方套件。** 用 Python 內建的 `urllib` 呼叫 SerpApi。

## 需求

### 1. `pulse.py trends <run_dir> [--provider serpapi|google]` 子指令

`--provider` 預設是 `serpapi`。`google` 先保留這個名稱：選了會寫出 `status: unavailable`、`reason: "官方 API 尚未實作"`，exit 0。

輸入：`<run_dir>/verify.json`，使用 `event_date` 和 `keywords`。

期間：`event_date` 往前 30 天到今天，格式 `YYYY-MM-DD YYYY-MM-DD`。沒有 `event_date` 就用 `today 3-m`。

地區對應：

| topic-pulse 地區 | geo | 備註 |
|---|---|---|
| zh-tw | TW | |
| en | US | |
| ja | JP | |
| ko | KR | |
| zh-cn | — | 一律 `skipped`，原因是「Google 在中國無資料」 |
| 全球 | （空） | 只用主關鍵字，取國家排名前 10 |

主關鍵字：`keywords.en[0]`，沒有就取第一個有值地區的第一個關鍵字。

每個地區送 2 次請求，再加上 1 次全球請求，一份報告共 9 次：
- `data_type=TIMESERIES`：該區關鍵字前 5 個，用逗號串在同一個 `q` 裡，同區的關鍵字可以互相比較
- `data_type=RELATED_QUERIES`：只查該區第一個關鍵字，rising 與 top 各取前 10
- 全球：`data_type=GEO_MAP_0`，用主關鍵字查國家排名

### 2. SerpApi 的串接細節

- **金鑰**：從環境變數 `SERPAPI_API_KEY` 讀取。沒設定 → 頂層 `unavailable`，`reason: "未設定 SERPAPI_API_KEY"`，不送出任何請求。金鑰不能出現在 `trends.json`、`explore_url`、錯誤訊息或 stdout。錯誤訊息裡如果帶有請求網址，要先把 `api_key` 拿掉再寫出。
- **錯誤**：SerpApi 出錯時回傳的 JSON 會有 `error` 欄位（額度用完、金鑰錯誤、查無結果等），原文寫進該區的 `reason`，狀態標 `error`。HTTP 錯誤或逾時（逾時設 30 秒）重試一次，仍失敗就標 `error`，繼續下一區。
- **對帳**：每次請求都記下 `search_metadata.id`，放在該區的 `search_ids`。
- **explore_url**：優先用回傳的 `search_metadata.google_trends_url`，沒有才依實際查詢參數（date、geo、q）自己組。

### 3. `trends.json` 格式

```json
{
  "status": "ok | partial | unavailable",
  "reason": "",
  "source": "serpapi",
  "scale": "per_request_0_100",
  "fetched_at": "2026-10-27T14:00:00+08:00",
  "timeframe": "2026-09-01 2026-10-27",
  "worldwide": {
    "keyword": "Blue Archive",
    "status": "ok | error",
    "reason": "",
    "search_ids": ["..."],
    "explore_url": "https://trends.google.com/trends/explore?...",
    "top_countries": [{"country": "Thailand", "value": 100}]
  },
  "regions": {
    "zh-tw": {
      "geo": "TW",
      "status": "ok | error | skipped",
      "reason": "",
      "keywords": ["蔚藍檔案", "Blue Archive"],
      "search_ids": ["...", "..."],
      "explore_url": "https://trends.google.com/trends/explore?...",
      "timeline": [{"date": "2026-10-01", "values": {"蔚藍檔案": 42}, "partial": false}],
      "peak": {"date": "2026-10-20", "keyword": "蔚藍檔案", "value": 100},
      "rising": [{"query": "...", "value": "Breakout"}],
      "top": [{"query": "...", "value": 100}]
    }
  }
}
```

欄位規則：
- 頂層 `status`：所有查詢都 ok 是 `ok`；部分成功是 `partial`；全部失敗、沒金鑰或來源尚未實作是 `unavailable`（原因寫在頂層 `reason`）。`skipped` 的地區不影響判定
- `scale`：說明數值能不能跨請求比較
  - `per_request_0_100`：每次查詢各自換算成 0–100，不同請求、不同地區之間不可比較（SerpApi）
  - `consistent`：不同請求之間的比例一致（預留給官方 API，實作時依官方文件確認）
- `rising`／`top`／`top_countries`：`null` 表示這個來源不支援；`[]` 表示有查但沒有結果
- `rising` 的 `value` 保留原始字串（`"Breakout"`、`"+110%"`）；`top` 和 `timeline` 的數值存整數
- `timeline[].date` 一律轉成 `YYYY-MM-DD`；以週為單位的資料取該週的第一天
- 結束代碼：有寫出 `trends.json` 就是 0，連檔案都寫不出來才回非 0

### 4. 流程調整（SKILL.md）

在階段 A 和 B 之間加入「A.5 搜尋熱度（主對話）」：

1. `python3 S trends RUN`
2. 主對話讀 `trends.json` 的 `rising`，挑出和話題相關的詞補進 brief-b 的關鍵字表。不是全部照抄，由主對話判斷要不要收。`rising` 是 `null` 就跳過這一步
3. `status: unavailable` 不用停下來，直接進 B

`--update` 模式：一樣重抓，報告的「變化」一節加上熱度比較（高峰日期、目前熱度相對於上次的高峰）。`scale` 是 `per_request_0_100` 時，兩次查詢的期間不同，數值不能直接相減，只比較高峰日期與走勢方向。

產出清單加上 `trends.json`；用法區塊註明需要設定 `SERPAPI_API_KEY`，以及每份報告約用 9 次額度。

### 5. 報告格式

在「3. 時間軸」後面新增「4. 搜尋熱度」，原本的 4–11 節順延成 5–12。內容：

- 各地區的高峰日期，並和時間軸的事件對照（例：「10/20 高峰，對應官方直播」）
- 全球熱度排名前幾名的國家
- 值得注意的上升搜尋
- 每個地區附上 explore 連結
- 資料說明依 `scale` 決定：`per_request_0_100` 寫「0–100 是相對指數，地區之間不可比較」；`consistent` 改寫可比較的範圍。兩種都要加上「中國無資料，韓國和日本的 Google 市佔偏低，只能當參考」
- `unavailable` 時本節只寫一行「本次無法取得 Google Trends 資料（原因）」
- 註明資料來源（`source`）

「平台覆蓋狀況」一節（新編號 11）加上一列 Google Trends，標示 full／partial／blocked。

### 6. 測試（selftest，不連網路）

把「送出請求」和「整理成 trends.json」拆開，selftest 只測整理的部分，用 SerpApi 回傳格式的固定 JSON 當假資料：

- 正常資料 → timeline、peak、rising／top、top_countries、search_ids、explore_url 正確
- zh-cn → `skipped`，並附上原因
- 沒設定 `SERPAPI_API_KEY` → 頂層 `unavailable`，沒有送出請求，仍然寫出檔案
- 回傳帶有 `error` 欄位 → 該區 `error`、`reason` 是原文，頂層 `partial`
- 送出請求的函式拋出例外（模擬逾時）→ 重試一次後標 `error`
- 錯誤訊息裡的網址帶有 `api_key` → 寫出前已遮掉
- `--provider google` → `unavailable`、原因「官方 API 尚未實作」、exit 0
- 不支援的功能用 `null` 表示 → 報告產生邏輯和 A.5 不會出錯
- `verify.json` 沒有 `event_date` → timeframe 改用 `today 3-m`
- 既有的 selftest 項目全部通過，`check`、`html` 的行為不變

## 不在本次範圍

- 實作官方 Google Trends API 的抓取函式（核准、拿到文件後另開一張票。只需新增一個函式，並確認 `scale` 和各功能是否支援）
- Naver DataLab（韓國）、百度指數或微信指數（中國）
- 用 Knowledge Graph 主題 ID 合併不同語言的關鍵字
- 跨地區的絕對搜尋量換算

## 待確認

- **SerpApi 方案額度**：每份報告約 9 次，每週 3–10 份就是每月約 120–400 次。超過方案額度時要選一種省法：相關搜尋只查主要地區，或 `--update` 時不重抓相關搜尋。開發前先確認方案。

## 驗收標準

1. `python3 pulse.py selftest` 通過，包含上述新案例
2. 設定好 `SERPAPI_API_KEY` 後，用一個真實的 run 目錄執行 `pulse.py trends`：產出的 `trends.json` 符合上面的格式；explore_url 開得起來，看到的走勢和檔案內容一致；`search_ids` 在 SerpApi 後台查得到
3. 沒設定金鑰、或金鑰錯誤時，仍然產出 `status: unavailable` 或 `partial` 的 `trends.json`，exit 0，金鑰沒有出現在任何輸出
4. `--provider google` 產出 `unavailable` 並說明尚未實作
5. SKILL.md 的流程、產出清單、用法和報告格式都已更新，`--update` 段落有提到熱度比較的限制
6. `check` 和 `html` 子指令的行為沒有改變
