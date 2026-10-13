"""
E2E Visual Testing & Screenshot Capture for VoiceNotes.
Drives the application through all key interactive states and saves
high-resolution screenshots for visual UI/UX inspection.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication

from voicenotes.config import config
from voicenotes.engine.transcriber import TranscriptionResult, TranscriptionSegment
from voicenotes.gui.dialogs import AboutDialog, SendVoiceDialog, SettingsDialog
from voicenotes.gui.main_window import MainWindow
from voicenotes.gui.styles import create_palette, get_stylesheet


def capture_widget(widget, output_path: Path):
    """Render and grab a clean PNG image of the widget."""
    widget.show()
    widget.raise_()
    widget.activateWindow()
    QApplication.processEvents()
    QApplication.processEvents()

    pix = widget.grab()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(output_path), "PNG")
    print(f"Captured: {output_path.name} ({pix.width()}x{pix.height()})")


def create_sample_result() -> TranscriptionResult:
    """Create a realistic two-speaker conversational result."""
    segments = [
        TranscriptionSegment(
            id=1,
            start=1.68,
            end=3.48,
            text="How long is this project going to take, Sheila?",
            speaker="Speaker 1",
        ),
        TranscriptionSegment(
            id=2,
            start=3.68,
            end=5.50,
            text="I'm not quite sure. Diane, what do you think?",
            speaker="Speaker 2",
        ),
        TranscriptionSegment(
            id=3,
            start=5.60,
            end=7.80,
            text="We should be able to wrap up the transcription engine by Thursday.",
            speaker="Speaker 1",
        ),
        TranscriptionSegment(
            id=4,
            start=8.00,
            end=11.20,
            text="Excellent. Make sure offline diarization and 250ms streaming are tested.",
            speaker="Speaker 2",
        ),
        TranscriptionSegment(
            id=5,
            start=11.40,
            end=14.10,
            text="The test suite passed all thirty-one tests without issues.",
            speaker="Speaker 1",
        ),
    ]
    sample_wav = Path("samples/two_speakers_conversation.wav").resolve()
    return TranscriptionResult(
        audio_path=str(sample_wav) if sample_wav.exists() else "conversation.wav",
        duration=14.5,
        language="en",
        language_probability=0.99,
        segments=segments,
        model_name="small",
        num_speakers=2,
        diarization_enabled=True,
    )


def main():
    app = QApplication(sys.argv)
    output_dir = Path("screenshots").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Main Window Light - Empty Initial State
    config.set("theme", "light")
    win = MainWindow()
    win.resize(1060, 720)
    capture_widget(win, output_dir / "01_main_window_light_empty.png")

    # 2. Main Window Dark - Empty Initial State
    config.set("theme", "dark")
    win._set_theme("dark")
    capture_widget(win, output_dir / "02_main_window_dark_empty.png")

    # 3. Main Window Light - Populated with Audio and Transcribed Dialogue
    config.set("theme", "light")
    win._set_theme("light")
    sample_wav = Path("samples/two_speakers_conversation.wav").resolve()
    if sample_wav.exists():
        win.load_audio_file(str(sample_wav))

    sample_result = create_sample_result()
    win.current_result = sample_result
    win._render_transcript_html(sample_result)
    win.speakers_panel.update_speakers(sample_result.segments)
    capture_widget(win, output_dir / "03_main_window_light_with_transcript.png")

    # 4. Main Window Dark - Populated with Transcript
    config.set("theme", "dark")
    win._set_theme("dark")
    capture_widget(win, output_dir / "04_main_window_dark_with_transcript.png")

    # 5. Inline Find & Replace Bar Active
    win.find_bar.show_replace(initial_query="transcription")
    capture_widget(win, output_dir / "05_find_replace_bar_active.png")
    win.find_bar.hide()

    # 6. Live Streaming Dictation State (with live in-progress ~250ms draft line)
    win._is_recording = True
    win.btn_record.setText("⏹ Stop Recording")
    win.btn_record.setStyleSheet(
        "QPushButton { background-color: #d9383a; color: #ffffff; font-weight: bold; padding: 4px 10px; border-radius: 4px; border: 1px solid #b32d2f; }"
    )
    win.progress_frame.setVisible(True)
    win.lbl_progress.setText("🔴 Listening live... (~250ms dual-pass real-time)")
    win._live_committed_segments = sample_result.segments[:3]
    win._live_draft_start = 7.9
    win._live_draft_text = "and we are testing the live real-time draft hypothesis"
    win._render_live_dictation()
    capture_widget(win, output_dir / "06_live_streaming_draft_dark.png")

    # Also in Light Mode
    win._set_theme("light")
    capture_widget(win, output_dir / "06_live_streaming_draft_light.png")

    win._is_recording = False
    win.progress_frame.setVisible(False)
    win.close()

    # 7. Settings Dialog - Light Mode
    config.set("theme", "light")
    app.setPalette(create_palette("light"))
    app.setStyleSheet(get_stylesheet("light"))
    settings_dlg = SettingsDialog()
    settings_dlg.resize(580, 520)
    capture_widget(settings_dlg, output_dir / "07_settings_dialog_light.png")
    settings_dlg.close()

    # 8. Settings Dialog - Dark Mode
    config.set("theme", "dark")
    app.setPalette(create_palette("dark"))
    app.setStyleSheet(get_stylesheet("dark"))
    settings_dlg = SettingsDialog()
    settings_dlg.resize(580, 520)
    capture_widget(settings_dlg, output_dir / "08_settings_dialog_dark.png")
    settings_dlg.close()

    # 9. About Dialog - Light Mode
    config.set("theme", "light")
    app.setPalette(create_palette("light"))
    app.setStyleSheet(get_stylesheet("light"))
    about_dlg = AboutDialog()
    about_dlg.resize(460, 360)
    capture_widget(about_dlg, output_dir / "09_about_dialog.png")
    about_dlg.close()

    # 10. About Dialog - Dark Mode
    config.set("theme", "dark")
    app.setPalette(create_palette("dark"))
    app.setStyleSheet(get_stylesheet("dark"))
    about_dlg = AboutDialog()
    about_dlg.resize(460, 360)
    capture_widget(about_dlg, output_dir / "10_about_dialog_dark.png")
    about_dlg.close()

    # 11. Send Voice Dialog - Light Mode
    config.set("theme", "light")
    app.setPalette(create_palette("light"))
    app.setStyleSheet(get_stylesheet("light"))
    send_dlg = SendVoiceDialog(
        audio_path=str(sample_wav) if sample_wav.exists() else None,
        transcript_text=sample_result.plain_text,
        transcript_result=sample_result,
    )
    send_dlg.edit_notes.setPlainText("Transcription test clip with 2 speakers. Some background noise near 0:04.")
    send_dlg.resize(560, 530)
    capture_widget(send_dlg, output_dir / "11_send_voice_dialog_light.png")
    send_dlg.close()

    # 12. Send Voice Dialog - Dark Mode
    config.set("theme", "dark")
    app.setPalette(create_palette("dark"))
    app.setStyleSheet(get_stylesheet("dark"))
    send_dlg_dark = SendVoiceDialog(
        audio_path=str(sample_wav) if sample_wav.exists() else None,
        transcript_text=sample_result.plain_text,
        transcript_result=sample_result,
    )
    send_dlg_dark.edit_notes.setPlainText("Transcription test clip with 2 speakers. Some background noise near 0:04.")
    send_dlg_dark.resize(560, 530)
    capture_widget(send_dlg_dark, output_dir / "12_send_voice_dialog_dark.png")
    send_dlg_dark.close()

    print("\nAll screenshots generated successfully in screenshots/")


if __name__ == "__main__":
    main()
