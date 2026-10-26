#!/usr/bin/env bash
# Scroll-scrub encodes for the sales-journey film (same settings as encode.sh).
set -euo pipefail
ffmpeg -v error -y -i out/sales-master.mp4 -an -vf "unsharp=5:5:0.4:5:5:0.0" \
  -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -g 8 -keyint_min 8 -sc_threshold 0 -movflags +faststart out/sales-desktop.mp4
ffmpeg -v error -y -i out/sales-master-portrait.mp4 -an -vf "scale=720:-2,unsharp=5:5:0.3:5:5:0.0" \
  -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p -g 4 -keyint_min 4 -sc_threshold 0 -movflags +faststart out/sales-mobile.mp4
ffmpeg -v error -y -ss 0 -i out/sales-desktop.mp4 -frames:v 1 -q:v 2 out/sales-poster.jpg
ffmpeg -v error -y -ss 0 -i out/sales-mobile.mp4 -frames:v 1 -q:v 2 out/sales-mobile-poster.jpg
