---
name: markitdown
description: >-
  Convert documents to Markdown using microsoft/markitdown. Supports PDF, DOCX,
  PPTX, XLSX, HTML, EPUB, CSV, JSON, XML, ZIP archives, images (EXIF + OCR),
  audio (metadata + transcription), YouTube URLs, and Outlook .msg files.
  Output is structure-preserving Markdown optimized for feeding into LLMs.
  Triggers on: 轉 markdown, 轉成 md, convert to markdown, markitdown,
  PDF 轉文字, 文件轉 md, 解析 PDF, parse document, extract text from.
  Examples: "/markitdown ./report.pdf",
  "/markitdown ./slides.pptx -o slides.md",
  "/markitdown https://www.youtube.com/watch?v=...".
compatibility: Requires Python 3.10+ and markitdown installed in ~/.markitdown-env (or override via MARKITDOWN_VENV).
metadata:
  short-description: Convert PDF/Office/HTML/media to Markdown for LLMs
---

# Markitdown: Document → Markdown

Wraps [microsoft/markitdown](https://github.com/microsoft/markitdown) so any
supported file (or YouTube URL) becomes structure-preserving Markdown. Built
for LLM ingestion — keeps headings, lists, tables, links; strips visual
chrome.

## Usage

```
/markitdown <input> [-o output.md]
/markitdown --list           # show supported formats
/markitdown --version        # show installed version
```

`<input>` may be a local file path or a URL (YouTube is the documented
URL case). Without `-o`, Markdown is written to stdout.

## Supported Inputs

| Category   | Formats                                            |
| ---------- | -------------------------------------------------- |
| Documents  | PDF, DOCX, PPTX, XLSX, XLS                         |
| Web / Book | HTML, EPUB                                         |
| Data       | CSV, JSON, XML                                     |
| Archives   | ZIP (walks contents)                               |
| Media      | Images (EXIF + OCR), Audio (metadata + transcript) |
| Other      | YouTube URLs, Outlook `.msg`, plain text           |

## Execution Flow

### Step 0: Pre-flight

Confirm the wrapper script and venv exist:

```bash
ls ~/.markitdown-env/bin/markitdown >/dev/null 2>&1 || {
  echo "markitdown venv missing — run: python3 -m venv ~/.markitdown-env && ~/.markitdown-env/bin/pip install 'markitdown[all]'"
  exit 127
}
```

### Step 1: Parse Input

From the user's message extract:

- The input path or URL (the only positional argument)
- Optional `-o <output.md>` destination
- Mode flags: `--list`, `--version`

If the user just says e.g. "把這個 PDF 轉成 markdown 存到 foo.md"，無需追問，
直接組成 `bash ~/.claude/skills/scripts/markitdown.sh <input> -o foo.md`.

### Step 2: Run

Invoke the wrapper script:

```bash
bash ~/.claude/skills/scripts/markitdown.sh "$INPUT" ${OUTPUT:+-o "$OUTPUT"}
```

For very large outputs (PDFs over ~50 pages, big XLSX), prefer `-o` to a file
rather than dumping to stdout, otherwise the conversation context bloats.

### Step 3: Report

After conversion succeeds, briefly tell 皇上:

- Output location (file path or "stdout")
- A 1–2 line preview of the Markdown (first heading, table count, etc.)
- Any warnings markitdown emitted to stderr

Do NOT paste the full converted Markdown into chat unless explicitly asked —
it can be huge. Save to file and summarize.

### Step 4: Failure Modes

| Symptom                          | Likely cause                | Fix                                         |
| -------------------------------- | --------------------------- | ------------------------------------------- |
| `markitdown not found at …`      | venv not installed          | Run the install command in Pre-flight       |
| `KeyError` / `UnsupportedFormat` | File extension misdetected  | Try renaming to correct extension           |
| Empty / whitespace-only output   | Image-only PDF, no OCR text | Run with `[all]` extras (already installed) |
| YouTube failure                  | Network / region block      | Retry; some videos disable transcripts      |

## Boundaries

- This skill does NOT do LLM image captioning. Pure format conversion only.
  If 皇上 wants AI-generated alt-text for images, ask first — would need
  OpenAI client wiring.
- Do NOT use markitdown for HTML scraping when `WebFetch` would do — markitdown
  is for converting files 朕 already has, not for arbitrary web crawling.
- Token-aware: PDFs/XLSX can balloon to tens of MB of Markdown. Always prefer
  `-o file.md` for anything non-trivial, then read the file.
