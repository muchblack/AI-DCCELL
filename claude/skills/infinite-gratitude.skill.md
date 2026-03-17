# 🐾 無限貓報恩 | Infinite Gratitude | 無限の恩返し

> Multi-agent research that keeps bringing gifts back — like cats! 🐱

## Trigger

`/infinite-gratitude`

## Description

Dispatch multiple agents to research a topic in parallel. They bring back findings, and based on new discoveries, go out again — like cats bringing gifts home, endlessly.

## Arguments

- `topic` (required): Research topic
- `--depth`: `quick` / `normal` / `deep` (default: `normal`)
- `--agents`: Number of agents, 1-10 (default: `5`)

## Usage

```
/infinite-gratitude "pet AI recognition"
/infinite-gratitude "RAG best practices" --depth deep
/infinite-gratitude "React state management" --agents 3
```

## Behavior

### Step 1: Split directions

Split `{topic}` into 5 parallel research directions:
1. GitHub projects
2. HuggingFace models
3. Papers / articles
4. Competitors
5. Best practices

### Step 2: Dispatch agents

```
Task(
    prompt="Research {direction} for {topic}. Find:
    1. Top 3-5 recommendations
    2. Pros and cons
    3. Use cases
    4. Key insights

    Output: Markdown",
    subagent_type="research-scout",
    model="haiku",
    run_in_background=True
)
```

### Step 3: Collect gifts

Compile all findings:

```markdown
# {topic} Report

## 📊 Overview
- Time: {timestamp}
- Agents: {count}

## 🔍 Findings
### 1. GitHub
### 2. HuggingFace
### 3. Papers
### 4. Competitors
### 5. Best Practices

## 💡 Key Insights

## 🔄 Follow-up Questions
```

### Step 4: Loop

If follow-up questions exist:
- Ask user → Continue? → Back to Step 2
- No questions or user declines → End

### Step 5: Final report

## Example

```
🐾 Infinite Gratitude!

📋 Topic: "pet AI recognition"
🐱 Dispatching 5 agents...

━━━━━━━━━━━━━━━━━━━━━━
🎁 Wave 1
━━━━━━━━━━━━━━━━━━━━━━

🐱 GitHub: MegaDescriptor, wildlife-datasets...
🐱 HuggingFace: DINOv2, CLIP...
🐱 Papers: Petnow uses Siamese Network...
🐱 Competitors: Petnow 99%...
🐱 Tutorials: ArcFace > Triplet Loss...

💡 Key: Data volume is everything!

🔍 New questions:
   - How to implement ArcFace?
   - How to use MegaDescriptor?

Continue? (y/n)

🐾 by washinmura.jp
```

## Notes

- Uses `haiku` to save cost
- Max 5 agents per wave
- Deep mode loops until satisfied

---

*🐾 Made with love by [Washin Village](https://washinmura.jp) — Home of 28 cats & dogs*
