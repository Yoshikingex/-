#!/usr/bin/env bash
# Scroll-scrub encodes: short GOP so seeking backward/forward is instant.
# desktop = landscape 16:9 master, mobile = portrait 9:16 master
set -euo pipefail
land=${1:-out/hero-master.mp4}
port=${2:-out/hero-master-portrait.mp4}
ffmpeg -v error -y -i "$land" -an -vf "unsharp=5:5:0.5:5:5:0.0" \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -g 8 -keyint_min 8 -sc_threshold 0 -movflags +faststart out/hero-desktop.mp4
ffmpeg -v error -y -i "$port" -an -vf "scale=720:-2,unsharp=5:5:0.4:5:5:0.0" \
  -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p -g 4 -keyint_min 4 -sc_threshold 0 -movflags +faststart out/hero-mobile.mp4
ffmpeg -v error -y -ss 0 -i out/hero-desktop.mp4 -frames:v 1 -q:v 2 out/hero-poster.jpg
ffmpeg -v error -y -ss 0 -i out/hero-mobile.mp4 -frames:v 1 -q:v 2 out/hero-mobile-poster.jpg
