#!/usr/bin/env bash
# VoiceNotes macOS double-clickable launcher
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
exec ./run.sh "$@"
