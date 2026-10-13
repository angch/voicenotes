@echo off
title VoiceNotes - Offline Transcriber
cd /d "%~dp0"

echo Starting VoiceNotes...

REM If virtual environment exists, run using virtual environment
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" main.py %*
    exit /b 0
)

REM If portable build exists in dist, run standalone executable
if exist "dist\VoiceNotes\VoiceNotes.exe" (
    start "" "dist\VoiceNotes\VoiceNotes.exe" %*
    exit /b 0
)

REM Fallback to system uv or python
where uv >nul 2>&1
if %errorlevel% equ 0 (
    uv run python main.py %*
    exit /b 0
)

python main.py %*
