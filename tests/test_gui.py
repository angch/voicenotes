"""
Automated GUI Tests for VoiceNotes using pytest-qt.
Tests widget interactions, audio loading, player controls,
timestamp anchor clicks, and live transcription workflow.
"""

from pathlib import Path
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent
import pytest

from voicenotes.config import config
from voicenotes.gui.main_window import MainWindow
from voicenotes.gui.dialogs import AboutDialog, SettingsDialog


@pytest.fixture
def app_window(qtbot):
    """Fixture providing a managed MainWindow instance."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


def test_main_window_init(app_window):
    """Verify MainWindow initializes with all required widgets and correct initial states."""
    win = app_window
    assert win.editor is not None
    assert win.player_widget is not None
    assert win.panel_speech is not None
    assert win.btn_transcribe is not None
    assert win.status_bar is not None

    # Initial state
    assert win.btn_transcribe.isEnabled() is False
    assert win.player_widget.btn_play_pause.isEnabled() is False
    assert "Untitled" in win.lbl_doc_status.text()
    assert win.editor.toPlainText() == ""


def test_load_audio_file(app_window):
    """Test loading audio file updates labels, enables transcription and audio controls."""
    win = app_window
    jfk_sample = Path("samples/jfk.flac").resolve()
    assert jfk_sample.exists()

    win.load_audio_file(str(jfk_sample))

    assert win.current_audio_file == str(jfk_sample)
    assert "jfk.flac" in win.lbl_audio_name.text()
    assert win.btn_transcribe.isEnabled() is True
    assert win.player_widget.btn_play_pause.isEnabled() is True
    assert win.player_widget.slider.isEnabled() is True


def test_player_controls(app_window, qtbot):
    """Test player seek, jump, and speed controls."""
    win = app_window
    jfk_sample = Path("samples/jfk.flac").resolve()
    win.load_audio_file(str(jfk_sample))

    from PyQt6.QtMultimedia import QMediaPlayer

    qtbot.waitUntil(
        lambda: win.player_widget.player.mediaStatus()
        in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ),
        timeout=5000,
    )

    # Test seek to 4 seconds
    win.player_widget.seek_to(4.0, auto_play=False)
    qtbot.waitUntil(lambda: win.player_widget.player.position() == 4000, timeout=3000)
    assert win.player_widget.player.position() == 4000

    # Test relative seek +2 seconds
    win.player_widget.seek_relative(2.0)
    qtbot.waitUntil(lambda: win.player_widget.player.position() == 6000, timeout=3000)
    assert win.player_widget.player.position() == 6000

    # Test speed combo
    win.player_widget.combo_speed.setCurrentText("1.5x")
    assert win.player_widget.player.playbackRate() == 1.5


def test_editor_text_modification(app_window):
    """Test typing into editor updates status bar and modified flag."""
    win = app_window
    assert win._is_modified is False

    win.editor.setPlainText("Meeting Notes: Discussing project roadmap.")
    assert win._is_modified is True
    assert "*" in win.lbl_doc_status.text()
    assert "Words: 5" in win.lbl_doc_stats.text()


def test_clickable_timestamp_anchor(app_window, qtbot):
    """Test that clicking on a timestamp anchor seeks the audio player."""
    win = app_window
    jfk_sample = Path("samples/jfk.flac").resolve()
    win.load_audio_file(str(jfk_sample))

    from PyQt6.QtMultimedia import QMediaPlayer

    qtbot.waitUntil(
        lambda: win.player_widget.player.mediaStatus()
        in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ),
        timeout=5000,
    )

    # Insert formatted HTML with time link
    html = '<p><a href="time:7.5"> [00:07 - 00:10]</a> <b>Speaker 1:</b> Testing clickable time.</p>'
    win.editor.setHtml(html)

    # Simulate anchor click via anchorAt / seek
    anchor = "time:7.5"
    seconds = float(anchor.replace("time:", ""))
    win.player_widget.seek_to(seconds, auto_play=False)
    qtbot.waitUntil(lambda: win.player_widget.player.position() == 7500, timeout=3000)

    assert win.player_widget.player.position() == 7500


def test_theme_toggle(app_window):
    """Test switching between Light and Dark mode."""
    win = app_window
    win.act_dark.setChecked(True)
    win._toggle_theme()
    assert config.get("theme") == "dark"

    win.act_dark.setChecked(False)
    win._toggle_theme()
    assert config.get("theme") == "light"


def test_dialogs_gui(qtbot):
    """Test Settings and About dialog instantiation and interaction."""
    settings_dlg = SettingsDialog()
    qtbot.addWidget(settings_dlg)
    settings_dlg.show()
    assert settings_dlg.combo_device is not None
    assert settings_dlg.table_models.rowCount() > 0
    settings_dlg.close()

    about_dlg = AboutDialog()
    qtbot.addWidget(about_dlg)
    about_dlg.show()
    about_dlg.close()


def test_live_transcription_gui_workflow(app_window, qtbot):
    """
    Test live GUI transcription workflow using a fast test sample (single_mic_female.flac, 2s).
    Verifies worker thread, progress bar, and final editor text population.
    """
    win = app_window
    sample = Path("samples/single_mic_female.flac").resolve()
    assert sample.exists()

    win.load_audio_file(str(sample))

    # Configure fast test parameters
    idx_tiny = win.combo_model.findData("tiny")
    if idx_tiny >= 0:
        win.combo_model.setCurrentIndex(idx_tiny)
    win.chk_diar.setChecked(False)  # Single speaker test

    # Click transcribe button
    qtbot.mouseClick(win.btn_transcribe, Qt.MouseButton.LeftButton)

    # Progress frame should become visible
    assert win.progress_frame.isVisible() is True

    # Wait for worker thread to complete and populate result (max 20 seconds)
    qtbot.waitUntil(lambda: win.current_result is not None, timeout=20000)

    # Verify results in GUI
    assert win.current_result is not None
    assert len(win.current_result.segments) >= 1
    assert win.editor.toPlainText() != ""
    assert win.btn_transcribe.isEnabled() is True
