# 🎙️ VoiceNotes

> **Multiplatform Offline Speech Transcriber with Speaker Diarization — Designed as a Notepad Lite for non-technical users.**

[![Offline AI](https://img.shields.io/badge/Privacy-100%25%20Offline-brightgreen)](https://github.com)
[![Engine](https://img.shields.io/badge/Speech%20Engine-Faster--Whisper-blue)](https://github.com)
[![Diarization](https://img.shields.io/badge/Diarization-CAM%2B%2B%20ONNX-orange)](https://github.com)
[![OS](https://img.shields.io/badge/Platform-Windows%20First%20%7C%20Cross--Platform-informational)](https://github.com)

VoiceNotes is a simple, intuitive desktop speech-to-text tool that works like Windows Notepad with built-in voice superpowers. Open any audio/video file or record from your microphone, and VoiceNotes automatically transcribes the speech, tags different speakers (diarization), and formats the result with interactive, clickable timestamps.

**Zero cloud connection is required after downloading models. Your recordings and notes never leave your computer.**

---

## ✨ Features

- **📝 Familiar "Notepad Lite" Experience**:
  - Clean, unencumbered text editor with standard menus (File, Edit, Speech, Audio, View, Help).
  - Freely edit, correct typos, rename speaker labels, and take notes.
  - Light and Dark modes matching Windows 11 design.

- **⏱️ Interactive Clickable Timestamps**:
  - Every transcription block has a timestamp (e.g., `[00:14 - 00:17]`).
  - Clicking any timestamp instantly seeks the audio player to that exact moment and plays it!

- **👥 Multi-Speaker Tagging (Diarization)**:
  - Optionally labels different speakers (`Speaker 1:`, `Speaker 2:`...).
  - Uses offline **CAM++ ONNX** voice embeddings with hierarchical clustering.
  - No Hugging Face account, gated model agreements, or API tokens required.

- **⚡ Blazing Fast & Fully Offline**:
  - Powered by **Faster-Whisper** (CTranslate2 inference engine).
  - Uses INT8 quantization for fast execution on standard laptops and desktops without dedicated GPUs.
  - Automatically activates NVIDIA CUDA acceleration when available.

- **🎙️ Built-in Microphone Recording**:
  - One-click record modal with live timer.
  - Instantly transcribes when you finish speaking.

- **📤 Multi-Format Export**:
  - **Plain Text (`.txt`)**: Clean text or with timecoded speakers.
  - **Subtitles (`.srt` & `.vtt`)**: SubRip and WebVTT subtitle files for video editors and media players.
  - **Markdown (`.md`)**: Meeting notes document with metadata summary table.
  - **JSON (`.json`)**: Full structured output including word-level timestamps and confidence scores.

- **📦 Zero-Python Standalone Executable**:
  - Can be packaged into a standalone `VoiceNotes.exe` folder with PyInstaller.
  - Other machines can simply download and run without ever installing Python!

---

## 🚀 Quick Start (Running Locally)

### Prerequisites
- Windows 10/11 (or macOS / Linux)
- [uv](https://docs.astral.sh/uv/) (recommended) or Python 3.10+

### Option A: One-Click Run
Double-click `run.bat` or in PowerShell run:
```powershell
.\run.ps1
```

### Option B: Using `uv`
```powershell
# Clone the repository
git clone <repo-url>
cd voicenotes

# Run the desktop app
uv run python main.py
```

---

## 🎧 Included Test Audio Samples

VoiceNotes comes with pre-downloaded diverse test clips located in the `samples/` directory:

| Sample File | Speakers | Duration | Description |
| :--- | :---: | :---: | :--- |
| `two_speakers_conversation.wav` | 2 | 30.0s | Real telephone dialogue (Diane & Sheila) for testing speaker separation. |
| `jfk.flac` | 1 | 11.0s | Clear historic presidential speech ("Ask not what your country can do..."). |
| `single_mic_male.wav` | 1 | 3.3s | Clean studio microphone test (male voice). |
| `single_mic_female.flac` | 1 | 2.1s | Clean studio microphone test (female voice). |

### Testing via the GUI
1. Launch VoiceNotes (`run.bat` or `uv run python main.py`).
2. Go to **Help** -> **Load Test Audio Clip** -> choose `Two Speakers Conversation (30s)`.
3. Ensure **Detect Speakers** is checked.
4. Click **▶ Transcribe**.
5. Click any timestamp in the text to hear that specific person speaking!

### Testing via the Command Line (CLI)
You can also transcribe directly from the terminal:
```powershell
# Transcribe two-speaker conversation with diarization
uv run python main.py samples/two_speakers_conversation.wav --cli --speakers 2

# Transcribe single-speaker audio with tiny model and export to SRT
uv run python main.py samples/jfk.flac --cli --model tiny -o jfk.srt
```

---

## 📦 Creating the Zero-Python Standalone Executable

To share VoiceNotes with a non-technical user who does not have Python installed:

1. Run the build script:
   ```powershell
   uv run python build_executable.py
   ```
2. The self-contained application will be generated in:
   ```
   dist/VoiceNotes/VoiceNotes.exe
   ```
3. Distribute the `dist/VoiceNotes` folder (or zip it).
4. On any Windows computer, the user simply double-clicks `VoiceNotes.exe` to run!

---

## 📂 Project Structure

```
voicenotes/
├── voicenotes/
│   ├── __init__.py
│   ├── app.py                     # Application entry point (GUI & CLI modes)
│   ├── config.py                  # Settings, paths, and model metadata
│   ├── engine/
│   │   ├── audio_utils.py         # Audio loading, resampling, fbank extraction, recording
│   │   ├── diarizer.py            # Offline CAM++ ONNX speaker diarization & clustering
│   │   ├── model_manager.py       # Offline model storage and downloader
│   │   └── transcriber.py         # Faster-Whisper transcription engine
│   ├── export/
│   │   └── exporters.py           # TXT, SRT, VTT, JSON, and Markdown export
│   └── gui/
│       ├── audio_player.py        # Audio playback widget with timeline seek
│       ├── dialogs.py             # Settings, Recording, and About dialogs
│       ├── main_window.py         # "Notepad Lite" main window
│       ├── styles.py              # Light and Dark Windows themes
│       └── transcription_worker.py# Background QThread for non-blocking UI
├── samples/                       # Test audio clips and documentation
│   ├── two_speakers_conversation.wav
│   ├── jfk.flac
│   ├── single_mic_male.wav
│   └── single_mic_female.flac
├── tests/                         # Automated unit test suite
│   ├── test_engine.py
│   └── test_exporters.py
├── scripts/
│   └── download_models.py         # Pre-download models for offline distribution
├── build_executable.py            # Builds standalone VoiceNotes.exe
├── VoiceNotes.spec                # PyInstaller specification
├── run.bat                        # Windows 1-click batch launcher
├── run.ps1                        # PowerShell launcher
├── pyproject.toml                 # Project metadata and dependencies
└── README.md                      # Documentation
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + N` | New Blank Note |
| `Ctrl + O` | Open Text File |
| `Ctrl + S` | Save Note |
| `Ctrl + Shift + S` | Save Note As... |
| `Ctrl + Shift + O` | Open Audio or Video File |
| `Ctrl + R` | Record from Microphone |
| `F5` | Transcribe Loaded Audio |
| `Ctrl + P` / `Space` | Play / Pause Audio |
| `Ctrl + Left` | Skip Back 5 Seconds |
| `Ctrl + Right` | Skip Forward 5 Seconds |
| `Ctrl + Shift + C` | Copy Plain Text (without timestamps) |
| `Ctrl + =` / `Ctrl + -` | Zoom In / Zoom Out (Font Size) |
| `Ctrl + ,` | Settings & Offline Models Catalog |

---

## 🔒 Privacy & Offline Guarantee

VoiceNotes operates 100% locally on your machine.
- No network requests are made during audio playback, recording, transcription, or editing.
- Models are cached locally in `./models/` or your user directory.
- No third-party accounts, APIs, or telemetries are involved.

---

## 📄 License

MIT License. Open source and free for personal and commercial use.
