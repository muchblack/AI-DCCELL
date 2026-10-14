---
name: job104
description: >-
  104 人力銀行求職助手：抓 JD、快速看懂職缺並跟履歷對照、寫自我推薦信
  （初稿 → herdr 雙審 → 說人話潤稿）。資料都放在 ~/documents/self/。
  Triggers on: 104 職缺, 看一下這個職缺, 這份工作內容是, 那這份呢,
  104.com.tw/job/, 自我推薦信, 推薦信, 求職信.
  Examples: "/job104 look https://www.104.com.tw/job/8x35q",
  "/job104 cover <url> <url> <url>", "/job104 list".
argument-hint: "look|cover|list [url ...]"
metadata:
  short-description: 104 職缺速查 + 履歷對照 + 推薦信產線
---

# job104：104 職缺速查與推薦信

使用者貼 104 職缺網址（`https://www.104.com.tw/job/<id>`），或只說「那這份呢」時，就用這個 skill。
只說「那這份呢」卻沒附網址時，直接問網址，不要猜是哪一份。

## 固定路徑

| 用途 | 路徑 |
|---|---|
| 履歷（事實來源） | `~/documents/resume_text.md`（主）、`~/documents/resume.md`（詳細版，含自傳） |
| JD 原文 | `~/documents/self/jd/<公司簡稱>-<職位>.txt`，第一行是 `來源：<104 網址>` |
| 推薦信 | `~/documents/self/<公司簡稱>-<職位>.md` 和 `.txt` |
| 過程檔 | `~/documents/self/drafts/`（v1 初稿、v2 審後、v3 潤稿）、`~/documents/self/reviews/` |

檔名一律用「公司簡稱-職位」，不用 104 的職缺代碼。公司簡稱取大家認得的名字，例如 `vocus新銳數位`、`TransBiz睿博數位行銷`。

## 抓 JD（所有子指令共用）

```bash
python3 -I ~/.claude/skills/job104/scripts/fetch_104.py <url-or-id> \
  --save-dir ~/documents/self/jd --name <公司簡稱>-<職位>
```

- **不要用 WebFetch**，104 會回 402。裸 curl 會被 Cloudflare 擋（403 challenge）。腳本打的是 `ajax/content/<id>`，並帶上完整的瀏覽器 header。
- curl 拿到的不是 JSON 時，腳本會自動改用 Playwright（`scripts/fetch_104_browser.cjs`）：開 headless Chromium 進職缺頁，等 Cloudflare challenge 過了，再在頁面裡呼叫同一個 ajax 端點。stderr 會印 `[playwright] …` 說明原因。需要全域安裝的 playwright 和 Chromium（`pnpm add -g playwright && playwright install chromium`）。想直接走瀏覽器就加 `--browser`。
- 回應是 JSON 但沒有 `data`，代表職缺已關閉或代碼錯誤，這種情況不會改用瀏覽器重試。
- 先不加 `--save-dir` 跑一次，看了公司和職位名稱再決定檔名，然後存檔。
- 抓不到時（腳本 exit 1），請使用者貼 JD 文字，不要憑網址猜內容。

## Jev 契合度評分（`look` 和 `list` 共用，輔助訊號）

JD 存檔後，用 TypeSafe Jev 對「JD × 履歷」打三個分數、判斷一個職務類型，存成 `self/jd/<名稱>.jev.json`。`look` 的第 7 步拿來參考，`list` 拿來排序。

- **資料說明**：這一步會把 JD 和 `resume_text.md` 送到 TypeSafe（第三方服務）。送出前刪掉 `- 姓名：` 那一行，其他照原文
- 請求檔放 `~/documents/self/drafts/jev-<名稱>.json`，用完刪掉：

