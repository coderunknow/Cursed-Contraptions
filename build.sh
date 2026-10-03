#!/bin/bash
#
# Cursed Contraptions — Build Script
# Packages the add-on into a distributable .mcaddon file.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Cursed Contraptions Build ==="

# Run validation first
echo "Running validation..."
python3 tests/validate_build.py

if [ $? -ne 0 ]; then
    echo "❌ Validation failed. Fix errors before building."
    exit 1
fi

echo ""
echo "Packaging add-on..."

# Clean previous build
rm -f Cursed-Contraptions.mcaddon
rm -f behavior_pack.zip resource_pack.zip

# Package behavior pack
cd behavior_pack
zip -rq ../behavior_pack.zip . -x "*.DS_Store" -x "__pycache__/*"
cd ..

# Package resource pack
cd resource_pack
zip -rq ../resource_pack.zip . -x "*.DS_Store" -x "__pycache__/*"
cd ..

# Combine into .mcaddon
zip -q Cursed-Contraptions.mcaddon behavior_pack.zip resource_pack.zip

# Clean up intermediate files
rm -f behavior_pack.zip resource_pack.zip

SIZE=$(ls -lh Cursed-Contraptions.mcaddon | awk '{print $5}')

echo ""
echo "✅ Build complete!"
echo "   File: Cursed-Contraptions.mcaddon"
echo "   Size: $SIZE"
echo ""
echo "Install by double-clicking the .mcaddon file or dragging it into Minecraft."
