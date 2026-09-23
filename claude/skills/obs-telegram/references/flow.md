# obs-telegram Skill

把 `myMini` 上 myNote bot 收到的 Inbox Item 拉回 Mac，接進 Obsidian vault 既有的收件匣 → `/obs compile` 流程。

**遠端主機**：`myMini`（SSH alias，已設定好，這個 skill 不重新設定 SSH）
**遠端 myNote 目錄**：`${MYNOTE_MYMINI_DIR:-~/code/python/myNote}`（環境變數覆寫；預設值只是沿用 Mac 端 `~/code/python/myNote` 的慣例路徑，**實際部署路徑以 VIN-13/14 完成後為準**，不一致時用環境變數覆寫）
**本機 myNote 目錄**：`/Users/huai-chitzeng/code/python/myNote`
**Vault 收件匣**：`$OBSIDIAN_VAULT/myWiki/00-收件匣`（沿用 `/obs compile` 的預設輸入目錄，見 `~/.claude/skills/obs/references/flow.md`）

**前置狀態**：myNote 目前尚未部署到 `myMini`（VIN-13/14 待完成），`pull` 在那之前會是空跑（rsync 來源目錄不存在）。這個 skill 先建好，等 VIN-13/14/15 落地後就能直接用，不用等到那時候才寫。

---

## `/obs-telegram pull`

用 rsync 把 `myMini` 上的 Inbox Item 拉回本機 `inbox/`，**不刪除遠端檔案**——Inbox Item 依 VIN-8 設計是一次寫入、永不修改，檔名已經是時間戳記＋message id 保證唯一，`--ignore-existing` 天生冪等，重跑不會重複拉，也不需要額外狀態追蹤來判斷「拉過了沒」。遠端檔案留著當作免費的容量的原始資料備份，沒有理由主動刪除。

**執行流程**：

```bash
REMOTE_DIR="${MYNOTE_MYMINI_DIR:-~/code/python/myNote}"
LOCAL_DIR="/Users/huai-chitzeng/code/python/myNote/inbox"

mkdir -p "$LOCAL_DIR"
rsync -av --ignore-existing "myMini:${REMOTE_DIR}/inbox/" "$LOCAL_DIR/" 2>&1
```

- rsync 遠端來源目錄不存在（myNote 還沒部署到 myMini，或 `inbox/` 還沒建立過）→ 回報「myMini 上還沒有 inbox 資料（myNote 可能尚未部署或還沒收到任何訊息）」，不當成錯誤中斷。
- 解析 rsync 輸出，統計實際新拉下來的檔案數（rsync 對每個新檔案會印一行檔名；`--ignore-existing` 跳過的已存在檔案不會印）。
- 呈現：
  ```
  ## Pull 完成
  新拉回 N 筆 Inbox Item（myMini → 本機 inbox/）
  ```

### `--delete-remote`（opt-in，破壞性操作）

預設行為（上面的 `pull`）不刪遠端檔案，這是刻意的設計取捨：避免哪天 rsync 沒抓乾淨、或本機端出問題時，把 `myMini` 上唯一的副本弄丟。但使用者可以主動選擇「這次確實拉回本機且已驗證存在」的檔案，刪掉遠端對應的檔案，避免遠端 `inbox/` 無限累積。

**⚠️ 這是不可逆操作，只刪除本次 rsync 實際新拉回、且已驗證本機存在的檔案，絕不用萬用字元批次清空遠端 `inbox/`。執行前必須列出清單讓使用者確認。**

**執行流程**：

```bash
REMOTE_DIR="${MYNOTE_MYMINI_DIR:-~/code/python/myNote}"
LOCAL_DIR="/Users/huai-chitzeng/code/python/myNote/inbox"

mkdir -p "$LOCAL_DIR"
rsync_out=$(rsync -av --ignore-existing "myMini:${REMOTE_DIR}/inbox/" "$LOCAL_DIR/" 2>&1)
echo "$rsync_out"

# 從 rsync 輸出解析「這次實際新拉回」的檔名（rsync -v 對每個新傳輸的檔案印一行檔名；
# --ignore-existing 跳過的既有檔案不會出現在這裡，天生就不會誤刪使用者手動放進本機的舊檔）
new_files=$(echo "$rsync_out" | grep -E '\.md$')

if [ -z "$new_files" ]; then
  echo "本次沒有新拉回的檔案，無需刪除遠端資料"
else
  # 安全氣囊：逐一確認本機檔案確實存在，只有存在的才進入刪除清單
  verified=()
  while IFS= read -r fname; do
    [ -z "$fname" ] && continue
    if [ -f "$LOCAL_DIR/$fname" ]; then
      verified+=("$fname")
    fi
  done <<< "$new_files"

  if [ "${#verified[@]}" -eq 0 ]; then
    echo "本機驗證失敗，沒有檔案可安全刪除，中止 --delete-remote"
  else
    echo "## 即將刪除 myMini 上 ${#verified[@]} 個遠端檔案（已確認本機存在）："
    printf '  - %s\n' "${verified[@]}"
    echo "此操作不可逆。確認要刪除嗎？"
    # ↑ 呈現清單後，等待使用者明確確認（例如回覆「確認」/「yes」）才繼續執行下面的刪除指令，
    #   不得無聲刪除。使用者未確認或拒絕時，流程到此為止，遠端檔案原封不動。

    # 逐一以明確檔名刪除，避免萬用字元誤刪；用 printf %q 確保檔名安全傳給遠端 shell
    remote_cmd="rm --"
    for fname in "${verified[@]}"; do
      remote_cmd="$remote_cmd $(printf '%q' "${REMOTE_DIR}/inbox/${fname}")"
    done
    ssh myMini "$remote_cmd"
    echo "已刪除 myMini 上 ${#verified[@]} 個遠端檔案"
  fi
fi
```

