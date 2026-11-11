---
name: shopee-calc
description: 蝦皮雙軌試算與帳本判讀。使用者要求蝦皮利潤、退貨期望值、出清價、廣告上限、準備金、在途額度或 Day 14／42／56 決策時使用。只讀自訂 CSV，不解析賣家中心匯出檔，不操作賣場。
---

# 蝦皮試算與判讀

用 Python 3 標準函式庫指令完成計算，依 JSON 說明結果。不要自行替換公式或放寬風控門檻。

**never write or modify any ledger file**：絕不寫入、修改或自動補全任何帳本檔。資料錯誤時請使用者自行修正；不要自動調價、投放廣告、採購或上下架。

## 呼叫方式

以下從共用庫根目錄執行；在其他目錄請將腳本改為實際絕對路徑。

事前試算，只需要參數：

```bash
python3 claude/skills/shopee-calc/scripts/shopee_calc.py --params params.json --as-of 2026-11-11
```

事後判讀，三份 CSV 必須一起提供（沒有資料也要保留標頭）：

```bash
python3 claude/skills/shopee-calc/scripts/shopee_calc.py --params params.json --orders orders.csv --cashflow cashflow.csv --daily daily.csv --as-of 2026-11-11
```

`--rates rates.json` 可指定費率，預設使用隨附的 `scripts/rates.json`。`--as-of` 預設本機今日，是唯一時間輸入。重現報告時務必固定它；所有日期均不得晚於判讀日。費率生效日不得晚於判讀日，查核日可以晚於歷史判讀日。

stdout 僅有一個 JSON；金額為新台幣、小數二位，比例使用小數（0.1＝10%）。結束碼 0＝成功，2＝輸入錯誤（仍輸出 JSON，但三個計算區段均為 null），1＝命令列用法錯誤。參數錯誤在 stderr。

## 說明報告

先看 `errors`，有錯時只列出檔案、資料列與欄位，不給財務判斷。列號 1 是第一筆資料，0 是標頭，null 是檔案或參數層級。

以繁體中文依序呈現：

1. **結論與命中規則**：`global_state`（NORMAL 正常、PAUSED 暫停、STOP_ACCEPTING 停止接單、EXIT 退場），接著依 `actions` 原順序說明 scope、rule、instruction 與 evidence。全案動作優先，單品動作也必須保留。
2. **關鍵數字**：各 SKU 的保留單利潤、退貨加權期望利潤、廣告上限及出清級距；事後再列各軌現金、已付支出、未付義務、曝險、實際虧損、準備金餘額／缺口、B 在途占用／剩餘。
3. **警告**：`meta.warnings` 的費率過期、`errors`、`maturity` 與各項 `*_status` 的 PENDING。null 不是 0%，不得描述成沒有退貨或沒有風險。

事前試算的 `ledger_state` 與 `verdict` 為 null，不要自行補出決策。各 SKU 的 `flags` 必須原意保留：「不碰」、「不准上架」、「不可依賴付費廣告」。自動廣告沿用 A 期望利潤／B 期望貢獻 50% 的 CPA 上限。

## 參數 JSON

從 [templates/params.json](templates/params.json) 建立使用者自己的參數檔。所有金額／數量必須有限且非負，缺少必要參數會回報錯誤；沒有暗藏的匯率、CR 或成本預設。

| 欄位 | 意義 |
| --- | --- |
| `plan` | 1 或 2，實際報名方案 |
| `category` | 費率鍵的類目後綴，例如 `default` 對應 `category_default` |
| `return_rate`, `per_return_loss` | 事前預估退貨率、每次退貨損失；事後績效不套預估退貨率 |
| `fx`, `wholesale_discount` | 日圓換台幣匯率、代批折扣（0–1） |
| `auto_ad` | JSON 布林值；只表達廣告模式，不放寬上限 |
| `tracks` | 以 A、B 為鍵的軌道設定；只放實際經營的軌道 |
| `skus` | SKU 設定陣列，SKU ID 須唯一 |
| `inventory` | 現有庫存及不可撤銷採購的回收估算陣列；無庫存填 `[]` |

每軌 `tracks.A`／`tracks.B`：

| 欄位 | 意義 |
| --- | --- |
| `budget` | 開始經營的現金預算，含準備金 |
| `reserve_requirement` | 準備金規定額度，同時作為期初準備金餘額 |
| `in_transit_cap` | B 必填，在途成本上限 |
| `current_round` | 本次判讀輪次，字串，例如 `"1"` |
| `rounds` | 輪次字串→Day 1 日期的物件；各輪接單期固定 14 天，不得重疊 |

