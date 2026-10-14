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

- **Offline Transcription & Hardware Acceleration**:
  - Powered by Faster-Whisper (CTranslate2) with local model caching.
  - Automatically detects NVIDIA CUDA GPUs (e.g. GeForce RTX) with FP16 Tensor Core acceleration.
  - Seamless fallback to optimized CPU execution with INT8 quantization when no GPU is present.

- **Audio Compression & Archival**:
  - Compresses audio recordings into lightweight `.ogg` (Opus) or `.mp3` format (up to ~88% reduction vs WAV).
  - **Archive Voice Note Package (`Ctrl+Shift+Z`)**: Exports a single `.zip` bundle containing compressed audio, formatted transcript, and metadata.
  - **Send Voice for Tuning**: Packages debug metadata and compressed voice audio for model and diarization quality tuning.

- **Live Microphone Dictation and Recording**:
  - Low-latency (~250ms) streaming dictation directly into the document with concurrent refinement pass.
  - Microphone recording dialog with live timer.

- **Export Formats**:
  - **Plain Text (`.txt`)**: Clean text or formatted with timecodes and speaker tags.
  - **Subtitles (`.srt`, `.vtt`)**: SubRip and WebVTT formats for video players and editing software.
  - **Markdown (`.md`)**: Formatted notes with metadata summary table.
  - **JSON (`.json`)**: Structured output including timestamps and segment metadata.
  - **Archival Zip (`.zip`)**: Note package bundling transcript, metadata, and compressed audio.

- **Standalone Executable**:
  - Can be packaged into a standalone distribution with PyInstaller.
  - Runs on target systems without requiring a Python installation.

---

## Quick Start

