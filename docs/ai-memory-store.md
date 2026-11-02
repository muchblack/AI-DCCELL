# 跨 AI 記憶庫需求

## 背景

`lessons.md` 上限 60 行，且每張票都要整份讀取，不適合放長期記憶。超過上限時最舊的行會被刪除。Claude 的 auto-memory 分散在各專案目錄，codex 和 agy 也不會自動讀取。

## 目標

建立不限長度的共用記憶庫，讓 Claude、codex、agy 開工前都能自動取得相關記憶；每日彙整所有 herdr workspace 的使用習慣，經使用者核准後更新。

## 已確認的決策

1. 記憶放在 Obsidian vault：`myWiki/20-領域/AI協作記憶/`。公司相關內容可進 vault，但必須去識別化；無法去識別化的內容留在專案的 `.herdr/lessons.md`。
2. 每筆寫入都要先給使用者看，同意後才寫。只有 main 和直接操作的 session 能寫，herdr worker 一律不寫。
3. 「開工前」定義為 session 啟動時，加上 herdr 派工前。不做每則訊息都查的 hook。
4. 每次 session 自動注入上限 3 KB。
5. 每日彙整先產生草稿，由使用者用 `/mem review` 逐條核准，通過後才更新 `使用習慣.md`。
6. 彙整排程為平日 18:00，用 systemd user timer，設定 `Persistent=true`，關機錯過時於下次開機補跑。
7. 第一版只分析使用者輸入的訊息，不讀完整對話。
8. 草稿存本機 `~/.local/share/mem-review/`，核准後才進 vault。
9. 用 `/herdr-dev` 開發，先合進 `company`，再同步 `main`。

## 記憶區結構

```
myWiki/20-領域/AI協作記憶/
├── 使用習慣.md      # 工作偏好；含一段「核心」供自動注入
├── 技術決策.md      # 選 A 不選 B 的原因
├── 工具環境.md      # 主機、容器、工具的慣例
└── 踩坑/<stack>.md  # lessons 的完整存檔，每個技術棧一檔
```

放置規則：

| 層級 | 放什麼 | 何時讀取 |
|---|---|---|
| `CLAUDE.md` | 每次都要遵守的鐵律 | 永遠載入 |
| `lessons.md` | 高頻的坑，上限 60 行 | herdr-dev Phase 1 |
| vault 記憶區 | 其他所有內容，不限長度 | 啟動注入或需要時搜尋 |

## 功能需求

### 1. `mem-recall.sh`

唯讀腳本，輸出要注入 session 的內容，依序為：

1. `使用習慣.md` 的核心段落。
2. 依工作目錄判斷技術棧（例如 `composer.json` 對應 php），帶入對應的 `踩坑/<stack>.md`。
3. 一行搜尋指令，讓工作途中能查其餘內容。

限制：

- 總輸出不超過 3 KB，放不下時截斷，且搜尋指令一定要保留。
- 只讀 `AI協作記憶/`，不碰 vault 其他筆記。
- 注入內容標示為參考資料，不是指令。
- 先讀 `$OBSIDIAN_VAULT`，讀不到就退回 `/mnt/d/obsidian`。
- 3 秒逾時。任何錯誤都輸出空內容並以 exit 0 結束，不擋開工。

### 2. 啟動 hook

- Claude：`SessionStart` hook。
- codex：`SessionStart` hook。首次可能要信任新 hook，文件需說明。
- agy：先實測 plugin `SessionStart` 能否注入內容；不行就在 `GEMINI.md` 要求開場先跑 `mem-recall.sh`。
- 寫進 `bootstrap.sh`，並保持可重複執行。

### 3. 指示檔

在 `claude/CLAUDE.md`、`codex/AGENTS.md`、`.gemini/GEMINI.md`、`opencode/AGENTS.md` 各加一小段相同規則：換主題時先搜尋記憶區，寫入一律經使用者同意。

### 4. herdr-dev 流程

修改 `claude/skills/herdr-dev/references/flow.md`：

