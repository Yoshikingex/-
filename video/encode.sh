#!/usr/bin/env bash
# Scroll-scrub encodes: short GOP so seeking backward/forward is instant.
set -euo pipefail
in=${1:-out/hero-master.mp4}
ffmpeg -v error -y -i "$in" -an -vf "unsharp=5:5:0.5:5:5:0.0" \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -g 8 -keyint_min 8 -sc_threshold 0 -movflags +faststart out/hero-desktop.mp4
ffmpeg -v error -y -i "$in" -an -vf "scale=-2:720,unsharp=5:5:0.4:5:5:0.0" \
  -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p -g 4 -keyint_min 4 -sc_threshold 0 -movflags +faststart out/hero-mobile.mp4
ffmpeg -v error -y -ss 0 -i out/hero-desktop.mp4 -frames:v 1 -q:v 2 out/hero-poster.jpg
ffmpeg -v error -y -ss 0 -i out/hero-mobile.mp4 -frames:v 1 -q:v 2 out/hero-mobile-poster.jpg
