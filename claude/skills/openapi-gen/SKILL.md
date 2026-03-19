---
name: openapi-gen
description: "Scan project API endpoints and generate OpenAPI 3.x YAML documentation with validation. Supports Laravel, Express, and other frameworks. Triggers on: generate API docs, 生成API文件, swagger, openapi, API documentation, API文件."
metadata:
  short-description: API endpoint scanner + OpenAPI YAML generator
---

# OpenAPI Generator

Scan project API endpoints and generate OpenAPI 3.x YAML documentation.

- **Framework Detection**: Auto-detect from manifest files (composer.json, package.json, etc.)
- **Route Extraction**: Static code analysis (priority) + framework reflection (fallback)
- **Validation**: npx @redocly/cli lint

For full instructions, see `references/flow.md`
