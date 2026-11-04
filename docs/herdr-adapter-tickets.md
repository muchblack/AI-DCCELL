# 其他 skill 改走 herdr-ctl adapter：票

> 2026-11-04 用 `/to-tickets` 拆票，**只寫成 md，不發布到 Linear**。
> 前一張（herdr-dev 本身支援 Herdr desktop）已完成：commit `867bf37`。

**結論**：拆成 7 張票。票 1 是前置重構，沒有 blocker；票 2～7 都只被票 1 擋住，彼此之間沒有依賴，票 1 做完後可以並行。

**需要決斷**：無。三個決斷都已經拍板，見下方「已定案」。

**需要討論**：php-exec 說明裡「sandbox 會換掉 `$HOME`」在 hc 終端機上是否成立，要等票 7 實測後才知道。

| # | 票 | 嚴重度 | Blocked by |
|---|---|---|---|
| 1 | herdr-ctl adapter 搬到共用 scripts 目錄 | High | — |
| 2 | health-check 在 Herdr desktop 上正確判斷 agent 是否可用 | Medium | 1 |
| 3 | topic-pulse 在 Herdr desktop 上能派工 | Medium | 1 |
| 4 | ask 在 Herdr desktop 上能用，而且只叫醒 main 一次 | High | 1 |
| 5 | dispatch 在 Herdr desktop 上能用，而且只叫醒 main 一次 | High | 1 |
| 6 | herdr-mkt 在 Herdr desktop 上能用，改用 wait-result 等待 | Medium | 1 |
| 7 | job104、career-ops 用 cwd 找審稿 agent；php-exec 說明依實測更新 | Low | 1 |

## 已定案（所有票共用）

1. adapter 的正式位置是 `~/.claude/skills/scripts/herdr-ctl.sh`。`herdr-dev/scripts/herdr-ctl.sh` 留一個轉呼叫，現有呼叫不能壞。
2. 原本用 `prompt --wait` 的地方，一律改成「送出 prompt 不等待」加上背景執行 herdr-dev 的 `wait-result.sh`。對方寫的回覆檔，第一行必須是這次派工的 `dispatch_id: <id>`。
3. 「同一個 workspace」一律改成「cwd 相同」，兩個後端用同一套規則判斷。

## 共用完成條件（每張票都適用）

- 該 skill 底下沒有任何直接呼叫 `herdr agent`、`herdr pane`、`herdr worktree` 的地方，全部改走 adapter。
- 送給其他 agent 的 brief 都要寫明：只把結果寫進檔案，不執行 herdr、hc、herdr-ctl.sh 指令。原因是 hc 會把訊息包成 `<hc from="…">`，對方可能會試著用 `hc send` 回話，結果打進 main 的對話裡。
- 在 Herdr desktop 上實際跑過一次，留下指令和關鍵輸出（每項 20 行以內）。
- TUI 後端的行為和改之前一樣。

adapter 的輸出格式（這是已定的介面，各票照這個寫）：`list` 每行 `<id>\t<agent>\t<status>\t<cwd>`；agent 名稱已經正規化（`antigravity` 會顯示成 `agy`）；`status` 只會是 `idle`、`working`、`blocked`、`done`、`unknown` 其中一個；`wait` 的逾時單位是秒。

---

## 票 1：herdr-ctl adapter 搬到共用 scripts 目錄

**嚴重度**：High

### What to build

其他 skill 改用 adapter 時，不必寫死 herdr-dev 的路徑。adapter 和它的測試搬到共用 scripts 目錄，跟 `linear-ws.sh`、`mem-recall.sh` 放在一起。herdr-dev 原本的路徑留一個轉呼叫，herdr-dev、topic-pulse 現有的呼叫都照常可用。herdr-dev 的文件改成指向新位置。

### Acceptance criteria

- [ ] adapter 的測試在新位置、在 `HERDR_BACKEND=tui` 和 `hc` 兩個後端下都通過。
- [ ] herdr-dev 的 `wait-result`、`approve-loop` 測試在兩個後端下都通過（證明轉呼叫有效）。
- [ ] 用舊路徑和新路徑各跑一次 `list`，輸出相同。
- [ ] 用 symlink 或相對路徑呼叫舊路徑，也能找到新位置的 adapter。

### Blocked by

None — can start immediately.

---

## 票 2：health-check 在 Herdr desktop 上正確判斷 agent 是否可用

**嚴重度**：Medium

### What to build

共用的 health-check 目前靠 TUI 版 herdr 列出 agent，判斷 codex、agy、gemini 能不能用。在 Herdr desktop 上 TUI 的 herdr 不一定在跑，結果會把明明在跑的 agent 誤報成 down。改成透過 adapter 列 agent 之後，兩個後端都能判斷正確，回傳的 JSON 格式不變。

### Acceptance criteria

- [ ] 有對應 agent 時回 `up`，沒有時回 `down`，兩個後端都不在時回 `down`。兩個後端都用假的 stub 測過。
- [ ] 錯誤訊息不再綁特定後端，例如不再寫「herdr agent list failed」。
- [ ] 回傳的 JSON 欄位和改之前一樣。
- [ ] 在 desktop 上實際查 agy，回 `up`。
- [ ] hf-image 用到的 `hf` 檢查行為不變。

