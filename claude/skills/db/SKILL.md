---
name: db
description: "查詢 Podman MariaDB 的 schema（表、欄位、索引），用於規劃與開發時確認 DB 結構。"
argument-hint: "[database] [table] [--sql 'raw query']"
---

# 資料庫 Schema 查詢

透過 Podman MariaDB 容器查詢資料庫結構，支援列 DB、列表、查欄位、執行唯讀 SQL。

完整流程見 `references/flow.md`
