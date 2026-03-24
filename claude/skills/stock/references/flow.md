# Stock Skill

讀取 Obsidian stockDB 股市原始資料，同步 stockDB git 倉庫，執行 AIStock 情緒分析 pipeline。

**Vault 路徑**：`$OBSIDIAN_VAULT/stockDB`
**AIStock 專案**：`~/code/python/AIstock`

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

### `/stock analyze [--prices] [--notify] [--migrate]`

執行 AIStock 情緒分析 pipeline。

**參數**：
- `--prices`（可選）：僅抓取股價與計算技術指標，不做情緒分析
- `--notify`（可選）：強制發送通知（忽略 quiet_hours）
- `--migrate`（可選）：初始化/更新資料庫 schema

**AIStock 路徑**：`~/code/python/AIstock`
**Python venv**：`~/code/python/AIstock/.venv/bin/python`

**執行流程**：

1. **前置檢查**：
   - 確認 venv 存在：`~/code/python/AIstock/.venv/bin/python`
   - 確認 config.yaml 存在
   - 若不存在，回報錯誤並提示設定方式

2. **同步 stockDB**（自動）：
   ```bash
   git -C ~/Obsidian/stockDB pull --rebase 2>/dev/null || true
   ```

3. **執行 pipeline**：
   ```bash
   cd ~/code/python/AIstock && .venv/bin/python main.py 2>&1
   ```
   - `--prices` 模式：
     ```bash
     cd ~/code/python/AIstock && .venv/bin/python main.py --prices 2>&1
     ```
   - `--migrate` 模式：
     ```bash
     cd ~/code/python/AIstock && .venv/bin/python main.py --migrate 2>&1
     ```

4. **呈現結果**：
   - 解析 stdout/stderr 輸出
   - 擷取關鍵資訊：新增文章數、分析結果數、通知發送數
   - 若有錯誤，顯示錯誤訊息並建議修復方式
   - 格式：
     ```
     ## AIStock 分析結果

     📥 抓取：{N} 篇新文章
     🧠 分析：{N} 篇完成（MLX {n1} / MAGI {n2} / Claude {n3}）
     📊 技術指標：{symbols}
     📢 通知：{N} 則已發送

     ### 詳細日誌
     （最後 20 行 log）
     ```

5. **錯誤處理**：
   - venv 不存在 → 提示 `cd ~/code/python/AIstock && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
   - config.yaml 不存在 → 提示 `cp config.example.yaml config.yaml`
   - DB 未初始化 → 自動執行 `--migrate` 後重試
   - MLX 不可用 → 提示檢查 MLX server（`localhost:8090`）
   - Redis 不可用 → 告警但不阻塞（fail-open）

**範例**：
```
/stock analyze            # 完整 pipeline：抓取 → 分析 → 通知
/stock analyze --prices   # 僅抓股價和技術指標
/stock analyze --migrate  # 初始化資料庫
```

---

## 規則

1. 讀取前一律先 git fetch 檢查遠端更新
2. stockDB vault 路徑由環境變數 `$OBSIDIAN_VAULT/stockDB` 決定（`OBSIDIAN_VAULT` 定義於 `~/.zshrc`）
3. read 和 sync 為唯讀操作，analyze 會寫入 AIStock 的 SQLite DB
4. analyze 執行前自動同步 stockDB
5. 使用繁體中文回覆