### Prerequisites
- Linux (Ubuntu 22.04 / 24.04+, Debian 11/12), macOS (Apple Silicon M1–M4 or Intel), or Windows 10/11
- [uv](https://docs.astral.sh/uv/) (recommended) or Python 3.10+

### Option A: One-Click Run (Linux & macOS)
Run in terminal:
```bash
./run.sh
```
*On Linux, `run.sh` automatically detects whether you are running under **Wayland** or **X11**, configures the appropriate Qt platform plugins, preloads bundled PortAudio/XCB libraries, and initializes NVIDIA CUDA or AMD ROCm GPU acceleration if present.*

### Option B: One-Click Run (Windows)
Double-click `run.bat` or run in PowerShell:
```powershell
.\run.ps1
```

### Option C: Using `uv` (Cross-Platform)
```bash
# Clone the repository
git clone <repo-url>
cd voicenotes

# Run the desktop application
uv run python main.py

# Or inspect system and GPU acceleration diagnostics
uv run python main.py --info
```

---

## Linux Support: Ubuntu / Debian

VoiceNotes provides complete, native support for modern Linux distributions (tested on Ubuntu 24.04 LTS Noble Numbat and Debian 12):

- **Display Server Compatibility**: Native **Wayland** (`wayland;xcb`) with seamless fallback to **X11** (`xcb`).
- **Zero-Crash Qt 6 Experience**: Bundles `libxcb-cursor.so.0` and `libportaudio.so.2` inside the package, preventing common `xcb` startup crashes on fresh Ubuntu 24.04 installations without requiring root intervention.
- **Hardware Acceleration Out of the Box**:
  - **CPU INT8**: Parallelized OpenMP vector compute; guaranteed to run fast on all modern x86_64 processors.
  - **NVIDIA CUDA**: Automatic discovery of cuBLAS and cuDNN libraries (`CUDA 11/12`) with FP16 Tensor Core acceleration.
  - **AMD ROCm**: Automatic detection of HIP runtime (`libamdhip64.so`), `/dev/kfd`, and ROCm execution providers.
  - Verify your active GPU and display engine at any time with:
    ```bash
    voicenotes --info
    # or
    voicenotes-gpu-check
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
1. Launch VoiceNotes (`./run.sh`, `run.bat`, or `uv run python main.py`).
2. Go to **Help** -> **Load Test Audio Clip** -> select `Two Speakers Conversation (30s)`.
3. Ensure **Detect speakers** is enabled.
4. Click **Transcribe**.
5. Click any timestamp in the text to jump to that moment in the audio.

### Testing via the Command Line (CLI)
Transcribe directly from the terminal in headless mode:
```bash
# Transcribe two-speaker conversation with diarization
uv run python main.py samples/two_speakers_conversation.wav --cli --speakers 2

# Transcribe single-speaker audio with tiny model and export to SRT
uv run python main.py samples/jfk.flac --cli --model tiny -o jfk.srt

# Print system diagnostics and active hardware acceleration engine
uv run python main.py --info
```

---

## Building Standalone Executables & Debian (.deb) Packages

VoiceNotes includes automated scripts to package the entire project into self-contained distributions requiring zero Python on the target machine.

### 1. Build Standalone Executable (All Platforms)
```bash
uv run python build_executable.py
```
Outputs:
- **Linux**: Standalone directory in `dist/VoiceNotes/` with relocatable `VoiceNotes` binary.
- **macOS**: `dist/VoiceNotes.app` application bundle and `dist/VoiceNotes.dmg` disk image.
- **Windows**: `dist/VoiceNotes/VoiceNotes.exe` portable folder and Inno Setup installer.

### 2. Build Debian / Ubuntu (.deb) Packages

VoiceNotes offers two packaging strategies to accommodate diverse deployment needs:

#### Strategy 1: Single All-in-One Package (Recommended for easy offline installation)
Bundles the complete desktop application, Python runtime, pre-downloaded offline models (Whisper & CAM++), and acceleration libraries into a single file:
```bash
uv run python scripts/build_deb.py --mode all-in-one
```
Install on any Ubuntu/Debian machine:
```bash
sudo dpkg -i dist/voicenotes_0.5.1_all-in-one_amd64.deb
```

#### Strategy 2: Two Split Packages (Alternative for modular updates)
Separates the application/Python code from the larger neural network models and acceleration files:
- **Package 1 (`voicenotes_0.5.1_amd64.deb` / `voicenotes-app_...deb`)**: Contains the application binary, GUI/CLI, desktop entry, icons, and audio samples (~370 MB).
- **Package 2 (`voicenotes-models-accel_0.5.1_amd64.deb`)**: Contains the offline Whisper speech models, CAM++ ONNX speaker diarization models, and GPU acceleration configurations (~220 MB).

Build both split packages:
```bash
uv run python scripts/build_deb.py --mode split
```
Install both together:
```bash
sudo dpkg -i dist/voicenotes_0.5.1_amd64.deb dist/voicenotes-models-accel_0.5.1_amd64.deb
```

#### Strategy 3: Generate All Packages at Once
```bash
uv run python build_executable.py --deb both
# or
uv run python scripts/build_deb.py --mode both
```
All `.deb` artifacts are placed in `dist/`. Fast `gzip` compression is used by default; pass `--compression xz` or `--compression zstd` if maximum archive compression is desired.

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
├── assets/                        # High-resolution application icons (PNG, ICNS, ICO)
│   ├── app_icon.icns              # macOS Apple Icon Image
│   ├── app_icon.ico               # Windows multi-size icon
│   └── app_icon.png
├── tests/                         # Automated test suite (52 tests)
│   ├── test_engine.py
│   ├── test_exporters.py
│   ├── test_gui.py
│   └── test_vocabulary.py
├── scripts/
│   ├── capture_e2e_screenshots.py # E2E visual inspection runner
│   ├── download_models.py         # Pre-download models for offline distribution
│   └── eval_malaysian_speech.py   # Accuracy benchmarking
├── build_executable.py            # Standalone builder (VoiceNotes.app, DMG, or VoiceNotes.exe)
├── VoiceNotes.spec                # Cross-platform PyInstaller specification
├── VoiceNotes.iss                 # Inno Setup Windows installer specification
├── run.sh                         # macOS and Linux launcher script
├── run.command                    # macOS double-clickable Finder launcher
├── run.bat                        # Windows batch launcher
├── run.ps1                        # PowerShell launcher
├── pyproject.toml                 # Project metadata and dependencies
└── README.md                      # Documentation
```

---

## Keyboard Shortcuts

> **Note for macOS users**: The `Ctrl` modifier automatically maps to `Cmd` (`⌘`) on macOS (e.g. `Cmd + S` to save, `Cmd + O` to open, `Cmd + F` to find).

| Shortcut (Win / Linux) | Shortcut (macOS) | Action |
| :--- | :--- | :--- |
| `Ctrl + N` | `Cmd + N` | New Note |
| `Ctrl + O` | `Cmd + O` | Open Text File |
| `Ctrl + S` | `Cmd + S` | Save Note |
| `Ctrl + Shift + S` | `Cmd + Shift + S` | Save Note As... |
| `Ctrl + Shift + Z` | `Cmd + Shift + Z` | Archive Voice Note Package (.zip) |
| `Ctrl + Shift + O` | `Cmd + Shift + O` | Open Audio or Video File |
| `Ctrl + R` | `Cmd + R` | Record / Dictate from Microphone |
| `Ctrl + F` | `Cmd + F` | Find in Note |
| `Ctrl + H` | `Cmd + H` | Replace in Note |
| `F3` / `Shift + F3` | `F3` / `Shift + F3` | Find Next / Previous |
| `F5` | `F5` | Transcribe Loaded Audio |
| `Ctrl + P` / `Space` | `Cmd + P` / `Space` | Play / Pause Audio |
| `Ctrl + Left` | `Cmd + Left` | Skip Back 5 Seconds |
| `Ctrl + Right` | `Cmd + Right` | Skip Forward 5 Seconds |
| `Ctrl + Shift + C` | `Cmd + Shift + C` | Copy Plain Text (without timestamps) |
| `Ctrl + =` / `Ctrl + -` | `Cmd + =` / `Cmd + -` | Zoom In / Zoom Out (Font Size) |
| `Ctrl + ,` | `Cmd + ,` | Settings & Offline Models Catalog |

---

## Privacy and Offline Operation

VoiceNotes operates locally on the host machine:
- No network requests are made during audio playback, recording, transcription, or editing.
- Models are stored locally in `./models/` or the user configuration directory.
- No third-party accounts, APIs, or telemetry are required or included.

---

## License

MIT License. Open source and free for personal and commercial use.
