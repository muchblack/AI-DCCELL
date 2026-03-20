# Stock Skill

讀取 Obsidian stockDB 股市原始資料，同步 stockDB git 倉庫。

**Vault 路徑**：`$OBSIDIAN_VAULT/stockDB`

---

## 子命令

### `/stock read [date] [feed]`

讀取指定日期的原始資料。

**參數**：
- `date`（可選）：日期，格式 `YYYY-MM-DD` 或 `MM-DD`。預設今天。
- `feed`（可選）：指定 feed 名稱（如 `臺股動態`、`國際財經`）。預設全部。

**執行流程**：

1. **Git fetch**：先確認遠端是否有更新
   ```bash
   git -C $OBSIDIAN_VAULT/stockDB fetch origin 2>/dev/null
   LOCAL=$(git -C $OBSIDIAN_VAULT/stockDB rev-parse HEAD 2>/dev/null)
   REMOTE=$(git -C $OBSIDIAN_VAULT/stockDB rev-parse origin/main 2>/dev/null)
   ```
   - 若 `LOCAL != REMOTE`：執行 `git -C $OBSIDIAN_VAULT/stockDB pull --rebase` 先同步
   - 若 stockDB 無 git：跳過此步驟

2. **解析日期**：
   - 無參數 → 今天 (`currentDate`)
   - `MM-DD` → 當年 `{currentYear}/{MM-DD}`
   - `YYYY-MM-DD` → `{YYYY}/{MM-DD}`

3. **定位檔案**：
   ```
   $OBSIDIAN_VAULT/stockDB/原始資料/{feed}/{YYYY}/{MM-DD}.md
   ```
   - 若指定 feed → 讀取該 feed 檔案
   - 若未指定 feed → 用 Glob 搜尋 `原始資料/*/{YYYY}/{MM-DD}.md`，讀取全部

4. **讀取並呈現**：
   - 用 Read 工具讀取每個匹配的 .md 檔
   - 呈現格式：
     ```
     ## {feed_name} — {date}
     [文章數量] 篇新聞

     ### 文章標題一
     摘要前 100 字...

     ### 文章標題二
     ...
     ```
   - 若檔案不存在：回報「{date} 無 {feed} 資料」

5. **統計摘要**（自動附加）：
   - 各 feed 文章數量
   - 總計新聞數

**範例**：
```
/stock read              # 讀取今天所有 feed
/stock read 03-20        # 讀取 03-20 所有 feed
/stock read 2026-03-20 臺股動態  # 讀取指定日期指定 feed
```

---

### `/stock sync`

同步 stockDB git 倉庫。直接委派給 `/obs sync`。

**執行流程**：

呼叫 `/obs sync --vault $OBSIDIAN_VAULT/stockDB`

**範例**：
```
/stock sync
```

---

## 規則

1. 讀取前一律先 git fetch 檢查遠端更新
2. stockDB vault 路徑由環境變數 `$OBSIDIAN_VAULT/stockDB` 決定（`OBSIDIAN_VAULT` 定義於 `~/.zshrc`）
3. 此 skill 為唯讀操作（read）+ git 同步（sync），不做寫入
4. 使用繁體中文回覆
