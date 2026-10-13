# VoiceNotes

> **Offline speech transcription and speaker diarization tool with a lightweight Windows Notepad-style interface.**

[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-brightgreen)](https://github.com)
[![Engine](https://img.shields.io/badge/Engine-Faster--Whisper-blue)](https://github.com)
[![Diarization](https://img.shields.io/badge/Diarization-CAM%2B%2B%20ONNX-orange)](https://github.com)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Cross--Platform-informational)](https://github.com)

VoiceNotes is a desktop speech-to-text application designed around a clean, familiar Windows Notepad interface. Open audio or video files or record directly from a microphone; VoiceNotes transcribes the speech, tags distinct speakers (diarization), and formats the output with clickable timestamps.

All processing runs locally on device once models are downloaded. No recordings or notes are sent to external servers.

---

## Features

- **Familiar Notepad Interface**:
  - Clean text editor with standard menus (File, Edit, Audio, Speech, View, Help).
  - **Inline Find and Replace (`Ctrl+F` / `Ctrl+H`)**: Search toolbar with match counts, case sensitivity toggle, Next/Previous navigation, and Replace All.
  - **Drag and Drop**: Drag audio or video files directly into the window to transcribe, or drop text/subtitle files to open.
  - Light and Dark modes matching Windows 11 aesthetics, including automatic synchronization with OS system theme settings.

- **Interactive Timestamps and Audio Playback**:
  - Each transcription segment includes a timecode (for example, `[00:14 - 00:17]`).
  - Clicking any timestamp seeks the built-in media player to that point in the audio and starts playback.
  - Real-time status bar updates as audio plays.

- **Speaker Diarization**:
  - Identifies and labels distinct speakers (`Speaker 1:`, `Speaker 2:`).
  - Uses offline CAM++ ONNX voice embeddings with hierarchical clustering.
  - Dedicated **Speakers Panel**: rename speakers across the entire note and preview audio snippets for each speaker.
  - Runs fully offline without Hugging Face tokens, gated model agreements, or third-party API keys.

- **Offline Transcription Engine**:
  - Powered by Faster-Whisper (CTranslate2) with local model caching.
  - Uses INT8 quantization for efficient execution on standard CPUs.
  - Automatically utilizes NVIDIA CUDA GPU acceleration when available.

- **Live Microphone Dictation and Recording**:
  - Low-latency (~250ms) streaming dictation directly into the document with concurrent refinement pass.
  - Microphone recording dialog with live timer.

- **Export Formats**:
  - **Plain Text (`.txt`)**: Clean text or formatted with timecodes and speaker tags.
  - **Subtitles (`.srt`, `.vtt`)**: SubRip and WebVTT formats for video players and editing software.
  - **Markdown (`.md`)**: Formatted notes with metadata summary table.
  - **JSON (`.json`)**: Structured output including timestamps and segment metadata.

- **Standalone Executable**:
  - Can be packaged into a standalone distribution with PyInstaller.
  - Runs on target systems without requiring a Python installation.

---

## Quick Start

### Prerequisites
- Windows 10/11, macOS, or Linux
- [uv](https://docs.astral.sh/uv/) (recommended) or Python 3.10+

### Option A: One-Click Run (Windows)
Double-click `run.bat` or run in PowerShell:
```powershell
.\run.ps1
```

### Option B: Using `uv`
```powershell
# Clone the repository
git clone <repo-url>
cd voicenotes

# Run the desktop application
uv run python main.py
```

---

## Test Audio Samples

VoiceNotes includes test audio files in the `samples/` directory:

| Sample File | Speakers | Duration | Description |
| :--- | :---: | :---: | :--- |
| `two_speakers_conversation.wav` | 2 | 30.0s | Conversational dialogue (Diane & Sheila) for testing speaker diarization. |
| `jfk.flac` | 1 | 11.0s | Historic speech ("Ask not what your country can do..."). |
| `single_mic_male.wav` | 1 | 3.3s | Studio microphone recording (male voice). |
| `single_mic_female.flac` | 1 | 2.1s | Studio microphone recording (female voice). |

### Testing via the GUI
1. Launch VoiceNotes (`run.bat` or `uv run python main.py`).
2. Go to **Help** -> **Load Test Audio Clip** -> select `Two Speakers Conversation (30s)`.
3. Ensure **Detect speakers** is enabled.
4. Click **Transcribe**.
5. Click any timestamp in the text to jump to that moment in the audio.

### Testing via the Command Line (CLI)
Transcribe directly from the terminal in headless mode:
```powershell
# Transcribe two-speaker conversation with diarization
uv run python main.py samples/two_speakers_conversation.wav --cli --speakers 2

# Transcribe single-speaker audio with tiny model and export to SRT
uv run python main.py samples/jfk.flac --cli --model tiny -o jfk.srt
```

---

## Building the Standalone Executable

To generate a standalone executable folder for distribution:

1. Run the build script:
   ```powershell
   uv run python build_executable.py
   ```
2. The bundled application is generated in:
   ```
   dist/VoiceNotes/VoiceNotes.exe
   ```
3. Distribute the `dist/VoiceNotes` directory. Target machines can run `VoiceNotes.exe` without Python installed.

---

## Project Structure

```
voicenotes/
├── voicenotes/
│   ├── __init__.py
│   ├── app.py                     # Application entry point (GUI and CLI modes)
│   ├── config.py                  # Settings, paths, and model metadata
│   ├── engine/
│   │   ├── audio_utils.py         # Audio loading, resampling, feature extraction, recording
│   │   ├── diarizer.py            # Offline CAM++ ONNX speaker diarization and clustering
│   │   ├── model_manager.py       # Offline model management and downloader
│   │   └── transcriber.py         # Faster-Whisper transcription engine
│   ├── export/
│   │   └── exporters.py           # TXT, SRT, VTT, JSON, and Markdown exporters
│   └── gui/
│       ├── audio_player.py        # Audio playback widget with timeline seek
│       ├── dialogs.py             # Settings, Recording, and About dialogs
│       ├── find_bar.py            # Inline Find & Replace toolbar
│       ├── main_window.py         # Main Notepad-style window
│       ├── speakers_panel.py      # Speaker management panel with inline rename
│       ├── styles.py              # Windows Light and Dark theme stylesheets
│       └── transcription_worker.py# Background QThread workers for transcription
├── samples/                       # Test audio clips
│   ├── two_speakers_conversation.wav
│   ├── jfk.flac
│   ├── single_mic_male.wav
│   └── single_mic_female.flac
├── tests/                         # Automated test suite (31 tests)
│   ├── test_engine.py
│   ├── test_exporters.py
│   └── test_gui.py
├── scripts/
│   ├── capture_e2e_screenshots.py # E2E visual inspection runner
│   └── download_models.py         # Pre-download models for offline distribution
├── build_executable.py            # Builds standalone VoiceNotes.exe
├── VoiceNotes.spec                # PyInstaller specification
├── run.bat                        # Windows batch launcher
├── run.ps1                        # PowerShell launcher
├── pyproject.toml                 # Project metadata and dependencies
└── README.md                      # Documentation
```

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + N` | New Note |
| `Ctrl + O` | Open Text File |
| `Ctrl + S` | Save Note |
| `Ctrl + Shift + S` | Save Note As... |
| `Ctrl + Shift + O` | Open Audio or Video File |
| `Ctrl + R` | Record / Dictate from Microphone |
| `Ctrl + F` | Find in Note |
| `Ctrl + H` | Replace in Note |
| `F3` / `Shift + F3` | Find Next / Previous |
| `F5` | Transcribe Loaded Audio |
| `Ctrl + P` / `Space` | Play / Pause Audio |
| `Ctrl + Left` | Skip Back 5 Seconds |
| `Ctrl + Right` | Skip Forward 5 Seconds |
| `Ctrl + Shift + C` | Copy Plain Text (without timestamps) |
| `Ctrl + =` / `Ctrl + -` | Zoom In / Zoom Out (Font Size) |
| `Ctrl + ,` | Settings & Offline Models Catalog |

---

## Privacy and Offline Operation

VoiceNotes operates locally on the host machine:
- No network requests are made during audio playback, recording, transcription, or editing.
- Models are stored locally in `./models/` or the user configuration directory.
- No third-party accounts, APIs, or telemetry are required or included.

---

## License

MIT License. Open source and free for personal and commercial use.
