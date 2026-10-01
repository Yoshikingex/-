#!/usr/bin/env bash
# 4カット(各5秒)を結合して、通常版とスクロール用(全フレームキーフレーム)版を作る
# 使い方: bash build_video.sh 16x9   /   bash build_video.sh 9x16
set -euo pipefail
cd "$(dirname "$0")"
AR="${1:-16x9}"
if [ "$AR" = "16x9" ]; then FULL="1920:1080"; SCRUB="1280:720"; else FULL="1080:1920"; SCRUB="720:1280"; fi
C=clips
D=0.35   # 場面のつなぎ目の「白い光」フェード秒数
norm="fps=24,scale=${FULL}:force_original_aspect_ratio=increase,crop=${FULL},setsar=1,trim=0:5,setpts=PTS-STARTPTS"

ffmpeg -loglevel error -y \
  -i $C/c1_$AR.mp4 -i $C/c2_$AR.mp4 -i $C/c3_$AR.mp4 -i $C/c4_$AR.mp4 \
  -filter_complex "\
[0:v]$norm,eq=saturation=0.6:contrast=1.03,colorbalance=bs=0.06:bm=0.04,fade=t=out:st=$(echo "5-$D-0.15"|bc):d=$D:color=white[v1];\
[1:v]$norm,fade=t=in:st=0:d=$D:color=white,fade=t=out:st=$(echo "5-$D"|bc):d=$D:color=white[v2];\
[2:v]$norm,fade=t=in:st=0:d=$D:color=white,fade=t=out:st=$(echo "5-$D"|bc):d=$D:color=white[v3];\
[3:v]$norm,eq=saturation=1.08,fade=t=in:st=0:d=$D:color=white[v4];\
[v1][v2][v3][v4]concat=n=4:v=1:a=0,format=yuv420p[out]" \
  -map "[out]" -an -c:v libx264 -preset slow -crf 18 -profile:v high -movflags +faststart \
  seitai_hero_${AR}.mp4

# スクロール用: 全フレームをキーフレーム化(逆再生・シークでもカクつかない)、軽量解像度
ffmpeg -loglevel error -y -i seitai_hero_${AR}.mp4 \
  -vf "scale=${SCRUB}" -an -c:v libx264 -preset slow -crf 24 -g 1 -keyint_min 1 -sc_threshold 0 \
  -pix_fmt yuv420p -movflags +faststart seitai_hero_${AR}_scrub.mp4

for f in seitai_hero_${AR}.mp4 seitai_hero_${AR}_scrub.mp4; do
  printf "%s\t%s bytes\t" "$f" "$(wc -c < "$f")"
  ffprobe -v error -select_streams v:0 -count_frames \
    -show_entries stream=width,height,r_frame_rate,nb_read_frames:format=duration -of csv=p=0 "$f" | tr '\n' ' '; echo
done
