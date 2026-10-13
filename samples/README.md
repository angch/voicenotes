# VoiceNotes Test Audio Samples

This folder contains pre-packaged audio clips designed to test offline speech recognition and speaker diarization across diverse audio conditions:

| File | Speakers | Duration | Description | Key Test Purpose |
| :--- | :---: | :---: | :--- | :--- |
| `two_speakers_conversation.wav` | 2 | 30.0s | Real two-person telephone dialogue with turn-taking (Diane & Sheila). | Tests multi-speaker identification and speaker diarization clustering. |
| `jfk.flac` | 1 | 11.0s | Classic presidential speech ("Ask not what your country can do for you..."). | Tests clean single-speaker transcription accuracy and word alignment. |
| `single_mic_male.wav` | 1 | 3.3s | Clean studio microphone recording (male voice). | Tests short phrase latency and clean audio recognition. |
| `single_mic_female.flac` | 1 | 2.1s | Clean studio microphone recording (female voice). | Tests quick speech burst transcription. |

## How to Test in VoiceNotes

1. **In the GUI**:
   - Open VoiceNotes.
   - Go to `Help` -> `Load Test Audio Clip` -> Select any sample clip.
   - Click **▶ Transcribe**.
   - Notice how timestamps are clickable in the editor, jumping the audio player to that exact moment!

2. **From the Command Line**:
   ```powershell
   uv run python main.py samples/two_speakers_conversation.wav --cli --speakers 2
   ```
