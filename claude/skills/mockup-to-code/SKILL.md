---
name: mockup-to-code
description: >-
  Convert design mockups + assets into working HTML/CSS/JS pages with
  automated visual verification. Use when user has mockup images and
  wants to build a webpage from them. Triggers on:
  切版, mockup to code, 切頁面, 從 mockup 做, 做頁面, 把設計稿做出來,
  mockup 轉程式碼, design to code, build page from mockup, 網頁切版.
  Examples: "/mockup-to-code ./Material/mockup.jpg ./Material/assets/",
  "/mockup-to-code --mockup ./design.png --assets ./素材/",
  "/mockup-to-code" (interactive mode).
metadata:
  short-description: Mockup → HTML/CSS/JS with visual verification loop
---

# Mockup-to-Code: Design Mockup to Working Page

Convert design mockups and asset files into working HTML/CSS/JS pages.
Includes automated Playwright visual verification and iterative refinement.

## Usage

```
/mockup-to-code [--mockup PATH] [--assets PATH] [--requirements PATH] [--output PATH] [--tech html|react]
```

### Options

| Flag                   | Description                              | Default                   |
| ---------------------- | ---------------------------------------- | ------------------------- |
| `--mockup PATH`        | Mockup image (JPG/PNG)                   | interactive prompt        |
| `--assets PATH`        | Assets root folder (images, fonts, etc.) | interactive prompt        |
| `--requirements PATH`  | Requirements doc (PDF/docx/txt)          | optional                  |
| `--output PATH`        | Output project directory                 | `./package/`              |
| `--tech html\|react`   | Tech stack                               | `html` (pure HTML/CSS/JS) |
| `--mobile-mockup PATH` | Mobile version mockup                    | optional                  |
| `--max-rounds N`       | Max visual verification rounds           | `3`                       |

## Execution Flow (follow strictly)

### Phase 1: Input & Asset Scan

#### Step 1.1: Validate Inputs

If args not provided, ask interactively (one question at a time):

1. Mockup image path — MUST exist and be an image file
2. Assets folder path — MUST exist and be a directory
3. Requirements doc path — optional, skip if not provided
4. Output directory — default to `./package/` relative to the working project

Verify all paths exist before proceeding.

#### Step 1.2: Scan Assets

Run the asset scanner:

```bash
bash ~/.claude/skills/scripts/scan-assets.sh "<assets_path>"
```

This outputs a categorized JSON manifest:

- `fonts`: font files (.otf, .ttf, .woff, .woff2)
- `images`: image files (.jpg, .jpeg, .png, .svg, .gif, .webp)
- `documents`: docs (.pdf, .docx, .txt, .md)
- `videos`: video files (.mp4, .mov, .webm)
- `other`: everything else

Present the manifest summary to user:

```
素材盤點完成：
- 字型：N 個
- 圖片：N 個（含 N 個 PNG、N 個 JPG）
- 文件：N 個
- 影片：N 個
```

#### Step 1.3: Extract Text Content

If requirements doc provided:

- PDF → use `Read` tool with `pages` parameter
- docx → `textutil -convert txt -stdout <path>`
- txt/md → `Read` tool directly

Store extracted text for use in code generation.

### Phase 2: Mockup Analysis

#### Step 2.1: Read Mockup Images

Read the desktop mockup (and mobile mockup if provided) using the `Read` tool.
Claude's multimodal capabilities will analyze the visual design.

#### Step 2.2: Decompose into Sections

Analyze the mockup and output a structured section list:

```
## 區塊拆解

| # | Section ID | 區塊名稱 | 背景色/特徵 | 關鍵元素 | 互動需求 |
|---|-----------|---------|-----------|---------|---------|
| 1 | hero | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... | ... |
```

For each section, identify:

- **Background**: color, image, or gradient
- **Layout**: flex, grid, centered, sidebar
- **Typography**: headings, body text, special fonts
- **Images**: which assets map to which positions
- **Interactions**: carousels, animations, sticky elements, modals
- **Fixed elements**: floating buttons, scroll-to-top, sticky nav

#### Step 2.3: Asset Mapping

Map scanned assets to sections:

```
## 素材對應

| Asset | Target Section | Usage |
|-------|---------------|-------|
| kv-desktop.jpg | hero | 主視覺背景 |
| logo.png | navbar | 導覽列 logo |
| ... | ... | ... |
```

#### Step 2.4: User Confirmation

Present the section list + asset mapping to the user. Ask:

```
以上區塊拆解是否正確？需要調整的部分請告知。
```

Wait for confirmation before proceeding. Adjust if user requests changes.

### Phase 3: Project Scaffolding

#### Step 3.1: Create Directory Structure

```
<output>/
├── index.html
├── style.css
├── main.js
└── assets/
    ├── fonts/
    ├── images/
    │   ├── bg/
    │   ├── icons/
    │   ├── characters/
    │   ├── carousel/
    │   └── ...
    └── ...
```

Organize asset subdirectories based on the section analysis.
Use English filenames — rename CJK filenames to descriptive English names during copy.

#### Step 3.2: Copy & Rename Assets

Copy assets from source to project structure.
Apply renaming rules:

- CJK filenames → descriptive English (e.g., `主視覺.jpg` → `kv-desktop.jpg`)
- Spaces → hyphens
- Keep original extension
- Group by function (bg, icons, carousel, characters, etc.)

Log the mapping for reference.

### Phase 4: Code Generation

#### Step 4.1: HTML Structure

Generate `index.html` with:

- Semantic HTML5 structure
- One `<section>` per decomposed section
- Proper `id` attributes for anchor navigation
- Asset references using the renamed paths
- Text content from extracted requirements

#### Step 4.2: CSS Styling