### Blocked by

- 票 1

---

## 票 3：topic-pulse 在 Herdr desktop 上能派工

**嚴重度**：Medium

### What to build

topic-pulse 已經用 `wait-result.sh` 等待，只剩三個步驟直接呼叫 TUI 版 herdr：找閒置的 agy、送 prompt、出狀況時讀畫面。這三步改走 adapter 後，在 desktop 上也能把查證工作派給 agy，並優先挑 cwd 相同的那一個。

### Acceptance criteria

- [ ] 符合共用完成條件。
- [ ] 找 agy 時只挑狀態是 `idle` 的，cwd 相同的優先。
- [ ] 在 desktop 上跑一次最小的話題查詢，`wait-result` 回傳 `RESULT_READY`。

### Blocked by

- 票 1

---

## 票 4：ask 在 Herdr desktop 上能用，而且只叫醒 main 一次

**嚴重度**：High（linus-review 的交叉審查會用到 `/ask`，在 desktop 上目前完全跑不動）

### What to build

`/ask` 在 desktop 上可以把問題送給 codex 或 agy，並拿回答案。等待改用 `wait-result`：對方中途閃一下 idle 不會再提早叫醒 main，main 只在拿到這次的回覆時醒來一次。給對方的 brief 範本第一行放 `dispatch_id`，並要求回覆檔第一行照抄。`wait-result` 的五種結果各自怎麼處理，寫進 skill 說明。

### Acceptance criteria

- [ ] 符合共用完成條件。
- [ ] 在 desktop 上 `/ask agy` 一個小問題，main 只被叫醒一次，收到的是 `RESULT_READY`。
- [ ] 回覆檔留著上一輪的舊內容時，不會被當成這次的答案（回傳 `SETTLED_NO_RESULT`）。
- [ ] 對方卡在權限提示時，main 會收到 `BLOCKED` 並讀畫面，不會一直等下去。

### Blocked by

- 票 1

---

## 票 5：dispatch 在 Herdr desktop 上能用，而且只叫醒 main 一次

**嚴重度**：High（開發流程跨 provider 分工時會用到 `/dispatch`，在 desktop 上目前完全跑不動）

### What to build

`/dispatch` 在 desktop 上能自動偵測有哪些 provider 在跑，把需求拆成子任務派出去，最後整合結果。每個子任務有自己的 `dispatch_id`，在背景各自跑一個 `wait-result`。派工前檢查舊對話、回來後讀結果，都改走 adapter。子任務 brief 範本照票 4 的格式。

### Acceptance criteria

- [ ] 符合共用完成條件。
- [ ] 可用的 provider 改由 adapter 的 `list` 判斷，兩個後端列出的 provider 名稱一致。
- [ ] 在 desktop 上把一個需求拆給 codex 和 agy 兩個子任務，兩邊都回傳 `RESULT_READY`，main 整合兩份結果。
- [ ] 兩個子任務互不干擾：一邊卡住或沒交結果，不影響另一邊回傳。

### Blocked by

- 票 1

---

## 票 6：herdr-mkt 在 Herdr desktop 上能用，改用 wait-result 等待

**嚴重度**：Medium（herdr-mkt 目前還是草稿版 skill）

### What to build

herdr-mkt 的研究、策略、文案、視覺、審稿各個角色，在 desktop 上都能派工並拿回產出。它為了補 `prompt --wait` 提早回傳的問題，自己寫了一個「等檔案出現」的輪詢迴圈，這個迴圈要刪掉，改成 `wait-result`。各角色的產出檔第一行都寫 `dispatch_id`。綁定角色、`--resume` 重新找 pane，都改走 adapter。

### Acceptance criteria

- [ ] 符合共用完成條件。
- [ ] skill 裡不再有自己寫的檔案輪詢迴圈。
- [ ] 在 desktop 上跑一次 quick 模式，跑到策略產出為止，每個角色各回傳一次 `RESULT_READY`。
- [ ] 文案和視覺仍然在同一回合並行派出。
- [ ] 策略產出後仍然停下來等使用者核准，這個規則不變。

### Blocked by

- 票 1

---

## 票 7：job104、career-ops 用 cwd 找審稿 agent；php-exec 說明依實測更新

**嚴重度**：Low

### What to build

job104 和 career-ops 的雙審流程，原本是找「同一個 workspace」裡的 codex 和 agy。hc 沒有 workspace 的概念，改成找 cwd 等於目前專案目錄的那一組，兩個後端用同一套規則。php-exec 說明裡「herdr 的 sandbox 會換掉 `$HOME`」這段，先在 desktop 的 codex 和 agy 裡實測，再依結果更新。

### Acceptance criteria

- [ ] job104、career-ops 符合共用完成條件。
- [ ] cwd 不同的 codex／agy 不會被選中。
- [ ] 在 desktop 上跑一次 job104 的雙審流程，兩份審稿都有產出。
- [ ] php-exec 的說明附上實測結果：兩個後端各自的 `$HOME` 值，以及要不要加前綴。

### Blocked by

- 票 1

---

## 不開票

- linus-review 說明裡「`/ask` 透過 herdr 傳送」那句：只是描述，沒有實際呼叫。票 4 做完後這句話自然成立，不用改。
