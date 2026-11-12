# AI-DCCELL

> **多 AI 協作工作流的自進化基礎設施** — 會自我再生、自我增殖、自我進化的 Claude Code 體系。

以《機動武鬥傳G 鋼彈》惡魔鋼彈 **DG 細胞**的三大理論為隱喻框架，把 Claude Code 多 AI 協作工作流，打造成一套容錯可恢復、改進可擴散、行為可演化的工程基礎設施。

---

## 30 秒上手

```bash
git clone <repo-url> AI-DCCELL
cd AI-DCCELL
chmod +x bootstrap.sh
./bootstrap.sh
```

`bootstrap.sh` 會依序完成（共 4 個階段）：

1. **[1/4]** 建立 `~/.claude/` 下的 symlink（`CLAUDE.md`、`agents/`、`skills/`）
2. **[1b/4]** 部署 Codex 設定（`~/.codex/AGENTS.md`、`~/.codex/skills/`）
3. **[1c/4]** 部署 Gemini 設定（`~/.gemini/GEMINI.md`）
4. **[1d/4]** 初始化外部 skill submodule，並依 `shared-skills.txt` 把通用 skill 掛給 Codex 與 agy（見下方「與 Codex／agy 共用」）
5. **[1e/4]** 把 `lessons` 分支掛成 `~/.claude/herdr-lessons/`（見下方「herdr-dev 跨專案踩坑紀錄」）
6. **[1f/4]** 建立 SerpApi 金鑰檔 `~/.config/serpapi/.env`（權限 600），供 `topic-pulse` 的搜尋熱度（Google Trends）使用。檔案已存在就只重設權限；不存在時取環境變數 `SERPAPI_API_KEY`，沒有就在終端機詢問（不回顯，可留空跳過）
7. **[2/4]** 設定 scripts 執行權限
8. **[3/4]** 初始化 memory 目錄（telemetry）
9. **[4/4]** 執行 health check，驗證 Gemini / Codex / provider 連線

### 手動設定（bootstrap 不處理）

**SerpApi 金鑰載入**：bootstrap 只建金鑰檔，不改 `~/.bashrc`。要讓 shell 讀到金鑰，自己在 `~/.bashrc` 加一行（沒加的話 bootstrap 會提醒）：

```bash
[ -f ~/.config/serpapi/.env ] && set -a && . ~/.config/serpapi/.env && set +a
```

沒有金鑰時 `topic-pulse` 照常產出報告，只是搜尋熱度那節會標成 unavailable。

`~/.claude/settings.json` 不在本 repo 管理，新機器要自己補：

- **`"autoCompactWindow": 400000`**：context 超過 40 萬 token 就自動 compact。依 2026-10 近 30 天的 transcript 模擬，可以少讀約 22% 的 context token；受影響的只有少數超長 session，但它們每一輪都要重讀整段對話，所以影響很大。`/autocompact` 會存到 `modelSettings.<model>`，優先於這個全域值。

### herdr-dev 跨專案踩坑紀錄（`lessons` 分支）

herdr-dev 每張票結束時，會把跟工具、框架有關的坑去識別化後寫進 `~/.claude/herdr-lessons/lessons.md`；下一張票開始時，再依技術棧挑出相關的條目放進 brief，讓 worker 和 reviewer 事先知道。專案專屬的坑則寫在各專案的 `.herdr/lessons.md`。

- 這份紀錄放在獨立的 `lessons` 分支，不在 `company` 或 `main` 裡，所以兩條分支累積的經驗是同一份，不用 cherry-pick。
- `~/.claude/herdr-lessons/` 是這個 repo 的 git worktree。新機器 pull 之後跑一次 `./bootstrap.sh` 就會建好（step 1e，可重複執行）；沒跑也沒關係，herdr-dev 第一次用到時會自己建立。
- 每次寫入都會 commit 到 `lessons` 分支，你確認新增的條目後才 push。`.gitattributes` 設了 `merge=union`，兩台機器同時新增條目也不會衝突。
- Codex 也接上了（`codex/AGENTS.md`「Shared Pitfall Log」）：當 herdr worker 時不寫檔，把坑填在 report 的 `pitfalls` 欄位交給 main 整理；直接用 codex 開發時，開工前讀相關條目，解掉可重複發生的坑後先給你確認，再寫入並 commit（不 push）。
- 規則細節（去識別化、格式、上限 60 行）見 `claude/skills/herdr-dev/references/flow.md` Phase 5 step 6。