每個 `skus[]`：

| 欄位 | 意義 |
| --- | --- |
| `sku`, `track` | SKU ID、A 或 B；須對應已設定軌道 |
| `price`, `shipping` | 每單商品售價、金流費基礎中的運費；運費不是商品營收 |
| `promotion`, `gift`, `packaging`, `preorder_fee` | 每單促銷折讓、贈品、包材、預購固定費用，無則填 0 |
| `landed_cost` | A 必填，每單到岸成本，不含包材 |
| `conversion_rate` | A 必填，轉換率（0–1），用於損益兩平 CPC |
| `tuning_rounds` | 已完成且未達標的調優輪數，非負整數，由使用者維護；等待成熟不能增加它 |
| `items` | B 必填，訂單各品項陣列：`retail_jpy` 日本零售價、`domestic_shipping_jpy` 日本境內運費分攤、`international_shipping` 台幣國際運費分攤、`import_tax` 使用者提供的台幣稅費、`units` 件數 |

B 單件成本＝（日圓零售價×折扣＋日本運費）×匯率×（1＋刷卡費率）＋國際運費＋使用者提供稅費。計算保留 Decimal 精度，輸出才四捨五入；出清候選價向上進位至分，僅保留落在自身級距的候選。

每個 `inventory[]` 包含 `sku`, `track`, `units`, `book_cost_per_unit`, `est_net_recovery_per_unit`, `irrevocable`（JSON 布林值）。`units` 包含現貨與不可撤銷採購，預估淨回收額須已扣除出清費用。不可回收損失＝max(0, 件數×〔帳面單價−預估淨回收單價〕)。

若庫存與訂單或採購流水指向同一批貨，另填相同 `cost_id`，以免不可撤銷的未付義務重算。未填 `cost_id` 的不可撤銷庫存視為獨立、尚未付款的承諾；已付款者應提供 ID 並在流水記採購支出。已出售／報廢貨物不得繼續留在 inventory。

## CSV 格式

UTF-8，可有 BOM，第一列標頭必填。使用 [templates/orders.csv](templates/orders.csv)、[templates/cashflow.csv](templates/cashflow.csv)、[templates/daily.csv](templates/daily.csv) 的標頭；日期 YYYY-MM-DD，布林值只能是小寫 `true`／`false`。金額填非負數字，不含逗號、貨幣符號或百分號；不適用的文字欄留白，無金額填 0。

### 訂單明細 orders.csv

| 欄位 | 意義 |
| --- | --- |
| `order_id` | 唯一訂單 ID |
| `track`, `round`, `sku` | 軌道、接單輪次、SKU；接單日須位於該輪 Day 1–14 |
| `is_stranger` | 是否陌生人；只有 true 計入績效與品質判讀，親友單仍影響現金及在途 |
| `accepted_on` | 接單日 |
| `status` | `accepted`／`purchased`／`shipped`／`kept`／`returned`／`cancelled` |
| `completed_on` | 買家完成日，未完成留白；鑑賞期以此起算七天 |
| `bank_settled_on` | 銀行入帳日，尚未入帳留白 |
| `refund_settled_on` | 取消／退貨相關款項全部結清日，尚未結清留白 |
| `price`, `shipping` | 實際商品售價、金流計費運費；每單固定成本沿用 SKU 設定 |
| `cost_id` | 貨物成本 ID；退貨再售必須沿用。同 ID 代表同一份成本，不可用於不同批貨 |
| `estimated_cost` | 未採購時預估台幣成本 |
| `actual_cost` | 採購實際台幣成本；已採購必填，未採購可留白 |
| `return_loss` | 實際退貨損失，無則 0；不含已另列的出清損失 |
| `defect` | 已確認瑕疵；B 抵台驗貨的瑕疵可立即標 true |
| `purchased` | 是否已採購，用於在途狀態與供應商採購嘗試分母 |
| `disposed` | 是否已出清／報廢並轉出在途；相應損失須填 realized_loss |
| `realized_loss` | 已實現的出清差額／報廢損失，無則 0，勿重複填入 return_loss 或 loss 流水 |
| `cancel_reason` | 取消單必填 `buyer`／`supplier`／`other`，其他訂單留白 |

成熟＝保留單已入帳且完成滿七天，或取消／退貨相關款項已結清。退貨率只取同批成熟陌生人訂單；B 尚未成熟但已確認的抵台瑕疵另加入瑕疵觀察分母與分子。已結清取消單也在成熟分母，完成訂單數僅計成熟保留單。

