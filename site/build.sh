#!/usr/bin/env bash
# Assemble the publishable folder (dist/) — only what the browser needs.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf dist && mkdir -p dist
cp index.html dist/
cp -r assets dist/
find dist -name '*.map' -delete
echo "dist: $(find dist -type f | wc -l) files, $(du -sb dist | cut -f1) bytes"