```json
{
  "model": "jev-latest",
  "state": {"jd": "<JD 原文>", "resume": "<resume_text.md，去掉姓名行>"},
  "questions": {
    "role_type": {
      "type": "choice",
      "instructions": "What kind of role does `jd` describe?",
      "criteria": {
        "development": "Mainly writing and maintaining product or platform code.",
        "technical_support": "Customer-facing support, implementation, integration or pre-sales engineering; coding is secondary.",
        "management": "Mainly leading people or projects; hands-on coding is a minor part.",
        "non_engineering": "Not an engineering role."
      }
    },
    "must_have_coverage": {
      "type": "score",
      "instructions": "How many of the required (not nice-to-have) qualifications in `jd` are backed by concrete evidence in `resume`?",
      "criteria": [
        "Few or none of the required qualifications are backed by `resume`.",
        "Some are backed; several important ones have no evidence.",
        "Most are backed; one or two have no evidence.",
        "Every required qualification is backed by specific evidence in `resume`."
      ]
    },
    "stack_fit": {
      "type": "score",
      "instructions": "How closely does the technology stack in `jd` match the stack used in `resume`?",
      "criteria": [
        "Different stack across backend, frontend and data layers.",
        "Same general area, but the main language or framework differs.",
        "Main language and framework match; some secondary tools differ.",
        "Main language, framework and most named tools match."
      ]
    },
    "seniority_level": {
      "type": "score",
      "instructions": "Compared with the experience shown in `resume`, what level does `jd` target?",
      "criteria": [
        "Entry or junior level, far below the experience in `resume`.",
        "Mid level, somewhat below the experience in `resume`.",
        "Senior level, matching the experience in `resume`.",
        "Lead, architect or manager level beyond what `resume` shows."
      ]
    }
  }
}
```

- 呼叫：`bash ~/.claude/skills/scripts/jev.sh ~/documents/self/drafts/jev-<名稱>.json`。exit 非 0（沒有 key、逾時、錯誤）就**跳過整段**，`look` 照常輸出，`list` 那欄留空。不要每次都提醒沒 key，第一次提一句就好（key 放在 `~/.config/typesafe/.env` 的 `TYPESAFE_API_KEY`）
- 存檔內容：`{"model", "date", "role_type", "role_probs", "must_have", "stack", "seniority", "confidence": {...}, "fit"}`，數值直接從 `answers.<id>.score`、`.choice`、`.probabilities`、`.confidence` 抄
- 契合度用程式算，權重寫在這裡，調權重不用重打 API：

  ```
  seniority_fit = max(0, 1 - |seniority - 2| / 2)
  fit = round(100 * (0.4 * must_have / 3 + 0.3 * stack / 3 + 0.3 * seniority_fit))
  ```

  `role_type` 不是 `development` 時，不扣分，但要在 `look` 的「⚠️ 特殊注意」寫出來

**怎麼用這些分數：**

- 只是第二意見。`look` 第 6 步的對照還是要逐項附履歷證據，分數不能代替證據
- 分數跟 main 自己的判斷不一致時（例如 main 覺得必要條件幾乎都對得上，`must_have` 卻不到 1.5），回頭重讀那一段 JD；重讀後仍不同意，就以 main 的判斷為準，不改分數檔
- 某一題 `confidence < 0.5`，代表模型自己也拿不準，`list` 那格加註 `?`
- 對使用者呈現時寫成「契合度 72（參考）」，並附一句是哪一項拉低分數

## `look <url>`：這份工作在做什麼

輸出順序固定，用繁體中文：

1. **一句話定位**：公司、職稱、JD 更新日期
2. **基本條件**：薪資、地點、遠端程度、人數、經歷和學歷門檻、104 職類
3. **⚠️ 特殊注意**（有才寫）：只收外部申請表、語言列為 essential、職類掛「助理工程師」這種職級訊號
4. **工作內容**：依 JD 分組，保留百分比配比；最後一句說白話，例如「這是面對客戶的技術支援，不是開發職」
5. **必要條件／加分條件**：分開列
6. **跟履歷對照**：
   - 對得上的：每一項都要附履歷裡的具體證據（公司、數字、技術）
   - 主要缺口：必要條件缺的放前面，加分條件缺的放後面
7. **我的看法**：值不值得投、優先順序，並跟本 session 已經看過的職缺比較（薪資、職級、技術棧、遠端）。職級或薪資明顯不合時要直說。有 Jev 分數就附上契合度和拉低分數的那一項（見上方「Jev 契合度評分」）
8. 最後一行說明 JD 存到哪裡，並問要不要寫推薦信

判斷時要注意的訊號：
- 職類掛「客服工程師」「業務支援工程師」→ 不是開發職
- 月薪下限遠低於使用者資歷，或經歷只要求 1 年 → 初中階缺，會有大材小用的疑慮
- 技術棧整套不同（後端、前端、資料庫都換）→ 值得投，但推薦信要正面處理換技術棧，不能假裝會

## `cover <url ...>`：寫自我推薦信

使用者指定的順序是 **寫 → herdr 雙審 → 說人話潤稿**。跟 career-ops 先潤稿再審的順序不同，以使用者的順序為準。