同一成本 ID 的轉售以接單日、訂單 ID 排序後最後一筆為目前狀態；同日轉售請使用可排序且遞增的訂單 ID。保留單銀行入帳才釋放額度；退貨即使曾經入帳仍占用，未採購取消則釋放。

### 現金流水 cashflow.csv

| 欄位 | 意義 |
| --- | --- |
| `date`, `track` | 交易日、A 或 B，軌道必填 |
| `sku` | 單品支出所屬 SKU；全案支出可留白 |
| `category` | `procurement` 採購、`ad` 廣告、`sample` 樣品、`packaging` 包材、`refund` 退款／退貨運費、`bank_receipt` 銀行撥款、`reserve_topup` 明確補回準備金、`loss` 其他已實現損失、`other` 其他 |
| `direction` | `in` 收入、`out` 支出 |
| `estimated_twd`, `actual_twd` | 預估台幣、實際入帳台幣；actual 留白才用預估，0 仍是有效實際金額 |
| `uses_reserve` | 是否動用準備金；只容許退款／退貨運費與瑕疵損失（refund／loss）的支出 |
| `cost_id`, `order_id` | 關聯貨物、訂單 ID；無關聯可留白；採購付款應有 cost_id 才能抵掉未付義務 |

刷卡當日就列 `out`，繳卡費時不要再列一次。每筆銀行回款須另列 `in`，不能只填訂單入帳日。可用現金＝預算＋流水收入−流水支出。曝險＝全部已付支出＋未付成本義務，已付在途成本不再加一次。曝險與實際虧損分開管控。

實際虧損＝陌生人訂單的 return_loss／realized_loss＋sample／ad／loss 流水支出＋庫存無法回收額。同一筆損失只能放一處；流水 refund 表示資金移動，不能再把全部退款售價當成損失。每日廣告額用於績效，現金流水 ad 用於現金與已實現虧損，兩份應一致。

準備金＝規定額度−標記 uses_reserve 的支出＋reserve_topup。撥款不會自動補準備金。若從現有可用現金內部撥補準備金，reserve_topup 流入搭配同額 other 流出，避免虛增現金；外部注資則只記流入。

### 每日帳本 daily.csv

| 欄位 | 意義 |
| --- | --- |
| `date`, `track`, `round`, `sku` | 日期、軌道、所屬廣告／觀察輪次、SKU；可在接單期結束後繼續記錄 |
| `change` | 當日改動記錄 |
| `impressions`, `clicks`, `ctr` | 曝光、點擊（非負整數），CTR 小數 0–1 |
| `ad_spend` | 當日台幣廣告支出 |
| `orders`, `received_amount`, `in_transit` | 當日訂單數、實收完成金額、在途成本餘額（供人工對照，不取代訂單／流水計算） |
| `notes` | 備註與異常 |

## 決策與費率邊界

A 從 Day 14 評估六列，停損與品質隨時適用；單品損失 2,000、全案損失 6,000 為紅線。完成陌生人單不足 15 筆記 PENDING，不能驗證成功；第 5、6 列仍可列出轉換／樣本不足原因。兩輪未達標的數字完全依使用者維護的 tuning_rounds，不因等待自動增加。

B Day 42 僅停損，Day 56 才評估擴大／再測；未成熟時阻擋績效決策。全案撤離與 SKU 品質停損同時列出。準備金不足、曝險超額、B 在途滿額都會暫停新承諾；B 準備金低於一半停止接單，Day 56 仍不足一半則退場。跨軌採 EXIT > STOP_ACCEPTING > PAUSED > NORMAL，非 NORMAL 不給擴大／再測。暫停前已接單才能履約，新單不能藉「既有訂單」例外繞過暫停。

費率每項含 `value`, `effective_from`, `checked_on`。`meta.rates_version` 是費率內容 SHA-256，`meta.rates` 保留所用數值與日期；查核距判讀日超過 30 天時，每項各給一則警告。隨附數字依 2026-11-11 任務規格建檔，**不是即時官方查核**；成交費只有 `default` 的 6% 示意，使用前應換成自己的類目費率。方案 2 以 boundary 分為低額百分比／高額固定額，不是 NT$60 上限。

開賣前仍須自行向賣家中心確認：各物流是否可關貨到付款、廣告最低日預算、帳號可用廣告模式及現行費率。此工具不查平台、不算稅務／海關稅額、不解析平台匯出、不提供訂單或廣告自動化。

測試：

```bash
python3 -m unittest discover -s claude/skills/shopee-calc/tests -t claude/skills/shopee-calc
```
