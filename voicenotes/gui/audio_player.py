"""
Integrated Audio Player Widget for VoiceNotes with scrub bar,
playback speed selector, and instant timestamp jump capabilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QTime, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from voicenotes.engine.audio_utils import format_timestamp


class AudioPlayerWidget(QWidget):
    """
    Compact horizontal audio playback bar with scrub slider,
    play/pause, skip forward/backward, and playback rate options.
    """

    position_changed = pyqtSignal(float)  # Emits current position in seconds

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_file: Optional[str] = None
        self._duration_ms: int = 0
        self._is_seeking: bool = False

        self._setup_player()
        self._init_ui()

    def _setup_player(self) -> None:
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        self._pending_seek_ms: Optional[int] = None

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # Skip Back 5s
        self.btn_skip_back = QPushButton("⏪ -5s")
        self.btn_skip_back.setToolTip("Jump back 5 seconds (Ctrl+Left)")
        self.btn_skip_back.clicked.connect(lambda: self.seek_relative(-5.0))
        self.btn_skip_back.setEnabled(False)
        layout.addWidget(self.btn_skip_back)

        # Play / Pause button
        self.btn_play_pause = QPushButton("▶ Play")
        self.btn_play_pause.setObjectName("playButton")
        self.btn_play_pause.setMinimumWidth(80)
        self.btn_play_pause.setToolTip("Play / Pause (Space / Ctrl+P)")
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_play_pause.setEnabled(False)
        layout.addWidget(self.btn_play_pause)

        # Skip Forward 5s
        self.btn_skip_fwd = QPushButton("+5s ⏩")
        self.btn_skip_fwd.setToolTip("Jump forward 5 seconds (Ctrl+Right)")
        self.btn_skip_fwd.clicked.connect(lambda: self.seek_relative(5.0))
        self.btn_skip_fwd.setEnabled(False)
        layout.addWidget(self.btn_skip_fwd)

        # Timeline scrub slider
        from PyQt6.QtCore import Qt

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.setEnabled(False)
        layout.addWidget(self.slider, stretch=1)

        # Time label (00:00 / 00:00)
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setMinimumWidth(90)
        from PyQt6.QtCore import Qt

        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_time)

        # Speed selector
        self.combo_speed = QComboBox()
        self.combo_speed.setToolTip("Playback Speed")
        self.combo_speed.setMinimumWidth(75)
        for speed in ["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"]:
            self.combo_speed.addItem(speed)
        self.combo_speed.setCurrentText("1.0x")
        self.combo_speed.currentTextChanged.connect(self._on_speed_changed)
        layout.addWidget(self.combo_speed)

    def load_file(self, file_path: str) -> None:
        """Load an audio file into the player."""
        self._current_file = file_path
        self._pending_seek_ms = None
        url = QUrl.fromLocalFile(file_path)
        self.player.setSource(url)
        self.btn_play_pause.setEnabled(True)
        self.btn_skip_back.setEnabled(True)
        self.btn_skip_fwd.setEnabled(True)
        self.slider.setEnabled(True)
        self.btn_play_pause.setText("▶ Play")

    def play(self) -> None:
        if self._current_file:
            self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def toggle_play_pause(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()

    def seek_to(self, seconds: float, auto_play: bool = True) -> None:
        """Jump to a specific second in the audio."""
        if not self._current_file:
            return
        target_ms = max(0, int(seconds * 1000))
        if self.player.mediaStatus() in (
            QMediaPlayer.MediaStatus.NoMedia,
            QMediaPlayer.MediaStatus.LoadingMedia,
        ):
            self._pending_seek_ms = target_ms
        else:
            self.player.setPosition(target_ms)

        if auto_play and self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.play()

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            if self._pending_seek_ms is not None:
                self.player.setPosition(self._pending_seek_ms)
                self._pending_seek_ms = None

    def seek_relative(self, delta_seconds: float) -> None:
        """Jump relative to current position."""
        curr_sec = self.player.position() / 1000.0
        self.seek_to(curr_sec + delta_seconds, auto_play=False)

    def _on_speed_changed(self, text: str) -> None:
        try:
            rate = float(text.replace("x", ""))
            self.player.setPlaybackRate(rate)
        except ValueError:
            pass

    def _on_position_changed(self, position_ms: int) -> None:
        if not self._is_seeking and self._duration_ms > 0:
            val = int((position_ms / self._duration_ms) * 1000)
            self.slider.setValue(val)

        curr_sec = position_ms / 1000.0
        total_sec = self._duration_ms / 1000.0
        self.lbl_time.setText(f"{format_timestamp(curr_sec)} / {format_timestamp(total_sec)}")
        self.position_changed.emit(curr_sec)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        total_sec = duration_ms / 1000.0
        self.lbl_time.setText(f"00:00 / {format_timestamp(total_sec)}")

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play_pause.setText("⏸ Pause")
        else:
            self.btn_play_pause.setText("▶ Play")

    def _on_slider_pressed(self) -> None:
        self._is_seeking = True

    def _on_slider_moved(self, value: int) -> None:
        if self._duration_ms > 0:
            pos_ms = int((value / 1000.0) * self._duration_ms)
            curr_sec = pos_ms / 1000.0
            total_sec = self._duration_ms / 1000.0
            self.lbl_time.setText(f"{format_timestamp(curr_sec)} / {format_timestamp(total_sec)}")

    def _on_slider_released(self) -> None:
        if self._duration_ms > 0:
            pos_ms = int((self.slider.value() / 1000.0) * self._duration_ms)
            self.player.setPosition(pos_ms)
        self._is_seeking = False
