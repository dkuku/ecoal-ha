#!/usr/bin/env bash
# Syncs current SPA web files into esp32/data for LittleFS upload

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$REPO_DIR/custom_components/ecoal/www"
DEST_DIR="$SCRIPT_DIR/data"

mkdir -p "$DEST_DIR"

echo "Syncing $SRC_DIR -> $DEST_DIR..."
cp -v "$SRC_DIR"/*.html "$DEST_DIR/"
cp -v "$SRC_DIR"/*.css "$DEST_DIR/"
cp -v "$SRC_DIR"/*.js "$DEST_DIR/"

echo "Success! Files in $DEST_DIR ready for ESP32 LittleFS Data Upload:"
ls -lh "$DEST_DIR"