### 跨 AI 共用記憶

記憶存於 `${OBSIDIAN_VAULT:-/mnt/d/obsidian}/myWiki/20-領域/AI協作記憶/`，vault 路徑不是目錄時退回 `/mnt/d/obsidian`。檔案分成 `使用習慣.md`（含 `## 核心`）、`技術決策.md`、`工具環境.md`、`踩坑/<stack>.md`。容量不限；每次 session 僅注入最多 3072 UTF-8 bytes，內容標為參考資料，搜尋行固定保留。vault 不可用時不阻擋啟動。

`bootstrap.sh` 的 step 1g 會以 `install-mem.py` 合併 Claude、Codex、agy 的 SessionStart hook，保留既有設定，並安裝 systemd user units；重跑不會重複新增。無效 JSON 原檔不動，回報錯誤並回傳非零。安裝器不建立 vault、不啟動 timer，也不依賴 `.bashrc`。可用 `python3 claude/skills/scripts/install-mem.py --home <測試目錄>` 在隔離目錄檢查。

安裝器依平台選排程：Linux 裝 systemd units，macOS 裝 `~/Library/LaunchAgents/local.mem-digest.plist`，可用 `--scheduler` 覆寫。macOS 的 plist 寫入安裝當下的 Python 絕對路徑，Python 換版後要重跑安裝器。安裝時的 `OBSIDIAN_VAULT`（或 `--vault`）會以 `MEM_FALLBACK_VAULT` 寫進 hook 指令，供 GUI 啟動等讀不到 shell 設定的情境使用；換 vault 後重跑即可，舊 hook 會被取代。

安裝後手動執行：

```bash
# Linux
systemctl --user daemon-reload
systemctl --user enable --now mem-digest.timer
loginctl enable-linger

# macOS
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.mem-digest.plist
```

macOS 錯過排程時，睡眠醒來會補跑，關機期間的不補。

Codex 第一次需信任新增 hook；現有 Claude、Codex、agy panes 要重開。agy 的全域 hook 載入仍需實機確認，`GEMINI.md` 設有未注入時開場執行一次的備援。主控合併後另做三個 CLI 的標記注入、Known pitfalls 搜尋、`systemd-analyze verify` 與排程環境 `claude -p` 登入驗證。

平日 18:00 以 systemd timer 彙整三個 CLI 的使用者輸入，錯過時下次啟動補跑（`Persistent=true`；需要登出後仍排程可啟用 linger）。service 的 PATH 包含 `~/.local/bin`、`~/.npm-global/bin`、`/usr/local/bin` 與系統目錄；CLI 裝在其他位置時自行用 systemd override 設定 PATH。只讀 prompt history 和 Codex rollout 的 session metadata，不分析完整對話；排除 brief、貼上內容與彙整器自己的 prompt。使用 Sonnet 產生去識別化草稿，**永遠不直接寫 vault**。請先確認這些輸入適合送至已登入的 Claude。

草稿位於 `~/.local/share/mem-review/`（目錄 700、檔案 600），同日加數字後綴，不覆蓋。成功才原子推進游標；失敗保留游標。沒有輸入或沒有項目時不產生草稿、不通知。通知只帶草稿位置和項目數。單次內容列為「觀察」，重複或明確要求長期遵守的內容才列為「候選」。

```bash
bash ~/.claude/skills/scripts/mem-recall.sh --search 關鍵字
python3 ~/.claude/skills/scripts/mem-digest.py --dry-run
```

`--dry-run` 只列出過濾後的資料，不寫檔也不呼叫模型。測試可用 `OBSIDIAN_VAULT`、`MEM_FALLBACK_VAULT`、`MEM_DIGEST_CLAUDE_BIN`、`MEM_DIGEST_HERDR_BIN` 指定隔離來源與假執行檔。

使用 `/mem <內容>` 去識別化、查重並逐筆確認後寫入；`/mem review` 逐條審核草稿，處理完移至 `reviewed/`。核心段落會合併或移至非核心段落以維持注入預算。「觀察」不進核心。herdr worker 不寫入，交 main 處理。vault 只做限定記憶路徑的提交，不包含其他已 stage 的筆記，永遠不 push。`mem` 透過 `shared-skills.txt` 共用給 Codex 與 agy，與既有 telemetry 的 `memory` 不同。

### 外部 Skill（git submodule）

下列外部 skill 以 submodule 鎖定版本（放在 `vendor/`，再以 symlink 掛到 `claude/skills/`）：

