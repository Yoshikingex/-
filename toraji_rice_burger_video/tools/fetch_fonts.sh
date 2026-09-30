#!/usr/bin/env bash
# サムネ・仮編集で使う無料フォント（SIL Open Font License）を assets/fonts/ に取得する。
set -euo pipefail
cd "$(dirname "$0")/../assets" && mkdir -p fonts && cd fonts
BASE="https://cdn.jsdelivr.net/gh/google/fonts@main/ofl"
curl -sSL -o DelaGothicOne.ttf       "$BASE/delagothicone/DelaGothicOne-Regular.ttf"
curl -sSL -o NotoSansJP.ttf          "$BASE/notosansjp/NotoSansJP%5Bwght%5D.ttf"
curl -sSL -o ZenMaruGothic-Black.ttf "$BASE/zenmarugothic/ZenMaruGothic-Black.ttf"
ls -la