Generate `style.css` with:

- `@font-face` for custom fonts
- CSS reset/base styles
- **Per-section background colors** — do NOT rely on a single full-page background image
  (sections have dynamic height; a fixed BG image will misalign)
- Section-specific styles matching mockup colors, spacing, typography
- Responsive breakpoints (basic mobile support)

Key CSS patterns to include:

- Sticky navbar
- Floating/fixed elements (book-now buttons, scroll-to-top)
- Marquee animation for continuous-scroll carousels
- Carousel layout for arrow-controlled slideshows
- Character float animation (`@keyframes floatY`)

#### Step 4.3: JavaScript

Generate `main.js` with:

- Arrow-controlled carousel (auto-rotate + manual control)
- Marquee initialization (duplicate elements for seamless loop)
- Scroll effects (page-top button visibility, navbar state)
- Mobile hamburger menu toggle
- Smooth scroll for anchor links
- Optional: petal/particle animations

### Phase 5: Visual Verification Loop

#### Step 5.1: Start Local Server

```bash
cd <output> && python3 -m http.server <port> &
```

Use a random port between 8800-8899 to avoid conflicts.

#### Step 5.2: Take Screenshots

Use Playwright MCP tools:

1. `browser_navigate` to `http://localhost:<port>`
2. `browser_take_screenshot` with `fullPage: true` for overview
3. `browser_run_code` to screenshot individual sections:

```javascript
async (page) => {
  const sections = [...]; // list of CSS selectors
  for (const s of sections) {
    const el = await page.$(s.sel);
    if (el) await el.screenshot({ path: `section-${s.name}.jpeg`, type: 'jpeg', quality: 90 });
  }
}
```

#### Step 5.3: Compare with Mockup

For each section screenshot:

1. Read the section screenshot with `Read` tool
2. Compare visually with the original mockup (already loaded in context)
3. Generate a diff report:

```
## 比對報告 (Round N/3)

| # | Section | Match % | Issues |
|---|---------|---------|--------|
| 1 | hero | 95% | 花瓣可更多 |
| 2 | about | 80% | 角色尺寸偏小 |
| ... | ... | ... | ... |

**Overall: XX%**
```

#### Step 5.4: Fix Issues

For each issue with match < 85%:

1. Identify the CSS/HTML change needed
2. Apply the fix using `Edit` tool
3. Track what was changed

#### Step 5.5: Iterate

Repeat Steps 5.2-5.4 up to `--max-rounds` times (default 3).
Stop early if overall match >= 90%.

After all rounds, present final report:

```
## 最終比對報告

| # | Section | Match % |
|---|---------|---------|
| ... | ... | ... |

**Overall: XX%**
**Rounds used: N/3**
```

### Phase 6: Cleanup & Report

1. Kill the HTTP server process
2. Present final file listing:
   ```
   產出檔案：
   - index.html (N lines)
   - style.css (N lines)
   - main.js (N lines)
   - assets/ (N files)
   ```
3. Suggest next steps:
   - Mobile RWD refinement
   - Additional pages (if multi-page site)
   - Animation enhancement
   - Deployment

## Design Principles

1. **Per-section backgrounds** — NEVER use a single full-page background image.
   Each section gets its own `background` CSS. This avoids color-band misalignment
   when content heights change.

2. **Asset renaming** — Always rename CJK filenames to English.
   This prevents encoding issues and makes code more maintainable.

3. **Iterative refinement** — The visual verification loop is the core value.
   Don't try to be perfect on the first pass. Get 70% right, then iterate.

4. **Human-in-the-loop** — Section decomposition (Phase 2) MUST be confirmed
   by the user before code generation. This is where most errors occur.

5. **Separation of concerns** — HTML for structure, CSS for presentation,
   JS for interaction. No inline styles. No CSS-in-JS.

## Platform Image Reading Capabilities

Visual comparison (Phase 5) depends on the platform's ability to read images.
Choose the best strategy based on the running environment:

| Platform        | Image Reading              | Strategy                                               |
| --------------- | -------------------------- | ------------------------------------------------------ |
| **Claude Code** | `Read` tool (multimodal)   | Native — read screenshots directly, compare in context |
| **Gemini CLI**  | Native `@path/to/file.png` | Native — best UX, auto-reads local images              |
| **Codex CLI**   | No native image reading    | Workaround needed (see below)                          |

### Delegation Strategy for Visual Comparison

When running in **Claude Code** (primary):

- Use Playwright MCP to take screenshots
- Use `Read` tool to load screenshots into context
- Claude's multimodal vision does the comparison

When delegating via `/ask gemini`:

- Gemini can natively read local screenshots via `@path` syntax
- Ideal for second-opinion visual comparison
- Send: `@section-hero.jpeg @mockup.jpg "Compare these two images, list visual differences"`

When delegating via `/ask codex`:

- Codex CANNOT read images directly
- Workaround: describe the expected layout in text, ask Codex to review CSS/HTML for correctness
- Use Codex for code review, NOT visual comparison

### Recommended Multi-AI Visual Review

For critical pages, use dual comparison:

1. **Claude** — primary visual diff (Playwright screenshot vs mockup)
2. **Gemini** — second opinion via `/ask gemini` with `@screenshot @mockup`
3. Merge both reports, fix overlapping issues first

## Known Limitations

- AI mockup-to-code achieves ~85-90% visual match. Pixel-perfect alignment requires manual tuning.
- Complex animations (parallax, scroll-triggered, SVG morphing) need case-by-case implementation.
- Cannot read Figma/Sketch/XD files directly — export to PNG/JPG first.
- Font rendering may differ between mockup tool and browser.
- Codex CLI cannot read images — use Gemini or Claude for visual comparison tasks.