| Skill | 上游 | submodule |
|---|---|---|
| `security-audit` | cloudflare/security-audit-skill | `vendor/security-audit-skill` |
| `open-seo-advisor` | mars-tw/open-seo-advisor-skill | `claude/skills/open-seo-advisor` |
| `ui-ux-pro-max`、`brand`、`design`、`design-system`、`ui-styling` | nextlevelbuilder/ui-ux-pro-max-skill | `vendor/ui-ux-pro-max-skill` |
| `find-skills` | vercel-labs/skills | `vendor/vercel-skills` |
| `react-best-practices` | vercel-labs/agent-skills | `vendor/vercel-agent-skills` |

上游套組裡的 `banner-design`、`slides` 沒有掛出來：兩者的 reference 跟 `design` 內建的版本逐字相同，`slides` 的生成腳本也在 `design-system`，掛了只會重複觸發。

`react-best-practices` 的 `rules/`、`AGENTS.md` 是 symlink 指向上游；`SKILL.md` 是上游複製後把 `name` 從 `vercel-react-best-practices` 改回 `react-best-practices`（CLAUDE.md 與 agent 都用這個名字引用），`update-vendor.sh react-best-practices` 會自動重新產生。

`bootstrap.sh` 會自動初始化這些 submodule。已部署的機器 pull 之後補跑：

```bash
git pull && git submodule update --init
```

更新上游版本（會先顯示 diff、確認後跑檢查再 commit，不會自動 push）：

```bash
scripts/update-vendor.sh                  # 列出目前版本
scripts/update-vendor.sh security-audit
```

### 與 Codex／agy 共用

`shared-skills.txt` 列出要共用的 skill，來源一律是 `claude/skills/<name>`，由 `scripts/sync-shared-skills.sh` 以 symlink 掛到：

| CLI | 載入目錄 |
|---|---|
| Codex | `~/.agents/skills/` |
| Antigravity（agy） | `~/.gemini/config/skills/`（agy 不讀全域 `~/.agents/skills`） |

改完清單後執行 `scripts/sync-shared-skills.sh`，再重開 Codex／agy 的 session 才會生效。腳本只會動指向本 repo 的 symlink；CLI 自己的實體目錄（例如 `~/.codex/skills/linus-review`）會跳過，清單上用 `!codex`／`!agy` 標記不掛給哪一邊。主控派工類（herdr-dev、dispatch、ask）刻意不共用，以免 worker 自己再派工。

### 本地修補

以下外部 skill 直接複製進 `claude/skills/`（非 submodule），並加了本地修改。重新同步上游時會被覆蓋，同步後要補回：

| Skill | 上游 | 本地修改 | 日期 |
|---|---|---|---|
| `grill-with-docs` | mattpocock/skills | `SKILL.md` 第一行之後全部：① 程式碼／文件事實標 `EXTRACTED: <path:line>` 或 `INFERRED: <why>`，只有 EXTRACTED 能寫進 CONTEXT.md／ADR（與 herdr-dev verdict 的 CRITICAL 須 EXTRACTED 成對）② 開場 recon＋假設清單，只問清單沒解決的 ③ 收尾交接摘要給 `/to-spec` | 2026-10-12 |
| `to-tickets` | mattpocock/skills | `SKILL.md`：每張票給嚴重度（Critical/High/Medium/Low，來源已有分級就沿用並依序對應），直接寫進 Linear `priority`（1 Urgent／2 High／3 Medium／4 Low），不另建或套用嚴重度 label；label 只留 `ready-for-agent` | 2026-10-23 |

找回原文：`git log -p -- claude/skills/<skill>`。覆蓋上游前先 `git diff` 確認本地修改還在。

`ui-ux-pro-max` 是 vendor symlink，skill 本體不能改，注意事項記在這裡：

- `SKILL.md` 用的 `${CLAUDE_PLUGIN_ROOT}` 路徑在本機（symlink 安裝）會失效，一律用 `python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py`。
- 不要加 `-I`：腳本需從自身目錄 import `core.py`。
- `--design-system` 的版型偏行銷頁，非 landing page 的專案只參考配色與字體。

部署後可隨時用健康檢查確認 provider 狀態：

```bash
claude/skills/scripts/health-check.sh
```

---

## DG 細胞理論：神話與工程的對照

這套體系的核心是把鋼彈設定中的三大「生存本能」，落地成具體的腳本與工作流。**不是 vibe，是可執行的檔案。**

