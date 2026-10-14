# Changelog

All notable changes to VoiceNotes are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.5.0] - 2026-10-14

### Added
- **Linux Platform Support (Ubuntu & Debian)**:
  - Full compatibility verified on Ubuntu 24.04 LTS (Noble Numbat), Ubuntu 22.04 LTS, and Debian 11/12.
  - Native **Wayland** (`wayland;xcb`) support with seamless fallback to **X11** (`xcb`).
  - Bundled essential Linux runtime libraries (`libxcb-cursor.so.0` and `libportaudio.so.2` in `voicenotes/lib/`) with automatic `ctypes.CDLL` preloading, resolving Qt 6 xcb startup crashes and missing PortAudio recording dependencies out of the box without requiring root privileges.
- **Hardware Acceleration Out of the Box**:
  - **CPU INT8**: Optimized OpenMP parallelized vector execution active on all x86_64 processors.
  - **NVIDIA CUDA**: Automatic cuBLAS, cuDNN, and CUDA 11/12 library discovery and Tensor Core FP16 execution.
  - **AMD ROCm / HIP**: Kernel node (`/dev/kfd`), runtime (`libamdhip64.so`), and ONNX Runtime `ROCMExecutionProvider` / `MIGraphXExecutionProvider` detection with automatic CPU fallback.
  - Diagnostics CLI flag: `voicenotes --info` and `voicenotes-gpu-check` helper.
- **Debian (.deb) Packaging Pipeline (`scripts/build_deb.py`)**:
  - **Strategy 1 (All-in-One)**: Single self-contained `.deb` package (`voicenotes_0.5.0_all-in-one_amd64.deb`) bundling the application, Python runtime, pre-downloaded offline models (Whisper & CAM++), and acceleration wrappers for offline environments.
  - **Strategy 2 (Split Packages)**: Modular dual `.deb` distribution:
    - `voicenotes_0.5.0_amd64.deb` (Application code, GUI/CLI, desktop files, samples, ~370 MB)
    - `voicenotes-models-accel_0.5.0_amd64.deb` (Neural models & acceleration configs, ~220 MB)
  - Zero file collision between split packages with mutual `Recommends:` metadata.
  - Integrated with `build_executable.py --deb [all-in-one|split|both]`.

### Changed
- Relocatable path discovery in `voicenotes/config.py`: models and samples now support explicit environment variables (`VOICENOTES_MODELS_DIR`, `VOICENOTES_SAMPLES_DIR`) and prefix discovery relative to `sys.executable`.
- Launcher script `/usr/bin/voicenotes` detects runtime prefix dynamically and configures `LD_LIBRARY_PATH` and display plugins automatically.

---

## [0.4.0] - 2026-10-14

### Added
- **Native macOS Support**:
  - Application bundle (`dist/VoiceNotes.app`) and Apple disk image installer (`dist/VoiceNotes.dmg`).
  - Native Cocoa `NSProcessInfo` / `NSBundle` integration for system menu bar branding (`VoiceNotes`).
  - Multi-resolution Apple Icon Image (`assets/app_icon.icns`).
  - Terminal (`run.sh`) and Finder (`run.command`) launchers.
  - Apple Silicon M-series (NEON INT8) hardware acceleration detection.
- **Dark Mode & Styling**:
  - High-contrast transcript text rendering for dark themes.
  - Dynamic re-theming support for live palette transitions.

---

## [0.3.0] - 2026-10-14

### Added
- **Custom Vocabulary & Spelling Replacement**:
  - Preferred terms and domain-specific acronym replacement dictionary.
  - Retrospective transcript backfill (`Ctrl+Shift+B`).
  - Vocabulary import/export in JSON format.
- **Speech Engine Improvements**:
  - Anti-repetition decoding filters to suppress hallucinated loops on silent or noisy audio segments.
  - Benchmarking evaluation runner for accented and conversational speech.

---

## [0.2.0] - 2026-10-13

### Added
- **Speaker Diarization**:
  - Offline CAM++ ONNX speaker embedding model with agglomerative hierarchical clustering.
  - Dedicated Speakers Panel with batch renaming and audio snippet preview.
- **Interactive Timeline**:
  - Clickable segment timestamps seeking directly in the media player.

---

## [0.1.0] - 2026-10-12

### Initial Release
- Desktop speech-to-text Notepad interface with Faster-Whisper engine.
- Microphone recording, file transcription, live streaming dictation.
- Multi-format export: TXT, SRT, VTT, JSON, and Markdown.
