# PowerShell Launcher for VoiceNotes
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Starting VoiceNotes..." -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    Start-Process ".venv\Scripts\python.exe" -ArgumentList "main.py"
    exit 0
}

if (Test-Path "dist\VoiceNotes\VoiceNotes.exe") {
    Start-Process "dist\VoiceNotes\VoiceNotes.exe"
    exit 0
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run python main.py
    exit 0
}

python main.py
