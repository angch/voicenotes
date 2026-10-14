#!/usr/bin/env bash
# VoiceNotes macOS & Linux launcher
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "Starting VoiceNotes..."

# 1. If virtual environment exists, run using virtual environment
if [ -f ".venv/bin/python" ]; then
    exec ".venv/bin/python" main.py "$@"
fi

# 2. If uv is installed, run with uv
if command -v uv >/dev/null 2>&1; then
    exec uv run python main.py "$@"
fi

# 3. If macOS app bundle exists in dist, launch it (GUI mode)
if [ -d "dist/VoiceNotes.app" ] && [ "$(uname)" = "Darwin" ] && [ $# -eq 0 ]; then
    open "dist/VoiceNotes.app"
    exit 0
fi

# 4. If standalone binary exists in dist, run it
if [ -f "dist/VoiceNotes/VoiceNotes" ]; then
    exec "dist/VoiceNotes/VoiceNotes" "$@"
fi

# 5. Fallback to system python3
exec python3 main.py "$@"
