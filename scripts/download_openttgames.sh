#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$ROOT_DIR/datasets/OpenTTGames"
BASE_URL="https://lab.osai.ai/datasets/openttgames/data"
MODE="${1:-quick}"

mkdir -p "$DATA_DIR/markup" "$DATA_DIR/videos" "$DATA_DIR/markup_extracted"

markup_files=(
  game_1.zip game_2.zip game_3.zip game_4.zip game_5.zip
  test_1.zip test_2.zip test_3.zip test_4.zip test_5.zip test_6.zip test_7.zip
)

quick_videos=(game_1.mp4 test_2.mp4)
full_videos=(
  game_1.mp4 game_2.mp4 game_3.mp4 game_4.mp4 game_5.mp4
  test_1.mp4 test_2.mp4 test_3.mp4 test_4.mp4 test_5.mp4 test_6.mp4 test_7.mp4
)

for f in "${markup_files[@]}"; do
  echo "[download] $f"
  curl -L --fail --retry 3 --continue-at - "$BASE_URL/$f" -o "$DATA_DIR/markup/$f"
done

if [[ "$MODE" == "full" ]]; then
  videos=("${full_videos[@]}")
else
  videos=("${quick_videos[@]}")
fi

for f in "${videos[@]}"; do
  echo "[download] $f"
  curl -L --fail --retry 3 --continue-at - "$BASE_URL/$f" -o "$DATA_DIR/videos/$f"
done

for z in "$DATA_DIR"/markup/*.zip; do
  name="$(basename "$z" .zip)"
  mkdir -p "$DATA_DIR/markup_extracted/$name"
  unzip -o -q "$z" -d "$DATA_DIR/markup_extracted/$name"
done

echo "OpenTTGames pronto em: $DATA_DIR"
