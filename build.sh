#!/usr/bin/env bash
# Validate both packs and package them as importable .mcpack files in a .mcaddon.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$SCRIPT_DIR/Cursed-Contraptions.mcaddon"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

printf '%s\n' "=== Cursed Contraptions v0.1.5 Build ==="
python3 "$SCRIPT_DIR/tests/validate_build.py"

printf '\n%s\n' "Packaging behavior and resource packs..."
(
  cd "$SCRIPT_DIR/behavior_pack"
  zip -X -q -r "$TEMP_DIR/Cursed-Contraptions_BP.mcpack" . -x '*.DS_Store' '__pycache__/*'
)
(
  cd "$SCRIPT_DIR/resource_pack"
  zip -X -q -r "$TEMP_DIR/Cursed-Contraptions_RP.mcpack" . -x '*.DS_Store' '__pycache__/*'
)

rm -f "$OUTPUT"
(
  cd "$TEMP_DIR"
  zip -X -q "$OUTPUT" Cursed-Contraptions_BP.mcpack Cursed-Contraptions_RP.mcpack
)

python3 "$SCRIPT_DIR/tests/validate_build.py" --package "$OUTPUT"
printf '\n%s\n' "Build complete: $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