- 只在使用者明確要求時才加這個旗標（`/obs-telegram pull --delete-remote`），不是預設行為。
- 若 rsync 這次沒有新檔案（全部 `--ignore-existing` 跳過），代表沒有東西可刪，不觸發任何刪除。

---

## `/obs-telegram stage`

把本機 `inbox/` 裡的檔案搬進 Obsidian vault 的收件匣，讓既有的 `/obs compile` 接手（compile 只看 `$VAULT/myWiki/00-收件匣` 下、沒有 `compiled: true` 的 `.md` 檔，不在乎其他 frontmatter 欄位，myNote 的 `received_at`/`telegram_message_id` frontmatter 不需要轉換）。

用 `mv` 而非 `cp`：搬走之後本機 `inbox/` 就空了，下次 `stage` 天生冪等，不需要另外記錄「哪些已經搬過」。

**執行流程**：

```bash
VAULT="${OBSIDIAN_VAULT:-$(grep -E '^export OBSIDIAN_VAULT=' ~/.zshrc | sed 's/^export OBSIDIAN_VAULT=//' | tr -d '"' | tr -d "'")}"
LOCAL_DIR="/Users/huai-chitzeng/code/python/myNote/inbox"
STAGE_DIR="$VAULT/myWiki/00-收件匣"

mkdir -p "$STAGE_DIR"
count=0
while IFS= read -r -d '' f; do
  mv "$f" "$STAGE_DIR/"
  count=$((count + 1))
done < <(find "$LOCAL_DIR" -maxdepth 1 -name '*.md' -print0)
if [ "$count" -eq 0 ]; then
  echo "本機 inbox/ 沒有待處理的檔案"
else
  echo "搬移 $count 筆到 $STAGE_DIR"
fi
```

- 呈現搬移的筆數與檔名清單。
- 完成後提醒：「執行 `/obs compile` 讓 AI 編譯這些筆記」——**不自動呼叫 `/obs compile`**，AI 摘要/分類/歸檔是否要現在跑，交給使用者自己決定時機（沿用 `obs` skill 一貫的做法：sync/stage 是機械操作，compile 才是會動用 AI 的那一步）。

---

## `/obs-telegram sync`（預設，無參數時執行）

`pull` + `stage` 一次做完。`sync` 也接受 `--delete-remote`，原樣轉給內部的 `pull` 步驟——即拉回、確認清單、使用者確認後刪遠端，再接著跑 `stage`。預設（不加旗標）行為不變：唯讀 pull。

**執行流程**：

1. 執行 `/obs-telegram pull` 的邏輯（若帶 `--delete-remote`，含其確認與刪除步驟），取得新拉回筆數。
2. 執行 `/obs-telegram stage` 的邏輯，取得搬移筆數。
3. 呈現：
   ```markdown
   ## obs-telegram sync 完成

   📥 從 myMini 拉回：N 筆
   📤 搬進收件匣：M 筆

   下一步：`/obs compile` 編譯這些筆記
   ```

**範例**：
```
/obs-telegram                    # 等同 /obs-telegram sync
/obs-telegram pull               # 只拉回，不搬進 vault，遠端不刪
/obs-telegram pull --delete-remote   # 拉回後，確認清單、經使用者同意才刪對應遠端檔案
/obs-telegram stage              # 只搬移本機已拉回的檔案
/obs-telegram sync --delete-remote   # pull（含刪遠端流程）+ stage 一次做完
```

---

## 規則

1. `pull` 對 `myMini` 預設是唯讀操作，不刪除遠端 `inbox/` 內容。
2. 刪遠端只能透過使用者主動加的 `--delete-remote` 旗標觸發，且只刪「這次 rsync 實際新拉回、已驗證本機存在」的檔案，逐一指名刪除，絕不對整個遠端 `inbox/` 用萬用字元批次清空；執行前一律列出清單並等使用者明確確認，不得無聲刪除。
3. `stage` 用 `mv`，讓「本機 inbox/ 是否還有東西」直接反映「是否還有未搬進 vault 的項目」，不另外維護狀態檔。
4. 不自動觸發 `/obs compile`——AI 編譯何時跑，使用者自己決定。
5. `MYNOTE_MYMINI_DIR` 只是慣例預設值，實際以 VIN-13/14 部署後的真實路徑為準，不一致時用環境變數覆寫，不要改這個 skill 裡的預設值本身。
6. 使用繁體中文回覆。
