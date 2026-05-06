# Structured doneConditions Schema

Used by /tp (planning) and /tr (verification). Each doneCondition is a JSON object with a required 'type' field.

## Backward Compatibility

Legacy doneConditions (plain strings) are converted to `{ type: "manual", description: <the string> }` and therefore **skipped by auto-verification** — they never cause a verification failure. No migration needed for existing plans.

## Types

### file_exists
Verify a file or glob pattern exists.

- **pattern** (required): Glob pattern or exact file path. Paths are relative to the repo/working directory root. Standard glob syntax supported (`*`, `**`, `?`).
- **Verification**: Glob(pattern) returns >= 1 match

### grep_match
Verify content matches in a file.

- **pattern** (required): Regex pattern to search for (ripgrep syntax — Rust regex, not PCRE)
- **path** (required): File or directory to search in. Relative to repo/working directory root.
- **Verification**: Grep(pattern, path) returns >= 1 match

### test_passes
Verify a test command exits 0.

- **cmd** (required): Shell command to execute
- **Verification**: Bash(cmd) exit code == 0

### build_succeeds
Verify a build command exits 0.

- **cmd** (required): Shell command to execute
- **Verification**: Bash(cmd) exit code == 0

### no_lint_errors
Verify a lint command exits 0.

- **cmd** (required): Shell command to execute
- **Verification**: Bash(cmd) exit code == 0

### manual
Cannot be auto-verified. Skipped during Ralph Verification Gate (Step 8.6). Prompts user for manual confirmation.

- **description** (required): What the human should verify
- **Verification**: None (skipped in auto-verify, flagged for human)

## Usage in /tp Planning

When creating step doneConditions in /tp or /tr Step 2 design:
- Use structured objects for machine-verifiable conditions
- Use 'manual' type for human-judgment-only conditions
- Max 2 doneConditions per step (from design merge)

## Usage in /tr Verification (Step 8.6)

The Ralph Verification Gate iterates each doneCondition:
1. If string (legacy) -> treat as { type: 'manual', description: <string> }
2. If object with type -> execute type-specific verification
3. All auto-verifiable passed + manual skipped -> PASS
4. Any auto-verifiable failed -> trigger auto-fix retry
