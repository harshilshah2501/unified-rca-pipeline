#!/usr/bin/env bash
# Build A4 PDF from dissection markdown file(s).
# Usage (from repo root or anywhere):
#   ./federated-pipeline/scripts/build-dissection-pdf.sh
#   ./federated-pipeline/scripts/build-dissection-pdf.sh Panorama_dissection.md
set -euo pipefail

FP="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="$FP/docs/dissections"
ASSETS="$FP/docs/assets"
cd "$DOCS"

build_one() {
  local DOC="$1"
  local BASE="${DOC%.md}"
  local OUT="${BASE}.pdf"

  if [[ ! -f "$DOC" ]]; then
    echo "error: $DOC not found in $DOCS" >&2
    return 1
  fi

  local PANDOC_OPTS=(
    "$DOC"
    -o "$OUT"
    --css="$ASSETS/dissection-print.css"
    -V papersize=a4
    -V geometry:margin=18mm
    --resource-path="$DOCS:$ASSETS"
  )

  if command -v xelatex >/dev/null 2>&1; then
    echo "Building $OUT (XeLaTeX)..."
    pandoc "${PANDOC_OPTS[@]}" \
      --pdf-engine=xelatex \
      -V mainfont="DejaVu Serif"
  elif command -v wkhtmltopdf >/dev/null 2>&1; then
    echo "Building $OUT (HTML + wkhtmltopdf)..."
    local HTML="/tmp/${BASE}.html"
    pandoc "$DOC" -o "$HTML" \
      --css="$ASSETS/dissection-print.css" \
      --standalone \
      --metadata "title=${BASE}" \
      --resource-path="$DOCS:$ASSETS"
    wkhtmltopdf --page-size A4 -B 18mm -T 18mm -L 16mm -R 16mm \
      "$HTML" "$OUT" 2>/dev/null || true
  else
    echo "error: install texlive-xetex or wkhtmltopdf" >&2
    return 1
  fi

  echo "  → $OUT ($(du -h "$OUT" | cut -f1))"
}

if [[ $# -eq 0 ]]; then
  for doc in Panorama_dissection.md Murphy_dissection.md Nezha-dissection.md; do
    build_one "$doc"
  done
else
  for doc in "$@"; do
    build_one "$(basename "$doc")"
  done
fi
