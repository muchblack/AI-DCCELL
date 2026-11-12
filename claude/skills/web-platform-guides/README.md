# Web Platform Guides（摘錄）

（非 skill：此目錄沒有 SKILL.md，不會被自動觸發；由 mandi、mockup-to-code、react-best-practices 按需引用。）

- 來源：https://github.com/GoogleChrome/modern-web-guidance （commit 4dd9683，2026-11-10）
- 授權：指南內容為 CC BY 4.0（https://creativecommons.org/licenses/by/4.0/），© Google / GoogleChrome contributors；程式碼部分為 Apache-2.0（見 LICENSE-Apache-2.0）。
- 修改：僅挑選子集，保留原始相對路徑，內文未改動。

## 使用規則
- 純參考資料。指南內出現的 `npx modern-web-guidance ...` 指令一律不執行。
- 查詢：`rg -n -i -e '<api>' -e '<同義詞>' ~/.claude/skills/web-platform-guides/guides`，只讀命中段落與其 fallback／相容性段落。
- 指南提到但此處沒有的 guide id：直接回報「未收錄」，不要退回 npx。
- 離線版沒有 CLI 的 feature gate：先確認目標瀏覽器；origin trial／實驗性 API 不主動採用；指南要求 fallback 就照做。
- 專案既有元件、瀏覽器目標、使用者指定範圍優先於指南。
- 更新：看上游 diff 人工審過後，整批替換 guides/ 並更新上方 commit 號，不用 `@latest`。
