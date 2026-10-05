#!/bin/sh
# Re-render the flipbook page images from the PDF.
# Run this only when docs/text/zendegi-nameh-final.pdf changes.
# Needs: pdftoppm (poppler) and cwebp (webp)  —  brew install poppler webp
set -eu

root="$(cd "$(dirname "$0")/.." && pwd)"
pdf="$root/docs/text/zendegi-nameh-final.pdf"
out="$root/src/flip/pages"
width=1300
quality=78

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

pdftoppm -scale-to-x "$width" -scale-to-y -1 -png "$pdf" "$tmp/p"

rm -rf "$out"
mkdir -p "$out"
n=0
for png in "$tmp"/p-*.png; do
  n=$((n + 1))
  cwebp -quiet -q "$quality" -m 6 "$png" -o "$out/p$(printf %03d "$n").webp"
done

echo "$n pages -> $out ($(du -sh "$out" | cut -f1))"
echo "If the page count changed, update PAGE_COUNT and CHAPTER_PAGES in build.py."
