---
name: branch
description: >-
  從需求文件建立 git 分支。讀取 Markdown 需求文件，提取專案前綴，
  AI 生成功能名，組合為分支名稱並建立。Triggers on: 建分支, 開分支,
  create branch, new branch, 從需求開分支, branch from spec, 切分支.
  Examples: "/branch ./req.md", "/branch ./spec.md --from develop".
argument-hint: "<markdown-file> [--from <base-branch>]"
---

# 從需求文件建立 Git 分支

讀取指定的 Markdown 需求文件，自動提取專案前綴（如票號、專案代碼），
根據需求內容生成 kebab-case 功能名，組合為 `前綴_功能名` 格式的分支名稱。

使用者確認分支名稱後，從指定的基底分支建立並切換至新分支。

完整流程見 `references/flow.md`
