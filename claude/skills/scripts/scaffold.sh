#!/usr/bin/env bash
# scaffold.sh — Skill scaffold generator
# 用法: scaffold.sh SKILL_NAME [TIER]
#   TIER: simple (預設) | intermediate | complex
# 輸出: 在 ~/.claude/skills/ 下建立 skill 目錄結構
#
# 範例:
#   scaffold.sh my-tool              → simple (SKILL.md only)
#   scaffold.sh my-workflow intermediate → SKILL.md + references/flow.md
#   scaffold.sh my-system complex    → SKILL.md + references/ + adapters/ + templates/

set -euo pipefail

SKILLS_DIR="${HOME}/.claude/skills"

if [ $# -lt 1 ]; then
  echo "Usage: scaffold.sh SKILL_NAME [simple|intermediate|complex]" >&2
  exit 1
fi

SKILL_NAME="$1"
TIER="${2:-simple}"
SKILL_DIR="${SKILLS_DIR}/${SKILL_NAME}"

if [ -d "$SKILL_DIR" ]; then
  echo "Error: skill '${SKILL_NAME}' already exists at ${SKILL_DIR}" >&2
  exit 1
fi

# Validate tier
case "$TIER" in
  simple|intermediate|complex) ;;
  *) echo "Error: unknown tier '${TIER}'. Use: simple, intermediate, complex" >&2; exit 1 ;;
esac

echo "Creating ${TIER} skill: ${SKILL_NAME}"

# --- Simple: SKILL.md only ---
mkdir -p "$SKILL_DIR"

cat > "${SKILL_DIR}/SKILL.md" << EOF
---
name: ${SKILL_NAME}
description: >-
  TODO: Describe what this skill does and when to use it.
  Include 2-3 example invocations.
metadata:
  short-description: TODO brief summary
---

# ${SKILL_NAME}

TODO: Skill description.

## Usage

\`\`\`
/${SKILL_NAME} [arguments]
\`\`\`

## Execution Flow

EOF

if [ "$TIER" = "simple" ]; then
  cat >> "${SKILL_DIR}/SKILL.md" << 'EOF'
Follow these steps:

1. Parse user input from `$ARGUMENTS`
2. Execute the task
3. Present results

## Notes

- Maintain the Qing dynasty court official communication style
EOF
  echo "✅ Created simple skill: ${SKILL_DIR}/"
  echo "   └── SKILL.md"
  exit 0
fi

# --- Intermediate: + references/flow.md ---
cat >> "${SKILL_DIR}/SKILL.md" << 'EOF'
For full instructions, see `references/flow.md`
EOF

mkdir -p "${SKILL_DIR}/references"

cat > "${SKILL_DIR}/references/flow.md" << EOF
# ${SKILL_NAME} Execution Flow

## Input

- \`\$ARGUMENTS\`: User's request

## Execution Flow

### Step 1: TODO

### Step 2: TODO

### Step 3: TODO

---

## Error Handling

- TODO: Define error scenarios and fallback behavior

---

## Principles

1. TODO
EOF

if [ "$TIER" = "intermediate" ]; then
  echo "✅ Created intermediate skill: ${SKILL_DIR}/"
  echo "   ├── SKILL.md"
  echo "   └── references/"
  echo "       └── flow.md"
  exit 0
fi

# --- Complex: + adapters/ + templates/ + scripts/ ---
mkdir -p "${SKILL_DIR}/adapters"
mkdir -p "${SKILL_DIR}/templates"

cat > "${SKILL_DIR}/adapters/claude-code.md" << EOF
# ${SKILL_NAME} — Claude Code Adapter

## Role Mapping

| Role | Provider |
|------|----------|
| designer | claude |
| reviewer | codex |
| executor | claude |

## Platform-Specific Notes

- MCP tools available via \`mcp__mcp-ai-bridge__*\`
- Async delegation via \`/ask <provider>\`
EOF

cat > "${SKILL_DIR}/templates/README.md" << 'EOF'
# Templates

Place FileOpsREQ JSON templates here.

Naming: `{purpose}.json`
Format: `autoflow.fileops.v1` protocol

Placeholders use `{{PLACEHOLDER}}` syntax, documented in `_meta.placeholders`.
EOF

echo "✅ Created complex skill: ${SKILL_DIR}/"
echo "   ├── SKILL.md"
echo "   ├── references/"
echo "   │   └── flow.md"
echo "   ├── adapters/"
echo "   │   └── claude-code.md"
echo "   └── templates/"
echo "       └── README.md"
