# Workflow Complexity Classifier

> 判斷任務複雜度，供 `/dev` 等 skill 決定是否裁剪流程。

## 複雜度等級

| 等級 | 定義 | 可跳過的階段 |
|------|------|-------------|
| **simple** | 單檔案、少量行數、明確範圍 | Phase 3 (plan cross-review) + Phase 7 (code cross-review) |
| **medium** | 多檔案但範圍清晰、無架構變動 | Phase 3 (plan cross-review) |
| **complex** | 跨模組、架構變動、新功能、高風險 | 不跳過任何階段 |

## 判定規則

Claude 根據以下信號判斷複雜度（任一 complex 信號 → complex）：

### Complex 信號（任一觸發 → complex）
- 需求涉及 **3+ 檔案**
- 涉及 **架構變動**（新模組、資料結構重設計、API 介面變更）
- 涉及 **資料庫 migration**
- 涉及 **安全性**（認證、授權、加密）
- 需求描述超過 **3 句話** 且涉及多個獨立概念
- 使用者明確要求正式 review

### Simple 信號（全部滿足 → simple）
- 單一檔案修改
- 修改範圍 < 50 行
- Bug fix 或 typo 修正
- 純 config/env 變更
- 文件更新

### Medium（其餘情況）
- 不符合 simple 也不符合 complex

## 使用方式

Claude 在 `/dev` Phase 1 結束後，根據上述規則判斷複雜度，並在 Phase 1 output 中標註：

```
[COMPLEXITY: simple|medium|complex]
Reason: <one-line justification>
```

## 裁剪行為

| Phase | simple | medium | complex |
|-------|--------|--------|---------|
| 1 MLX Plan | ✅ 執行 | ✅ 執行 | ✅ 執行 |
| 2 Primary Review (plan) | ✅ 執行 | ✅ 執行 | ✅ 執行 |
| 3 Final Review (plan cross-review) | ⏭ 跳過 | ⏭ 跳過 | ✅ 執行 |
| 4 Learning | ✅ 執行 | ✅ 執行 | ✅ 執行 |
| 5 Ollama Code | ✅ 執行 | ✅ 執行 | ✅ 執行 |
| 6 Primary Review (code) | ✅ 執行 | ✅ 執行 | ✅ 執行 |
| 7 Final Review (code cross-review) | ⏭ 跳過 | ✅ 執行 | ✅ 執行 |
| 8 Learning | ✅ 執行 | ✅ 執行 | ✅ 執行 |
| 9 Git Commit | ✅ 執行 | ✅ 執行 | ✅ 執行 |

## Override

使用者可在需求中加入 `--full-review` 強制走完整流程（覆蓋 simple/medium 裁剪）。
