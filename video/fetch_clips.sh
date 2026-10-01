#!/usr/bin/env bash
# 生成済みの元カット(8本)を Higgsfield から再取得する（clips/ は容量節約のため git 管理外）
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p clips
base=$(python3 -c "import json;print(json.load(open('manifest.json'))['clip_base_url'])")
python3 -c "import json;[print(k,v) for k,v in json.load(open('manifest.json'))['clips'].items()]" |
while read -r name file; do curl -sS -o "clips/$name.mp4" "$base$file"; echo "clips/$name.mp4"; done
