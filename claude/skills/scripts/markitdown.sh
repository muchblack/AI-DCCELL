#!/usr/bin/env bash
# markitdown.sh — Convert documents to Markdown via microsoft/markitdown
# Wraps the markitdown CLI installed in a dedicated venv (~/.markitdown-env).
#
# Usage:
#   markitdown.sh <input>                 # write Markdown to stdout
#   markitdown.sh <input> -o <output.md>  # write to file
#   markitdown.sh --list                  # show supported formats
#   markitdown.sh --version               # show installed markitdown version
#
# Environment:
#   MARKITDOWN_VENV — override venv path (default: ~/.markitdown-env)

set -uo pipefail

VENV="${MARKITDOWN_VENV:-$HOME/.markitdown-env}"
BIN="$VENV/bin/markitdown"

if [ ! -x "$BIN" ]; then
  echo "markitdown not found at $BIN" >&2
  echo "Install with:" >&2
  echo "  python3 -m venv $VENV && $VENV/bin/pip install 'markitdown[all]'" >&2
  exit 127
fi

case "${1:-}" in
  --list|--formats)
    cat <<'EOF'
Supported input formats (microsoft/markitdown):
  Documents : PDF, DOCX, PPTX, XLSX, XLS
  Web       : HTML, EPUB
  Data      : CSV, JSON, XML
  Archives  : ZIP (recursively converts contents)
  Media     : Images (EXIF + OCR), Audio (metadata + transcription)
  Other     : YouTube URLs, Outlook .msg, plain text

Output: Markdown to stdout (or use -o <file.md>).
EOF
    exit 0
    ;;
  --version|-V)
    exec "$BIN" --version
    ;;
  "")
    echo "Usage: markitdown.sh <input> [-o output.md]" >&2
    echo "       markitdown.sh --list" >&2
    exit 2
    ;;
esac

exec "$BIN" "$@"
