---
name: obs
description: Obsidian 知識庫操作。建立筆記、讀取、搜尋、寫入、Git 同步、分類整理、AI 編譯、知識圖譜、連結發現、健康檢查。支援 --vault 指定其他儲存庫。Use when user wants to interact with their Obsidian vault, read, sort, categorize, compile, link, graph or health-check notes. Triggers on: 筆記, 知識庫, obsidian, vault, 寫筆記, 找筆記, 搜尋筆記, 整理筆記, 分類筆記, 編譯筆記, 知識圖譜, 連結發現, 健康檢查, note, wiki, 收件匣, inbox, compile, link, graph, health.
metadata:
  short-description: Obsidian vault 操作
---

# Obsidian 知識庫操作

操作個人 Obsidian 知識庫（建立、讀取、搜尋、寫入、同步、分類整理、AI 編譯、知識連結發現、健康檢查）。
支援 `--vault <path>` 指定其他儲存庫，未指定時使用 `$OBSIDIAN_VAULT`。

## 子命令一覽

| 子命令 | 用途 |
|--------|------|
| `new <type>` | 建立新筆記（daily/meeting/project/sop/til） |
| `search <query>` | 搜尋筆記 |
| `read <path>` | 讀取筆記 |
| `write <path>` | 寫入筆記 |
| `sync [action]` | Git 同步 |
| `sort [path]` | PARA 分類整理 |
| `compile [path]` | AI 編譯：原始筆記 → 結構化 + 品質評分 + 歸檔 |
| `graph [--open] [--moc]` | 知識圖譜生成（NetworkX + Louvain 社群偵測 + vis.js 視覺化） |
| `link [path]` | 知識連結發現（圖譜拓撲 + 語義搜尋 + 4 層連結類型） |
| `health` | 全庫健康檢查報告（含圖譜健康指標） |

For full instructions, see `references/flow.md`
