"""
Speakers Panel widget for VoiceNotes.
Displays detected speakers with turn counts, audio sample playback,
and inline editing to rename speakers across the entire transcript.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from voicenotes.engine.audio_utils import format_timestamp


# Distinct palette colors for up to 8 speakers
SPEAKER_COLORS = [
    ("#0067c0", "#e7f3ff"),  # Blue
    ("#087f5b", "#ebfbee"),  # Green
    ("#d9480f", "#fff4e6"),  # Orange
    ("#7048e8", "#f3f0ff"),  # Purple
    ("#c2255c", "#fff0f6"),  # Pink
    ("#1098ad", "#e6fcf5"),  # Teal
    ("#f08c00", "#fff9db"),  # Yellow
    ("#495057", "#f1f3f5"),  # Gray
]


class SpeakerCard(QFrame):
    """Card representing a single speaker with rename input and audio sample button."""

    renamed = pyqtSignal(str, str)  # (old_name, new_name)
    play_sample = pyqtSignal(float)  # (first_turn_start_seconds)

    def __init__(
        self,
        speaker_name: str,
        color_idx: int,
        turn_count: int,
        total_duration: float,
        first_turn_start: float,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.speaker_name = speaker_name
        self.first_turn_start = first_turn_start

        fg_color, bg_color = SPEAKER_COLORS[color_idx % len(SPEAKER_COLORS)]

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"""
            SpeakerCard {{
                background-color: {bg_color};
                border: 1px solid #d0d0d0;
                border-left: 4px solid {fg_color};
                border-radius: 6px;
                margin-bottom: 6px;
            }}
            """
        )

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(6)

        # Row 1: Editable name + Sample play button
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self.edit_name = QLineEdit(speaker_name)
        self.edit_name.setStyleSheet(
            f"""
            QLineEdit {{
                font-weight: 600;
                font-size: 13px;
                color: {fg_color};
                background: #ffffff;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 3px 6px;
            }}
            QLineEdit:focus {{
                border-color: {fg_color};
            }}
            """
        )
        self.edit_name.setToolTip("Click to rename this speaker throughout the notes")
        self.edit_name.editingFinished.connect(self._on_rename_finished)
        row1.addWidget(self.edit_name, stretch=1)

        self.btn_sample = QPushButton("▶")
        self.btn_sample.setToolTip("Listen to a sample of this speaker")
        self.btn_sample.setFixedSize(26, 26)
        self.btn_sample.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {fg_color};
                color: #ffffff;
                border: none;
                border-radius: 13px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            """
        )
        self.btn_sample.clicked.connect(lambda: self.play_sample.emit(self.first_turn_start))
        row1.addWidget(self.btn_sample)

        card_layout.addLayout(row1)

        # Row 2: Stats (turns, speaking time)
        dur_str = format_timestamp(total_duration)
        turns_text = f"{turn_count} {'turn' if turn_count == 1 else 'turns'} ({dur_str})"
        self.lbl_stats = QLabel(turns_text)
        self.lbl_stats.setStyleSheet("font-size: 11px; color: #555555;")
        card_layout.addWidget(self.lbl_stats)

    def _on_rename_finished(self):
        new_name = self.edit_name.text().strip()
        if new_name and new_name != self.speaker_name:
            old_name = self.speaker_name
            self.speaker_name = new_name
            self.renamed.emit(old_name, new_name)


class SpeakersPanel(QWidget):
    """
    Panel displaying all detected speakers in the current transcript,
    enabling click-to-rename and audio sample previews.
    """

    speaker_renamed = pyqtSignal(str, str)  # (old_name, new_name)
    play_speaker_sample = pyqtSignal(float)  # (seconds)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumWidth(210)
        self.setMaximumWidth(320)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 2)
        self.lbl_title = QLabel("👥 Speakers")
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 13px; color: #333333;")
        header.addWidget(self.lbl_title)

        self.lbl_count = QLabel("(0)")
        self.lbl_count.setStyleSheet("font-size: 12px; color: #777777;")
        header.addWidget(self.lbl_count)
        header.addStretch()

        layout.addLayout(header)

        # Scroll Area for Speaker Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(2, 2, 2, 2)
        self.cards_layout.setSpacing(4)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_placeholder = QLabel(
            "Speakers will appear here after transcribing with 'Detect speakers'."
        )
        self.lbl_placeholder.setWordWrap(True)
        self.lbl_placeholder.setStyleSheet(
            "color: #888888; font-style: italic; font-size: 12px; padding: 12px 4px;"
        )
        self.cards_layout.addWidget(self.lbl_placeholder)

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, stretch=1)

    def clear(self):
        """Reset speakers panel to empty placeholder state."""
        # Remove all existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.lbl_placeholder = QLabel(
            "Speakers will appear here after transcribing with 'Detect speakers'."
        )
        self.lbl_placeholder.setWordWrap(True)
        self.lbl_placeholder.setStyleSheet(
            "color: #888888; font-style: italic; font-size: 12px; padding: 12px 4px;"
        )
        self.cards_layout.addWidget(self.lbl_placeholder)
        self.lbl_count.setText("(0)")

    def update_speakers(self, segments: List[any]):
        """Populate panel with speakers detected across segments."""
        # Clear existing
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Compute stats per speaker
        speaker_stats: Dict[str, Dict[str, any]] = {}
        speaker_order: List[str] = []

        for seg in segments:
            spk = getattr(seg, "speaker", None)
            if not spk:
                continue

            if spk not in speaker_stats:
                speaker_order.append(spk)
                speaker_stats[spk] = {
                    "turn_count": 0,
                    "total_duration": 0.0,
                    "first_turn_start": seg.start,
                }
            speaker_stats[spk]["turn_count"] += 1
            speaker_stats[spk]["total_duration"] += max(0.0, seg.end - seg.start)

        if not speaker_order:
            self.lbl_placeholder = QLabel(
                "No distinct speakers detected."
            )
            self.lbl_placeholder.setStyleSheet("color: #888888; font-style: italic; font-size: 12px; padding: 12px 4px;")
            self.cards_layout.addWidget(self.lbl_placeholder)
            self.lbl_count.setText("(0)")
            return

        self.lbl_count.setText(f"({len(speaker_order)})")

        for idx, spk in enumerate(speaker_order):
            stats = speaker_stats[spk]
            card = SpeakerCard(
                speaker_name=spk,
                color_idx=idx,
                turn_count=stats["turn_count"],
                total_duration=stats["total_duration"],
                first_turn_start=stats["first_turn_start"],
            )
            card.renamed.connect(self.speaker_renamed.emit)
            card.play_sample.connect(self.play_speaker_sample.emit)
            self.cards_layout.addWidget(card)
