#!/bin/bash
# Download static ffmpeg binary for Lambda (arm64/aarch64)
# Source: https://johnvansickle.com/ffmpeg/
# This bundles ffmpeg directly with the Lambda function - no layer needed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/src/bin"
FFMPEG_VERSION="release"  # Use latest release build

echo "Setting up ffmpeg for Lambda (arm64)..."
echo "Target directory: $BIN_DIR"

# Create bin directory
mkdir -p "$BIN_DIR"

# Check if ffmpeg already exists and is executable
if [[ -f "$BIN_DIR/ffmpeg" ]]; then
    # Check if it's the right architecture
    FILE_INFO=$(file "$BIN_DIR/ffmpeg" 2>/dev/null || echo "")
    if echo "$FILE_INFO" | grep -q "aarch64\|ARM"; then
        echo "ffmpeg (arm64) already exists at $BIN_DIR/ffmpeg"
        exit 0
    else
        echo "Existing ffmpeg is wrong architecture, re-downloading..."
        rm -f "$BIN_DIR/ffmpeg"
    fi
fi

# Download static ffmpeg build for ARM64 (aarch64)
# These are statically linked builds that work on Amazon Linux 2 (Lambda)
DOWNLOAD_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-${FFMPEG_VERSION}-arm64-static.tar.xz"
TEMP_DIR=$(mktemp -d)

echo "Downloading ffmpeg from $DOWNLOAD_URL..."
curl -L "$DOWNLOAD_URL" -o "$TEMP_DIR/ffmpeg.tar.xz"

echo "Extracting..."
cd "$TEMP_DIR"
tar xf ffmpeg.tar.xz

# Find and copy the ffmpeg binary
FFMPEG_DIR=$(find . -maxdepth 1 -type d -name "ffmpeg-*" | head -1)
if [[ -z "$FFMPEG_DIR" ]]; then
    echo "Error: Could not find ffmpeg directory in archive"
    exit 1
fi

cp "$FFMPEG_DIR/ffmpeg" "$BIN_DIR/ffmpeg"
chmod +x "$BIN_DIR/ffmpeg"

# Cleanup
rm -rf "$TEMP_DIR"

echo "ffmpeg (arm64) installed successfully!"
echo ""
echo "Binary location: $BIN_DIR/ffmpeg"
echo "Size: $(du -h "$BIN_DIR/ffmpeg" | cut -f1)"
echo "Architecture: $(file "$BIN_DIR/ffmpeg" | grep -o 'ARM\|aarch64' || echo 'arm64')"
