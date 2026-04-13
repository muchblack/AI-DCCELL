#!/usr/bin/env bash
# scan-assets.sh — Scan an assets folder and output categorized manifest
# Usage: scan-assets.sh <assets_path>

set -euo pipefail

ASSETS_PATH="${1:-.}"

if [ ! -d "$ASSETS_PATH" ]; then
  echo "Error: Directory not found: $ASSETS_PATH" >&2
  exit 1
fi

# Count by category
count_fonts=0
count_images=0
count_png=0
count_jpg=0
count_svg=0
count_docs=0
count_videos=0
count_other=0

fonts=()
images=()
documents=()
videos=()
others=()

while IFS= read -r -d '' file; do
  ext="${file##*.}"
  ext_lower="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"
  rel="${file#$ASSETS_PATH/}"

  case "$ext_lower" in
    otf|ttf|woff|woff2|eot)
      fonts+=("$rel")
      ((count_fonts++))
      ;;
    jpg|jpeg)
      images+=("$rel")
      ((count_images++))
      ((count_jpg++))
      ;;
    png)
      images+=("$rel")
      ((count_images++))
      ((count_png++))
      ;;
    svg)
      images+=("$rel")
      ((count_images++))
      ((count_svg++))
      ;;
    gif|webp|ico)
      images+=("$rel")
      ((count_images++))
      ;;
    pdf|docx|doc|txt|md)
      documents+=("$rel")
      ((count_docs++))
      ;;
    mp4|mov|webm|avi)
      videos+=("$rel")
      ((count_videos++))
      ;;
    ds_store|db)
      # skip system files
      ;;
    *)
      others+=("$rel")
      ((count_other++))
      ;;
  esac
done < <(find "$ASSETS_PATH" -type f -print0 2>/dev/null)

# Output summary
echo "=== Asset Scan: $ASSETS_PATH ==="
echo ""
echo "Summary:"
echo "  Fonts:     $count_fonts"
echo "  Images:    $count_images (PNG: $count_png, JPG: $count_jpg, SVG: $count_svg)"
echo "  Documents: $count_docs"
echo "  Videos:    $count_videos"
echo "  Other:     $count_other"
echo ""

if [ ${#fonts[@]} -gt 0 ]; then
  echo "--- Fonts ---"
  printf '  %s\n' "${fonts[@]}"
  echo ""
fi

if [ ${#images[@]} -gt 0 ]; then
  echo "--- Images ---"
  printf '  %s\n' "${images[@]}"
  echo ""
fi

if [ ${#documents[@]} -gt 0 ]; then
  echo "--- Documents ---"
  printf '  %s\n' "${documents[@]}"
  echo ""
fi

if [ ${#videos[@]} -gt 0 ]; then
  echo "--- Videos ---"
  printf '  %s\n' "${videos[@]}"
  echo ""
fi

if [ ${#others[@]} -gt 0 ]; then
  echo "--- Other ---"
  printf '  %s\n' "${others[@]}"
  echo ""
fi
