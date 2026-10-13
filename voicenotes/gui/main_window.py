"""
Main Window for VoiceNotes - Notepad Lite with Speech & Diarization Options.
Provides an editable text area with clickable timestamp audio playback,
audio file import, microphone recording, and multi-format export.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPoint, Qt, QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QTextCharFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voicenotes.config import (
    AVAILABLE_WHISPER_MODELS,
    SUPPORTED_LANGUAGES,
    config,
    get_samples_dir,
)
from voicenotes.engine.audio_utils import format_timestamp, parse_timestamp
from voicenotes.engine.model_manager import ModelManager
from voicenotes.engine.transcriber import (
    SpeechTranscriber,
    TranscriptionResult,
    TranscriptionSegment,
)
from voicenotes.export.exporters import (
    export_to_json,
    export_to_markdown,
    export_to_srt,
    export_to_txt,
    export_to_vtt,
    save_export_to_file,
)
from voicenotes.gui.audio_player import AudioPlayerWidget
from voicenotes.gui.dialogs import AboutDialog, RecordDialog, SettingsDialog
from voicenotes.gui.styles import get_stylesheet
from voicenotes.gui.speakers_panel import SPEAKER_COLORS, SpeakersPanel
from voicenotes.gui.transcription_worker import TranscriptionWorker


class NotepadTextEdit(QTextEdit):
    """
    Enhanced QTextEdit that acts like Notepad, while enabling
    direct click navigation for timestamps without disabling text editing.
    """

    timestamp_clicked = pyqtSlot(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._timestamp_regex = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*-\s*[^\]]+\]")

    def mousePressEvent(self, event: QMouseEvent):
        # Check if user clicked on an anchor link
        anchor = self.anchorAt(event.pos())
        if anchor and anchor.startswith("time:"):
            try:
                seconds = float(anchor.replace("time:", ""))
                # Find parent main window and seek
                main_win = self.window()
                if hasattr(main_win, "player_widget"):
                    main_win.player_widget.seek_to(seconds)
                return
            except ValueError:
                pass

        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """VoiceNotes Notepad Lite Main Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoiceNotes - Notepad Lite")
        self.resize(960, 680)

        self.transcriber = SpeechTranscriber()
        self.worker: Optional[TranscriptionWorker] = None
        self.current_result: Optional[TranscriptionResult] = None
        self.current_audio_file: Optional[str] = None
        self.current_text_file: Optional[str] = None
        self._is_modified: bool = False

        self._init_ui()
        self._apply_theme()
        self._update_status_bar()

    def _init_ui(self):
        # Central layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # Top Speech & Audio Panel
        self.panel_speech = QGroupBox("Speech & Audio Options")
        self.panel_speech.setObjectName("speechPanel")
        panel_layout = QVBoxLayout(self.panel_speech)
        panel_layout.setContentsMargins(10, 8, 10, 8)
        panel_layout.setSpacing(8)

        # Row 1: Source & Transcription Controls
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)

        self.btn_open_audio = QPushButton("📁 Open Audio")
        self.btn_open_audio.setToolTip("Open audio or video file (WAV, MP3, M4A, FLAC, MP4...)")
        self.btn_open_audio.clicked.connect(self._on_open_audio_dialog)
        row1_layout.addWidget(self.btn_open_audio)

        self.btn_record = QPushButton("🔴 Record")
        self.btn_record.setObjectName("recordButton")
        self.btn_record.setToolTip("Record speech from microphone")
        self.btn_record.clicked.connect(self._on_record_mic)
        row1_layout.addWidget(self.btn_record)

        # Audio file label
        self.lbl_audio_name = QLabel("No audio loaded")
        self.lbl_audio_name.setStyleSheet("color: #666; font-style: italic;")
        self.lbl_audio_name.setMinimumWidth(120)
        row1_layout.addWidget(self.lbl_audio_name, stretch=1)

        # Diarization toggle button ("Detect speakers")
        self.btn_detect_speakers = QPushButton("👥 Detect speakers")
        self.btn_detect_speakers.setCheckable(True)
        self.btn_detect_speakers.setChecked(config.get("diarization_enabled", True))
        self.btn_detect_speakers.setToolTip("Toggle offline speaker identification")
        self.btn_detect_speakers.toggled.connect(self._on_toggle_detect_speakers)
        row1_layout.addWidget(self.btn_detect_speakers)
        # Compatibility alias for chk_diar
        self.chk_diar = self.btn_detect_speakers
        self._update_detect_speakers_style()

        # Transcribe Action Button
        self.btn_transcribe = QPushButton("▶ Transcribe")
        self.btn_transcribe.setObjectName("primaryButton")
        self.btn_transcribe.setMinimumWidth(110)
        self.btn_transcribe.setToolTip("Transcribe loaded audio (F5)")
        self.btn_transcribe.setEnabled(False)
        self.btn_transcribe.clicked.connect(self._on_transcribe_clicked)
        row1_layout.addWidget(self.btn_transcribe)

        panel_layout.addLayout(row1_layout)

        # Row 2: Integrated Audio Player
        self.player_widget = AudioPlayerWidget(self)
        panel_layout.addWidget(self.player_widget)

        # Row 3: Progress Bar & Status (Hidden when idle)
        self.progress_frame = QFrame()
        prog_layout = QHBoxLayout(self.progress_frame)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(10)

        self.lbl_progress = QLabel("Ready")
        self.lbl_progress.setStyleSheet("font-weight: 500; color: #0067c0;")
        prog_layout.addWidget(self.lbl_progress)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar, stretch=1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel_transcription)
        prog_layout.addWidget(self.btn_cancel)

        self.progress_frame.setVisible(False)
        panel_layout.addWidget(self.progress_frame)

        main_layout.addWidget(self.panel_speech)

        # Splitter: Central Notepad Text Editor (Left) + Speakers Panel (Right)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.editor = NotepadTextEdit(self)
        self.editor.setFont(QFont("Consolas", config.get("font_size", 13)))
        self.editor.textChanged.connect(self._on_text_modified)
        self.splitter.addWidget(self.editor)

        self.speakers_panel = SpeakersPanel(self)
        self.speakers_panel.speaker_renamed.connect(self._on_speaker_renamed)
        self.speakers_panel.play_speaker_sample.connect(self._on_play_speaker_sample)
        self.splitter.addWidget(self.speakers_panel)

        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([720, 240])

        main_layout.addWidget(self.splitter, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.lbl_doc_status = QLabel("Untitled")
        self.lbl_doc_stats = QLabel("Lines: 1 | Words: 0 | Chars: 0")
        self.lbl_device_status = QLabel("⚡ Offline Ready (CPU INT8)")

        self.status_bar.addWidget(self.lbl_doc_status, 1)
        self.status_bar.addPermanentWidget(self.lbl_doc_stats)
        self.status_bar.addPermanentWidget(self.lbl_device_status)

        # Build menus after all controls and widgets exist
        self._create_menus()

    def _create_menus(self):
        menubar = self.menuBar()

        # --- File Menu ---
        menu_file = menubar.addMenu("&File")

        act_new = QAction("&New", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new_file)
        menu_file.addAction(act_new)

        act_open_txt = QAction("&Open Text File...", self)
        act_open_txt.setShortcut("Ctrl+O")
        act_open_txt.triggered.connect(self._on_open_text_file)
        menu_file.addAction(act_open_txt)

        act_save = QAction("&Save", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._on_save_file)
        menu_file.addAction(act_save)

        act_save_as = QAction("Save &As...", self)
        act_save_as.setShortcut("Ctrl+Shift+S")
        act_save_as.triggered.connect(self._on_save_as_file)
        menu_file.addAction(act_save_as)

        menu_file.addSeparator()

        # Export Submenu
        menu_export = menu_file.addMenu("&Export Transcript As")

        act_exp_srt = QAction("Subtitles (.srt)", self)
        act_exp_srt.triggered.connect(lambda: self._export_as("srt"))
        menu_export.addAction(act_exp_srt)

        act_exp_vtt = QAction("WebVTT (.vtt)", self)
        act_exp_vtt.triggered.connect(lambda: self._export_as("vtt"))
        menu_export.addAction(act_exp_vtt)

        act_exp_json = QAction("Structured Data (.json)", self)
        act_exp_json.triggered.connect(lambda: self._export_as("json"))
        menu_export.addAction(act_exp_json)

        act_exp_md = QAction("Markdown Notes (.md)", self)
        act_exp_md.triggered.connect(lambda: self._export_as("md"))
        menu_export.addAction(act_exp_md)

        menu_file.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # --- Edit Menu ---
        menu_edit = menubar.addMenu("&Edit")

        act_undo = QAction("&Undo", self)
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_undo.triggered.connect(self.editor.undo)
        menu_edit.addAction(act_undo)

        act_redo = QAction("&Redo", self)
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        act_redo.triggered.connect(self.editor.redo)
        menu_edit.addAction(act_redo)

        menu_edit.addSeparator()

        act_cut = QAction("Cu&t", self)
        act_cut.setShortcut(QKeySequence.StandardKey.Cut)
        act_cut.triggered.connect(self.editor.cut)
        menu_edit.addAction(act_cut)

        act_copy = QAction("&Copy", self)
        act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        act_copy.triggered.connect(self.editor.copy)
        menu_edit.addAction(act_copy)

        act_paste = QAction("&Paste", self)
        act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        act_paste.triggered.connect(self.editor.paste)
        menu_edit.addAction(act_paste)

        menu_edit.addSeparator()

        act_select_all = QAction("Select &All", self)
        act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_select_all.triggered.connect(self.editor.selectAll)
        menu_edit.addAction(act_select_all)

        act_copy_plain = QAction("Copy Plain Text (without timestamps)", self)
        act_copy_plain.setShortcut("Ctrl+Shift+C")
        act_copy_plain.triggered.connect(self._copy_plain_text)
        menu_edit.addAction(act_copy_plain)

        # --- Audio Menu ---
        menu_audio = menubar.addMenu("&Audio")

        act_open_audio = QAction("&Open Audio File...", self)
        act_open_audio.setShortcut("Ctrl+Shift+O")
        act_open_audio.triggered.connect(self._on_open_audio_dialog)
        menu_audio.addAction(act_open_audio)

        act_rec = QAction("&Record from Microphone...", self)
        act_rec.setShortcut("Ctrl+R")
        act_rec.triggered.connect(self._on_record_mic)
        menu_audio.addAction(act_rec)

        menu_audio.addSeparator()

        act_play_toggle = QAction("Play / Pause Audio", self)
        act_play_toggle.setShortcut("Ctrl+P")
        act_play_toggle.triggered.connect(self.player_widget.toggle_play_pause)
        menu_audio.addAction(act_play_toggle)

        act_skip_b = QAction("Skip Back 5s", self)
        act_skip_b.setShortcut("Ctrl+Left")
        act_skip_b.triggered.connect(lambda: self.player_widget.seek_relative(-5.0))
        menu_audio.addAction(act_skip_b)

        act_skip_f = QAction("Skip Forward 5s", self)
        act_skip_f.setShortcut("Ctrl+Right")
        act_skip_f.triggered.connect(lambda: self.player_widget.seek_relative(5.0))
        menu_audio.addAction(act_skip_f)

        # --- Speech Menu ---
        menu_speech = menubar.addMenu("&Speech")

        act_trans = QAction("&Transcribe Loaded Audio", self)
        act_trans.setShortcut("F5")
        act_trans.triggered.connect(self._on_transcribe_clicked)
        menu_speech.addAction(act_trans)

        menu_speech.addSeparator()

        act_settings = QAction("&Settings & Offline Models...", self)
        act_settings.setShortcut("Ctrl+,")
        act_settings.triggered.connect(self._on_open_settings)
        menu_speech.addAction(act_settings)

        # --- View Menu ---
        menu_view = menubar.addMenu("&View")

        self.act_speech_panel = QAction("Show Speech Options Panel", self)
        self.act_speech_panel.setCheckable(True)
        self.act_speech_panel.setChecked(True)
        self.act_speech_panel.triggered.connect(self._toggle_speech_panel)
        menu_view.addAction(self.act_speech_panel)

        self.act_speakers_panel = QAction("Show Speakers Panel", self)
        self.act_speakers_panel.setCheckable(True)
        self.act_speakers_panel.setChecked(True)
        self.act_speakers_panel.triggered.connect(self._toggle_speakers_panel)
        menu_view.addAction(self.act_speakers_panel)

        self.act_dark = QAction("&Dark Mode", self)
        self.act_dark.setCheckable(True)
        self.act_dark.setChecked(config.get("theme", "light") == "dark")
        self.act_dark.triggered.connect(self._toggle_theme)
        menu_view.addAction(self.act_dark)

        menu_view.addSeparator()

        act_font_inc = QAction("Zoom &In (Font Larger)", self)
        act_font_inc.setShortcut("Ctrl+=")
        act_font_inc.triggered.connect(self._increase_font)
        menu_view.addAction(act_font_inc)

        act_font_dec = QAction("Zoom &Out (Font Smaller)", self)
        act_font_dec.setShortcut("Ctrl+-")
        act_font_dec.triggered.connect(self._decrease_font)
        menu_view.addAction(act_font_dec)

        # --- Help Menu ---
        menu_help = menubar.addMenu("&Help")

        # Test samples submenu
        menu_samples = menu_help.addMenu("Load Test Audio Clip")
        samples_dir = get_samples_dir()
        if samples_dir.exists():
            sample_clips = [
                ("Two Speakers Conversation (30s)", "two_speakers_conversation.wav"),
                ("JFK Speech (Single Speaker 11s)", "jfk.flac"),
                ("Clean Male Voice (3s)", "single_mic_male.wav"),
                ("Clean Female Voice (2s)", "single_mic_female.flac"),
            ]
            for label, fname in sample_clips:
                path = samples_dir / fname
                if path.exists():
                    act_s = QAction(label, self)
                    act_s.triggered.connect(lambda checked, p=str(path): self.load_audio_file(p))
                    menu_samples.addAction(act_s)

        menu_help.addSeparator()

        act_about = QAction("&About VoiceNotes", self)
        act_about.triggered.connect(self._on_about)
        menu_help.addAction(act_about)

    def _apply_theme(self):
        theme = config.get("theme", "light")
        self.setStyleSheet(get_stylesheet(theme))

    def _toggle_theme(self):
        new_theme = "dark" if self.act_dark.isChecked() else "light"
        config.set("theme", new_theme)
        self._apply_theme()

    def _toggle_speech_panel(self):
        self.panel_speech.setVisible(self.act_speech_panel.isChecked())

    def _toggle_speakers_panel(self):
        self.speakers_panel.setVisible(self.act_speakers_panel.isChecked())

    def _on_toggle_detect_speakers(self, checked: bool):
        config.set("diarization_enabled", checked)
        self._update_detect_speakers_style()

    def _update_detect_speakers_style(self):
        checked = self.btn_detect_speakers.isChecked()
        if checked:
            self.btn_detect_speakers.setText("👥 Detect speakers: ON")
            self.btn_detect_speakers.setStyleSheet(
                "QPushButton { background-color: #e7f3ff; color: #0067c0; border: 1px solid #0067c0; font-weight: 600; padding: 4px 10px; border-radius: 4px; }"
            )
        else:
            self.btn_detect_speakers.setText("👥 Detect speakers: OFF")
            self.btn_detect_speakers.setStyleSheet(
                "QPushButton { background-color: #f1f3f5; color: #6c757d; border: 1px solid #ced4da; padding: 4px 10px; border-radius: 4px; }"
            )

    def _increase_font(self):
        font = self.editor.font()
        font.setPointSize(font.pointSize() + 1)
        self.editor.setFont(font)
        config.set("font_size", font.pointSize())

    def _decrease_font(self):
        font = self.editor.font()
        if font.pointSize() > 8:
            font.setPointSize(font.pointSize() - 1)
            self.editor.setFont(font)
            config.set("font_size", font.pointSize())

    def _on_text_modified(self):
        self._is_modified = True
        self._update_status_bar()

    def _update_status_bar(self):
        title = Path(self.current_text_file).name if self.current_text_file else "Untitled"
        if self._is_modified:
            title += " *"
        self.lbl_doc_status.setText(title)

        text = self.editor.toPlainText()
        lines = len(text.splitlines()) if text else 1
        words = len(text.split())
        chars = len(text)
        self.lbl_doc_stats.setText(f"Lines: {lines} | Words: {words} | Chars: {chars}")

    def load_audio_file(self, file_path: str):
        """Load an audio file into the player and prepare for transcription."""
        self.current_audio_file = file_path
        p = Path(file_path)
        self.lbl_audio_name.setText(f"{p.name} ({os.path.getsize(file_path)/(1024*1024):.1f} MB)")
        self.lbl_audio_name.setStyleSheet("color: #0067c0; font-weight: 500;")
        self.player_widget.load_file(file_path)
        self.btn_transcribe.setEnabled(True)

    def _on_open_audio_dialog(self):
        last_dir = config.get("last_open_folder", "")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio or Video File",
            last_dir,
            "Audio & Video Files (*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.webm *.mp4 *.mkv);;All Files (*.*)",
        )
        if file_path:
            config.set("last_open_folder", str(Path(file_path).parent))
            self.load_audio_file(file_path)

    def _on_record_mic(self):
        dlg = RecordDialog(self)
        if dlg.exec() == RecordDialog.DialogCode.Accepted and dlg.recorded_file:
            self.load_audio_file(dlg.recorded_file)

    def _on_transcribe_clicked(self):
        if not self.current_audio_file:
            return

        model_key = config.get("model", "small")
        lang_key = config.get("language", None)
        diarize = self.btn_detect_speakers.isChecked()

        # Update UI state
        self.btn_transcribe.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("Starting offline transcription...")

        # Clear editor and speakers panel
        self.editor.clear()
        self.speakers_panel.clear()

        # Start worker thread
        self.worker = TranscriptionWorker(
            transcriber=self.transcriber,
            audio_source=self.current_audio_file,
            model_name=model_key,
            language=lang_key,
            diarize=diarize,
            num_speakers="auto",
            parent=self,
        )
        self.worker.progress_updated.connect(self._on_worker_progress)
        self.worker.segment_ready.connect(self._on_worker_segment)
        self.worker.finished_success.connect(self._on_worker_finished)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_progress(self, msg: str, percent: int):
        self.lbl_progress.setText(msg)
        self.progress_bar.setValue(percent)

    def _on_worker_segment(self, seg: TranscriptionSegment):
        """Stream transcription segment directly into the notes in real-time."""
        is_dark = config.get("theme", "light") == "dark"
        ts_color = "#4dabf7" if is_dark else "#0067c0"
        text_color = "#f0f0f0" if is_dark else "#1a1a1a"

        ts_str = seg.timestamp_str
        start_sec = seg.start
        link_html = f'<a href="time:{start_sec:.2f}" style="color: {ts_color}; text-decoration: none; font-weight: bold; font-family: monospace;">{ts_str}</a>'
        text_html = f'<span style="color: {text_color};"> {seg.text.strip()}</span>'
        paragraph = f"<p style='margin: 4px 0;'>{link_html}{text_html}</p>"

        # Move cursor to end and insert HTML
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(paragraph)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self._update_status_bar()

    def _on_worker_finished(self, result: TranscriptionResult):
        self.current_result = result
        self.progress_bar.setValue(100)
        self.lbl_progress.setText("Transcription complete!")
        self.btn_transcribe.setEnabled(True)

        # Hide progress frame after brief pause
        QTimer.singleShot(1500, lambda: self.progress_frame.setVisible(False))

        # Re-render full result into rich HTML with clickable timestamps and speaker badges
        self._render_transcript_html(result)

        # Populate speakers panel
        if result.diarization_enabled:
            self.speakers_panel.update_speakers(result.segments)
        else:
            self.speakers_panel.clear()

    def _render_transcript_html(self, result: TranscriptionResult):
        """Render transcript with clickable timestamp anchors and speaker badges."""
        html_parts = []
        is_dark = config.get("theme", "light") == "dark"
        ts_color = "#4dabf7" if is_dark else "#0067c0"
        text_color = "#f0f0f0" if is_dark else "#1a1a1a"

        # Map speakers to distinct palette colors matching the speakers panel
        speaker_color_map = {}
        distinct_speakers = []
        for s in result.segments:
            if s.speaker and s.speaker not in distinct_speakers:
                distinct_speakers.append(s.speaker)
        for idx, spk in enumerate(distinct_speakers):
            fg, _ = SPEAKER_COLORS[idx % len(SPEAKER_COLORS)]
            speaker_color_map[spk] = fg

        for seg in result.segments:
            ts_str = seg.timestamp_str
            start_sec = seg.start
            link_html = f'<a href="time:{start_sec:.2f}" style="color: {ts_color}; text-decoration: none; font-weight: bold; font-family: monospace;">{ts_str}</a>'

            speaker_html = ""
            if result.diarization_enabled and seg.speaker:
                spk_col = speaker_color_map.get(seg.speaker, "#087f5b")
                speaker_html = f' <b style="color: {spk_col};">{seg.speaker}:</b>'

            content_html = f'<span style="color: {text_color};"> {seg.text.strip()}</span>'
            html_parts.append(f"<p style='margin: 4px 0;'>{link_html}{speaker_html}{content_html}</p>")

        self.editor.setHtml("".join(html_parts))
        self._is_modified = False
        self._update_status_bar()

    def _on_speaker_renamed(self, old_name: str, new_name: str):
        """Update speaker label across all segments and notes."""
        if not new_name or old_name == new_name:
            return

        if self.current_result:
            for seg in self.current_result.segments:
                if seg.speaker == old_name:
                    seg.speaker = new_name
            self._render_transcript_html(self.current_result)
        else:
            content = self.editor.toHtml()
            content = content.replace(f"{old_name}:", f"{new_name}:")
            self.editor.setHtml(content)

        self._is_modified = True
        self._update_status_bar()
        self.status_bar.showMessage(f"Renamed speaker '{old_name}' to '{new_name}'", 3000)

    def _on_play_speaker_sample(self, start_sec: float):
        """Play audio sample of the selected speaker."""
        if self.player_widget:
            self.player_widget.seek_to(start_sec, auto_play=True)

    def _on_worker_error(self, err_msg: str):
        self.progress_frame.setVisible(False)
        self.btn_transcribe.setEnabled(True)
        QMessageBox.critical(self, "Transcription Error", f"An error occurred during transcription:\n{err_msg}")

    def _on_cancel_transcription(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.terminate()
            self.lbl_progress.setText("Transcription cancelled.")
            self.progress_frame.setVisible(False)
            self.btn_transcribe.setEnabled(True)

    def _copy_plain_text(self):
        if self.current_result:
            plain = self.current_result.plain_text
        else:
            # Strip timestamps from text
            raw = self.editor.toPlainText()
            plain = re.sub(r"\[\d{1,2}:\d{2}(?::\d{2})?.*?\]\s*(?:Speaker \d+:)?\s*", "", raw)
        clipboard = QApplication.clipboard()
        clipboard.setText(plain.strip())
        self.status_bar.showMessage("Plain text copied to clipboard!", 3000)

    def _export_as(self, fmt: str):
        if not self.current_result:
            QMessageBox.information(self, "Export", "No transcript available to export. Transcribe audio first.")
            return

        ext_map = {"srt": "Subtitles (*.srt)", "vtt": "WebVTT (*.vtt)", "json": "JSON (*.json)", "md": "Markdown (*.md)"}
        filter_str = ext_map.get(fmt, "Text Files (*.txt)")

        base_name = Path(self.current_audio_file).stem if self.current_audio_file else "transcript"
        default_path = f"{base_name}.{fmt}"

        file_path, _ = QFileDialog.getSaveFileName(self, f"Export as {fmt.upper()}", default_path, filter_str)
        if file_path:
            save_export_to_file(self.current_result, file_path, format_type=fmt)
            self.status_bar.showMessage(f"Exported successfully to {file_path}", 4000)

    def _on_new_file(self):
        self.editor.clear()
        self.speakers_panel.clear()
        self.current_text_file = None
        self.current_result = None
        self._is_modified = False
        self._update_status_bar()

    def _on_open_text_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Text File", "", "Text Files (*.txt);;All Files (*.*)")
        if file_path:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                self.editor.setPlainText(f.read())
            self.current_text_file = file_path
            self._is_modified = False
            self._update_status_bar()

    def _on_save_file(self):
        if not self.current_text_file:
            self._on_save_as_file()
        else:
            with open(self.current_text_file, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self._is_modified = False
            self._update_status_bar()
            self.status_bar.showMessage(f"Saved {self.current_text_file}", 3000)

    def _on_save_as_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Transcript As", "transcript.txt", "Text Files (*.txt);;All Files (*.*)")
        if file_path:
            self.current_text_file = file_path
            self._on_save_file()

    def _on_open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            self._apply_theme()

    def _on_about(self):
        dlg = AboutDialog(self)
        dlg.exec()
