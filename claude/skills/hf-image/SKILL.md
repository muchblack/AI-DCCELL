---
name: hf-image
description: >-
  Generate images using Hugging Face open-source models (FLUX.1, SDXL).
  Use when user wants to generate images from text prompts. Triggers on:
  生圖, 畫圖, generate image, hf image, 用 HF 生圖, text to image, 文生圖.
  Examples: "/hf-image a cat on the moon",
  "/hf-image --ratio 16:9 cyberpunk cityscape at sunset",
  "/hf-image --model stabilityai/stable-diffusion-xl-base-1.0 --mode i2i --input-image ./ref.png transform this".
metadata:
  short-description: HF text-to-image + image-to-image
---

# HF-Image: Hugging Face Image Generation

Generate images using open-source models on Hugging Face Inference API.

## Usage

```
/hf-image [options] <prompt>
```

### Options

| Flag                                | Description                                     | Default                            |
| ----------------------------------- | ----------------------------------------------- | ---------------------------------- |
| `--model MODEL`                     | HF model ID                                     | `black-forest-labs/FLUX.1-schnell` |
| `--mode t2i\|i2i`                   | Text-to-image or image-to-image                 | `t2i`                              |
| `--ratio 1:1\|16:9\|9:16\|4:3\|3:4` | Aspect ratio                                    | `1:1`                              |
| `--seed N`                          | Random seed (best-effort reproducibility)       | random                             |
| `--negative-prompt "..."`           | What NOT to include (SDXL only)                 | none                               |
| `--guidance N`                      | Guidance scale (FLUX.1-dev, SDXL)               | model default                      |
| `--steps N`                         | Inference steps (FLUX.1-dev, SDXL)              | model default                      |
| `--scheduler NAME`                  | Scheduler override (SDXL only)                  | model default                      |
| `--input-image PATH`                | Input image for i2i mode (SDXL only)            | required for i2i                   |
| `--open`                            | Open image in macOS Preview after generation    | off                                |
| `--refine`                          | Reload last generation's params and re-generate | off                                |
| `--history [N]`                     | List last N history entries (default 5)         | —                                  |
| `--no-enhance`                      | Skip prompt expansion                           | off                                |

### Supported Models

| Model                                        | t2i | i2i | guidance | steps | scheduler | negative_prompt | seed |
| -------------------------------------------- | --- | --- | -------- | ----- | --------- | --------------- | ---- |
| `black-forest-labs/FLUX.1-schnell` (default) | Y   | N   | N        | N     | N         | N               | Y    |
| `black-forest-labs/FLUX.1-dev`               | Y   | N   | Y        | Y     | N         | N               | Y    |
| `stabilityai/stable-diffusion-xl-base-1.0`   | Y   | Y   | Y        | Y     | Y         | Y               | Y    |

Unsupported params for a model are silently ignored with a stderr warning.
Unknown models: all params sent as-is.

## Execution Flow (follow strictly)

### Step 0: Pre-flight Check

1. Check `HF_TOKEN` environment variable is set:

   ```bash
   if [ -z "${HF_TOKEN:-}" ]; then
     # Tell user: "HF_TOKEN not set. Get your token at https://huggingface.co/settings/tokens"
     # Suggest: export HF_TOKEN=hf_xxxxx
     exit
   fi
   ```

2. Optionally check HF API health:
   ```bash
   bash ~/.claude/skills/scripts/health-check.sh hf
   ```

### Step 1: Parse User Input

Extract from user's message:

- The prompt text (everything after flags)
- Any flags (--model, --ratio, --seed, etc.)
- Special modes: --history, --refine

If `--history` is specified, run the script in history mode and display results, then stop.

### Step 2: Prompt Expansion (optional)

If the prompt is short (<10 words) and `--no-enhance` is NOT set:

- Claude enhances the prompt by adding style/quality descriptors
- Show both original and enhanced prompt to user
- Use the enhanced prompt for generation

Example:

- User: "a cat"
- Enhanced: "a cat, high quality, detailed fur texture, soft lighting, professional photography"

The enhanced prompt is logged separately in history.

### Step 3: Call Script

```bash
bash ~/.claude/skills/scripts/hf-image.sh \
  --prompt "PROMPT" \
  [--model MODEL] [--mode MODE] [--ratio RATIO] \
  [--seed N] [--negative-prompt "..."] [--guidance N] \
  [--steps N] [--scheduler NAME] [--input-image PATH] \
  [--refine]
```

Parse the JSON output from stdout.

### Step 4: Handle Result

#### On Success (`status: "ok"`)

1. Display generation info:

   ```
   ## Image Generated

   **Model**: {model} | **Time**: {duration_ms}ms | **Size**: {width}x{height} | **Seed**: {seed}
   ```

2. Use `Read` tool to display the image:

   ```
   Read(file_path="{path}")
   ```

3. If `--open` flag was set:

   ```bash
   open "{path}"
   ```

4. Report the file path for user reference.

#### On Error (`status: "error"`)

Display error with actionable suggestion:

| Error Code      | User Message                                                      |
| --------------- | ----------------------------------------------------------------- |
| `token_invalid` | "HF_TOKEN is not set or invalid. Run: `export HF_TOKEN=hf_xxxxx`" |
| `rate_limited`  | "Rate limited by HF. Wait a moment and try again."                |
| `model_loading` | "Model is cold-starting. Try again in 1-2 minutes."               |
| `timeout`       | "Request timed out. Try a simpler prompt or different model."     |
| `network`       | "Cannot reach HF API. Check internet connection."                 |

### Step 4.5: Telemetry (automatic)

After every invocation, record telemetry:

```bash
bash ~/.claude/skills/scripts/telemetry.sh record hf-image hf <duration_ms> <result>
```

- `result`: `ok` / `error` / `timeout` / `rate_limited`

## History & Refine

- History is stored at `~/.claude/hf-images/history.jsonl`
- Each successful generation appends an entry with id, prompt, model, params, path, duration
- `--history [N]` displays last N entries in a formatted table
- `--refine` loads the last entry's prompt+params and re-generates (seed is best-effort)

## Notes

- HF Inference API has free tier rate limits (~5-10 requests/minute)
- FLUX.1-schnell is the fastest free model (5-15s typical)
- Images are saved to `~/.claude/hf-images/` with timestamp filenames
- Seed reproduction is best-effort — HF does not guarantee determinism across backends
- Maintain the Qing dynasty court official communication style throughout