| DG 細胞理論 | 原始設定 | 工程實作 |
|------------|---------|---------|
| **自我再生** Regeneration | 核心未毀即可瞬間復原 | 健康檢查、指數退避重試、超時殺進程、狀態快照與修復 |
| **自我增殖** Multiplication | 感染後幾何級數擴散 | Skill 骨架生成、評分 rubric 單一來源 |
| **自我進化** Evolution | 依環境/對手自動進化 | 呼叫遙測、效能報告 |

### 自我再生（Regeneration）— 容錯與自動恢復

| 腳本 | 功能 |
|------|------|
| `scripts/health-check.sh` | Provider 健康檢查（秒級回傳 JSON 狀態） |
| `scripts/retry.sh` | 指數退避重試 + jitter |
| `scripts/watchdog.sh` | 超時殺進程（exit 124） |

搭配 `/herdr-dev --resume` 與 provider 降級鏈（→ Claude），中斷可從斷點續接。

### 自我增殖（Multiplication）— 知識共享與擴散

| 項目 | 功能 |
|------|------|
| `scripts/scaffold.sh` | Skill 骨架生成器（simple / intermediate / complex） |
| `linus-review/rubric.md` | 三級評分（🟢🟡🔴）的唯一定義來源 |

### 自我進化（Evolution）— 效能追蹤與智慧路由

| 項目 | 功能 |
|------|------|
| `scripts/telemetry.sh` | Skill 呼叫記錄（provider、耗時、結果、是否降級） |
| `scripts/telemetry-report.sh` | 效能報告（成功率、耗時、降級頻率） |

---

## 角色分工：herdr-dev 與 Human-in-the-Loop

體系雖高度自動化，**需求、範圍與最終決定都在使用者手上**。開發預設走 `/herdr-dev`，各 AI 在 herdr pane 裡分工：

| 角色 | 預設 Provider | 職責 |
|------|----------|------|
| main | Claude Code（本 session） | 確認需求、寫 brief、仲裁審查意見、merge、`/linus-review` 自審、回報 Linear |
| worker | codex（`--worker` 可換） | 在獨立 worktree 依 TDD（RED → GREEN）開發並 commit |
| reviewer | agy（`--reviewer` 可換） | 開工前審 brief；merge 後審品質、規格、TDD 證據、資安、效能 |

**審查關卡**：brief 先給 reviewer 看過才開工；merge 後 main 先用 `/linus-review` 自審，有 CRITICAL 就退回 worker，沒有才送 reviewer。reviewer 判 FIX 時，worker 先補失敗的回歸測試再修，最多 2 輪。細節見 `claude/skills/herdr-dev/`。

---

## 目錄結構

```
AI-DCCELL/
├── bootstrap.sh           # 一鍵部署（Claude + Codex + Gemini）
├── claude/
│   ├── CLAUDE.md          # 全域 Claude 指令
│   ├── agents/            # 空（.gitkeep）；角色知識已併入 herdr-dev／herdr-mkt
│   └── skills/            # 52 個 skill 定義
│       ├── scripts/       # 14 個共用基礎腳本（DG Cell Core）
│       ├── memory/        # 學習記憶（telemetry）
│       └── ...            # herdr-dev, herdr-mkt, linus-review, linus-analyze,
│                          #   topic-pulse, 命理三件套 等
├── codex/
│   ├── AGENTS.md          # Codex 角色與 Rubric 定義
│   └── skills/            # 12 個 Codex 端 skill
├── .gemini/
│   └── GEMINI.md          # agy 角色定義（skill 改由 shared-skills.txt 共用）
├── docs/                  # DG 細胞理論藍圖 + 實作紀錄
└── project-template/      # 新專案範本（CLAUDE.md）
```

---

## 體系數據

- **Skills**：52 個（涵蓋開發工作流、程式碼審查、輿情分析、命理三件套、影像生成、求職、股市分析等）
- **基礎腳本**：14 個（`claude/skills/scripts/`）
- **AI Providers**：Claude、Codex、agy（Antigravity）、opencode、droid
- **通訊協定**：herdr pane 派工（brief／report／verdict 檔案交接）、Linus 式審查

---

## 環境需求

- macOS 或 Linux（含 WSL2）
- Python 3.10+
- Claude Code CLI

---

## 相關連結

- [DG 細胞理論藍圖](docs/DG%20細胞理論%20—%20AI%20工作流自進化升級藍圖.md) — 設計文件
- [DG 細胞理論實作紀錄](docs/DG%20細胞理論實作紀錄.md) — 三大模組開發過程
