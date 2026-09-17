#!/bin/bash

# Script to generate preview.gif locally using VHS
# Requirements: vhs, ffmpeg, ttyd, and JetBrains Mono font

set -e

# Check if VHS is installed
if ! command -v vhs &> /dev/null; then
    echo "Error: VHS is not installed"
    echo "Install it with: go install github.com/charmbracelet/vhs@latest"
    exit 1
fi

# Check if commander-toolbox binary exists
if ! command -v commander-toolbox &> /dev/null && [ ! -f "./build/commander-toolbox" ] && [ ! -f "./target/release/commander-toolbox" ]; then
    echo "Error: commander-toolbox binary not found"
    echo "Build it first with: cargo build --release"
    exit 1
fi

# Add commander-toolbox to PATH if needed
if [ -f "./target/release/commander-toolbox" ]; then
    export PATH="$PWD/target/release:$PATH"
elif [ -f "./build/commander-toolbox" ]; then
    export PATH="$PWD/build:$PATH"
fi

echo "Generating preview.gif..."
cd .github
vhs preview.tape

echo "✓ Preview generated successfully at .github/preview.gif"
