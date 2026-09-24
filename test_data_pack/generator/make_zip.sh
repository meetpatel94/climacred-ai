#!/usr/bin/env bash
# Build ClimaCred_AI_Test_Data_Pack.zip (TESTING ARTEFACT - not application code).
# Run after: build_test_data.py -> validate_test_data.py -> build_readme.py
set -euo pipefail

PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="ClimaCred_AI_Test_Data_Pack"
OUT="$PACK_DIR/$NAME.zip"
STAGE="$(mktemp -d)"
mkdir -p "$STAGE/$NAME"

# workbooks + documents at the pack root
cp "$PACK_DIR"/*.xlsx "$STAGE/$NAME/"
cp "$PACK_DIR"/README_TESTING_GUIDE.md "$PACK_DIR"/VALIDATION_REPORT.md \
   "$PACK_DIR"/VALIDATION_REPORT.csv "$PACK_DIR"/MANIFEST.csv "$STAGE/$NAME/"

# machine-readable copies, POST-ready payloads and the build scripts
cp -r "$PACK_DIR/csv" "$STAGE/$NAME/csv"
cp -r "$PACK_DIR/api_payloads" "$STAGE/$NAME/api_payloads"
mkdir -p "$STAGE/$NAME/generator"
cp "$PACK_DIR"/generator/*.py "$PACK_DIR"/generator/make_zip.sh "$STAGE/$NAME/generator/"

rm -f "$OUT"
( cd "$STAGE" && zip -q -r "$OUT" "$NAME" )
rm -rf "$STAGE"

echo "wrote $OUT"
unzip -l "$OUT" | tail -3
