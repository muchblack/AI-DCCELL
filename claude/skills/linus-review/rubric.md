# Linus Taste Review Rubric

> Single source of truth — 所有 skill 的 3-tier 評分標準引用此文件。

## Taste Score（三層）

```
🟢 Good taste: 正確的資料結構、無特殊案例、簡潔有力
🟡 Passable:   能用但有改進空間、存在可消除的複雜度
🔴 Garbage:    結構性問題、錯誤的資料模型、過度複雜
```

## 評分權重（由高至低）

1. **資料結構正確性**（最高權重）
2. **特殊案例數量** — 越少越好，能消除最佳
3. **縮排深度** — 超過 3 層扣分
4. **函式長度與單一職責**
5. **命名清晰度**

## Fatal Issues 定義

以下為 fatal，不可與 style feedback 混淆：

- 破壞向後相容（Breaking userspace）
- 根本性資料結構錯誤
- 安全漏洞（SQL injection, XSS, 敏感資料洩露, trust boundary 違規）
- Race condition / 並發 bug
- 資料遺失或損壞風險
- 會在 production 造成實際損害的缺陷

無 fatal issues 時明確標示：`No fatal issues found.`

## Improvements 規則

- 每項改進必須**具體且可行動**
- 最多 3 項，按影響力排序
- 參考格式：
  - "消除這個特殊案例"
  - "這 N 行可以變成 M 行"
  - "資料結構有誤，應改為..."

## Informational（非 fatal，可標記）

- Magic numbers / 未命名常數
- Dead code / 不可達分支
- 變更程式碼缺少測試覆蓋
- 命名不一致

## 決策行動

| 評分 | 行動 |
|------|------|
| 🟢 Good taste | 建議直接採用 |
| 🟡 Passable | Claude 直接修正（不回送原 provider） |
| 🔴 Garbage | 回送原 provider 附帶 review 意見重寫（最多 2 輪，仍 🔴 則 Claude 接手） |