### 1. 初稿（main 自己寫）

- 每份 JD 挑 2–3 個關鍵要求，每個要求配一段履歷證據。配不到的不硬湊，摘要裡列為缺口
- 長度 400–500 字（不含空白），104 繁中，分 3–4 段，結構是：應徵什麼、為什麼 → 證據 → 誠實但不自貶的缺口 → 一句邀約
- JD 有指定題目時一定要回答（例：「分享一個發現問題並推動改善的經驗」）
- **送審前先自查有沒有捏造**：履歷沒寫的細節（誰發現的、花多少時間、客戶怎麼回報、「習慣跟客戶來回確認」這類推論）一律刪掉或改成履歷原句。不可以留 `（需補充：…）` 這種佔位字串送出去。缺料就在摘要裡問使用者
- 存成 `drafts/<名稱>.md`

### 2. herdr 雙審（agy、codex 平行）

`herdr agent list` 找出同一個 workspace 裡的 agy 和 codex pane，送**同一份英文 prompt**，只換掉輸出檔名：

- 唯讀，只准寫 `self/reviews/review_<agent>.md`
- 給它們：草稿、JD 檔、`resume_text.md`、`resume.md` 的路徑
- 要審四件事：事實保真（每個數字、公司、技術都要找得到出處）、跟 JD 的對應、語氣是否符合資深職位與長度、AI 腔和中國用語
- 每條意見標 `[MUST]/[SHOULD]/[NIT]`，並附具體改寫

派出去後，用背景的 `until` 迴圈等兩個檔案都寫出來，**而且兩個 pane 都不是 working 狀態**才去讀（codex 檔案寫出來時常常還在寫）。

### 3. 仲裁（main）

逐條判斷。過去的經驗：

- **codex 的事實查核通常很準**，會抓到講太滿（「這幾年都用 Vue 3」）、年資算法（全職年資和後端年資不一樣）、履歷沒寫的推論（「接案型公司」「跨語言接手系統」），這類意見要採用
- **agy 的方向通常對**（太長、自貶、漏掉加分項），**但它附的改寫版常常加料**：編出履歷沒有的事（「發現現場耗費大量人力」「能無縫切換 FastAPI」「全力配合晚上會議」），或用浮誇的詞（「高度契合」「深諳」「徹底解決」），改寫版不能直接用
- JD 的必要條件如果牽涉使用者個人意願（晚上開會、出差、搬到外地），履歷沒寫就不要替使用者承諾，在摘要裡請他確認

採用的意見改進 `drafts/<名稱>_v2.md`。

### 4. 說人話潤稿

套用 `speak-human-tw` 的規則。使用者說了「直接潤稿」，就走「跳過確認、事後摘要」。沒說的話，照該 skill 的規定先列清單、問使用者。保護清單和保真回讀照樣要做完。結果存成 `_v3.md`。

常見要修的地方：好幾個分號串成的長句要拆開、「堅持」這類姿態詞、空泛的結尾（「希望帶進…」）改成具體能接手的事、半形標點。

### 5. 產出與回報

- `self/<名稱>.md`：開頭寫公司、職位、JD 網址、日期、事實來源，接著是信件本文
- `self/<名稱>.txt`：只有信件本文，不用 Markdown，可以直接貼到 104
- 回報內容：
  1. 一張表：職缺、字數、這封信主打什麼
  2. 兩位審稿者的意見各採用了什麼、沒採用什麼，附理由
  3. 潤稿改了幾處
  4. **投遞前請使用者確認的事項**：個人意願、缺料的故事細節、職缺本身的疑慮
  5. 履歷裡也找不到的 JD 缺口

## `list`：目前看過的職缺

讀 `self/jd/*.txt` 的前三行，列一張表：公司、職位、薪資、遠端、契合度（`self/jd/<名稱>.jev.json` 的 `fit`，沒有就留空）、有沒有推薦信（`self/<名稱>.txt` 是否存在）。有契合度的依分數由高到低排，沒有的排最後。

## 原則

- **不捏造**：推薦信只能挑選、重排履歷上的內容。缺料就問使用者，不代編
- **不替使用者承諾**：意願、薪資、到職日、能不能出差，一律交給使用者決定
- **不自動投遞**：只準備資料，投不投由使用者決定
- 使用者跟這個 skill 的溝通一律用繁體中文；給 herdr pane 的 prompt 用英文
