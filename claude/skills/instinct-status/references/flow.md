# Instinct Status Execution Flow

Display learned instincts with statistics.

## Input

- `$ARGUMENTS`: Optional domain filter

## Execution Flow

### Step 1: Scan Instinct Directories

Read all `.md` files from:
- `~/.claude/instincts/approved/` (active instincts)
- `~/.claude/instincts/pending/` (awaiting review)

Parse YAML frontmatter from each file.

### Step 2: Display Statistics

```
## Instinct 統計
- ✅ 已核准: {count}
- ⏳ 待審查: {count}
- 🚫 已拒絕: {count in rejected/}
- 📊 平均信心分數: {avg confidence of approved}
```

### Step 3: Display Approved Instincts (grouped by domain)

If `$ARGUMENTS` specifies a domain, filter to that domain only.

```
### {Domain}

| ID | 觸發條件 | 行為 | 信心 | 建立日期 |
|----|----------|------|------|----------|
| {id} | {trigger} | {action} | {confidence} | {created} |
```

### Step 4: Display Pending (if any)

```
### ⏳ 待審查

| ID | 觸發條件 | 領域 | 信心 |
|----|----------|------|------|
| {id} | {trigger} | {domain} | {confidence} |

💡 執行 `/learn` 來審查這些 instincts
```

### Step 5: Observations Stats

Check `~/.claude/observations/` for the current project:
- Total observation count
- File size
- Last observation timestamp

```
### 📝 觀察記錄
- 當前專案觀察數: {count}
- 檔案大小: {size}
- 最後記錄: {timestamp}
```
