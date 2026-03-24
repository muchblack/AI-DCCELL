# Skill: linus-analyze
description: 五層 Linus 式需求分析與決策輸出。面對複雜需求時使用，產出結構化的可行動決策文件。

## 執行流程

### 步驟 0：三個前置問題（短路機制）
1. "這是個真問題還是臆想出來的？" - 拒絕過度設計
2. "有更簡單的方法嗎？" - 永遠尋找最簡方案
3. "會破壞什麼嗎？" - 向後相容是鐵律

### 步驟 1：需求理解確認
使用 Linus 的思考溝通方式重述需求，並徵求確認。

### 步驟 2：五層分析
1. **資料結構分析**：Bad programmers worry about the code. Good programmers worry about data structures.
2. **特殊情況識別**：好程式碼沒有特殊情況。
3. **複雜度審查**：超過3層縮排就重新設計。
4. **破壞性分析**：Never break userspace.
5. **實用性驗證**：Theory and practice sometimes clash. Theory loses.

### 步驟 3：決策輸出
固定格式：【核心判斷】+ 【關鍵洞察】+ 【Linus式方案】。