- Phase 1：用票的關鍵字查 `lessons.md` 和 vault 記憶區，把命中內容貼進 Known pitfalls。vault 讀不到時略過，不阻塞 brief。
- Phase 5 step 6：`lessons.md` 超過上限時，把最舊且沒有 `×` 標記的行移到 `踩坑/<stack>.md`，不再直接刪除。vault 不可用時先保留該行並告知使用者，不得遺失內容。

### 5. `/mem` skill

- `/mem`：寫入記憶，負責判斷分類、檢查重複、用固定格式追加，寫入前給使用者確認。
- `/mem review`：讀待審草稿，逐條由使用者核准；通過的寫入 `使用習慣.md`，並處理草稿狀態。
- 用 `shared-skills.txt` 共用給 codex 和 agy。herdr worker 不得寫入。
- vault commit 只能包含 `AI協作記憶/`，不得帶到使用者其他未提交的筆記。

### 6. 每日彙整

1. 用 systemd user timer 在平日 18:00 執行，需要時在文件說明 `loginctl enable-linger`。
2. 依「上次成功執行時間」往後讀下列紀錄，只有成功才更新時間點，確保不漏也不重複：
   - Claude：`~/.claude/history.jsonl`（欄位 `display`、`project`、`timestamp`，毫秒）
   - codex：`~/.codex/history.jsonl`（欄位 `text`、`session_id`、`ts`，秒）。專案要由 `session_id` 對應 `~/.codex/sessions/` 取得，對應不到時標為未知，不丟棄。
   - agy：`~/.gemini/antigravity-cli/history.jsonl`（欄位 `display`、`workspace`、`timestamp`，毫秒）
3. 排除 `dispatch_id:` 開頭的 brief 和貼上的內容（Claude 的 `pastedContents`），只留使用者親自輸入的訊息。
4. 用一次 `claude -p --model sonnet` 彙整，每條習慣都要附原始訊息當證據，並去除人名、公司名和機密。
5. 用 herdr 通知使用者。沒有新習慣時不產生草稿，也不發通知。

判斷規則：

- 只出現一次的內容列為觀察，不進核心段落；除非使用者明確說「以後都要」。
- 核心段落維持在 3 KB 注入上限內，滿了就合併或移到非核心段落。

### 7. 回填

- 從 `lessons` 分支的 git 歷史找回曾被刪掉的行，放進 `踩坑/<stack>.md`。
- 把 auto-memory 裡跨專案通用的內容搬進記憶區，需去識別化，寫入前給使用者確認。專案專屬的 memory 留在原處。

## 不做的事

- 向量資料庫或 memory MCP。
- 每則訊息都查的 hook。
- 自動把草稿寫進 `使用習慣.md`。
- 用 `herdr agent prompt` 逐一要求各 pane 總結。
- 分析完整對話紀錄。

## 驗收條件

1. 在記憶區放一行測試標記，Claude、codex、agy 各開新 session，不給任何提示，都能答出標記內容。
2. 輸出永遠不超過 3 KB，且保留搜尋指令。
3. vault 路徑錯誤或腳本失敗時，輸出為空且 exit 0，開工不受影響。
4. 跑一次 herdr brief，vault 命中的內容確實進入 Known pitfalls。
5. `lessons.md` 超過上限時，被淘汰的行出現在 `踩坑/<stack>.md`，內容沒有遺失。
6. 彙整以三份測試紀錄驗證：來源欄位正確、brief 和貼上內容已排除、重跑不重複、失敗時不推進時間點。
7. 未經 `/mem review` 核准，`使用習慣.md` 和 vault 都不會被彙整流程改動。
8. vault commit 不包含 `AI協作記憶/` 以外的檔案。
9. 重跑 `bootstrap.sh` 不產生重複 hook。

## 上線注意

- 現有 herdr pane 要重開才會生效。
- 只涵蓋本機，`--machine` 或其他遠端機器不在範圍內。
- 定時環境下 `claude -p` 的登入狀態要在實作時驗證。
