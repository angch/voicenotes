"""
Application dialogs: Settings & Model Manager, Audio Recording, and About.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voicenotes import __version__
from voicenotes.config import (
    AVAILABLE_WHISPER_MODELS,
    SUPPORTED_LANGUAGES,
    config,
    get_models_dir,
)
from voicenotes.engine.audio_utils import AudioRecorder, format_timestamp
from voicenotes.engine.model_manager import ModelManager
from voicenotes.export.exporters import export_to_json
from voicenotes.gui.styles import get_effective_theme, get_stylesheet


class ModelDownloadWorker(QThread):
    """Thread to download models without blocking the dialog."""

    progress_updated = pyqtSignal(str)
    download_finished = pyqtSignal(bool, str)

    def __init__(self, model_key: str, parent=None):
        super().__init__(parent)
        self.model_key = model_key

    def run(self):
        try:
            if self.model_key == "diarization":
                ModelManager.download_diarization_model(
                    progress_callback=lambda msg: self.progress_updated.emit(msg)
                )
            else:
                ModelManager.download_whisper_model(
                    self.model_key,
                    progress_callback=lambda msg: self.progress_updated.emit(msg),
                )
            self.download_finished.emit(True, f"Model '{self.model_key}' downloaded successfully!")
        except Exception as e:
            self.download_finished.emit(False, str(e))


class RecordDialog(QDialog):
    """Microphone recording dialog with live timer."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Record Audio")
        self.setFixedSize(380, 220)
        eff_theme = get_effective_theme(config.get("theme", "system"))
        self.setStyleSheet(get_stylesheet(eff_theme))
        self.recorder = AudioRecorder()
        self.recorded_file: Optional[str] = None

        self._init_ui()
        self._start_recording()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.lbl_status = QLabel("🔴 Recording in progress...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 15px; font-weight: bold; color: #cf1322;")
        layout.addWidget(self.lbl_status)

        self.lbl_timer = QLabel("00:00")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet("font-size: 32px; font-weight: bold; font-family: monospace;")
        layout.addWidget(self.lbl_timer)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_stop = QPushButton("Stop & Transcribe")
        self.btn_stop.setObjectName("primaryButton")
        self.btn_stop.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_layout)

        # Update timer every 250ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(250)

    def _start_recording(self):
        try:
            self.recorder.start()
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Could not access microphone:\n{e}")
            self.reject()

    def _update_timer(self):
        elapsed = self.recorder.get_elapsed_seconds()
        self.lbl_timer.setText(format_timestamp(elapsed))

    def _on_stop(self):
        self.timer.stop()
        self.lbl_status.setText("Processing audio recording...")
        self.btn_stop.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        try:
            self.recorded_file = self.recorder.save_to_temp_file()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save recording:\n{e}")
            self.reject()

    def _on_cancel(self):
        self.timer.stop()
        self.recorder.stop()
        self.reject()


class SettingsDialog(QDialog):
    """Settings and Offline Model Manager Dialog."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Offline Models")
        self.setMinimumSize(560, 480)
        eff_theme = get_effective_theme(config.get("theme", "system"))
        self.setStyleSheet(get_stylesheet(eff_theme))
        self.download_worker: Optional[ModelDownloadWorker] = None

        self._init_ui()
        self._refresh_models_table()

    def _init_ui(self):
        eff_theme = get_effective_theme(config.get("theme", "system"))
        is_dark = eff_theme == "dark"
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # General Preferences Group
        grp_general = QGroupBox("Transcription Preferences")
        form_layout = QFormLayout(grp_general)
        form_layout.setSpacing(10)

        # Hardware Device
        self.combo_device = QComboBox()
        self.combo_device.addItem("Automatic (GPU if available, else CPU)", "auto")
        self.combo_device.addItem("CPU Only (Reliable, INT8 quantized)", "cpu")
        self.combo_device.addItem("NVIDIA CUDA GPU (Fastest)", "cuda")
        curr_device = config.get("device", "auto")
        idx = self.combo_device.findData(curr_device)
        if idx >= 0:
            self.combo_device.setCurrentIndex(idx)
        form_layout.addRow("Inference Device:", self.combo_device)

        # Default Model
        self.combo_model = QComboBox()
        for k, v in AVAILABLE_WHISPER_MODELS.items():
            self.combo_model.addItem(f"{v['name']} (~{v['size_mb']}MB)", k)
        curr_model = config.get("model", "base")
        idx = self.combo_model.findData(curr_model)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)
        form_layout.addRow("Default Model:", self.combo_model)

        # Default Language
        self.combo_lang = QComboBox()
        for code, name in SUPPORTED_LANGUAGES:
            self.combo_lang.addItem(name, code)
        curr_lang = config.get("language", "auto")
        idx = self.combo_lang.findData(curr_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        form_layout.addRow("Default Language:", self.combo_lang)

        # Color Theme
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("💻 Follow System (OS Settings)", "system")
        self.combo_theme.addItem("☀️ Light Mode", "light")
        self.combo_theme.addItem("🌙 Dark Mode", "dark")
        curr_theme = config.get("theme", "system")
        idx = self.combo_theme.findData(curr_theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)
        form_layout.addRow("Color Theme:", self.combo_theme)

        layout.addWidget(grp_general)

        # Diarization Sensitivity
        grp_diar = QGroupBox("Speaker Diarization")
        diar_layout = QVBoxLayout(grp_diar)
        diar_layout.setSpacing(8)

        self.chk_diar = QCheckBox("Enable Speaker Diarization by default")
        self.chk_diar.setChecked(config.get("diarization_enabled", True))
        diar_layout.addWidget(self.chk_diar)

        lbl_info = QLabel(
            "Speaker detection uses offline CAM++ ONNX embeddings (28MB). "
            "No internet or cloud tokens needed."
        )
        lbl_info.setStyleSheet(f"color: {'#a0aec0' if is_dark else '#666666'}; font-size: 11px;")
        lbl_info.setWordWrap(True)
        diar_layout.addWidget(lbl_info)

        layout.addWidget(grp_diar)

        # Offline Models Manager Group
        grp_models = QGroupBox("Offline Models Catalog")
        models_layout = QVBoxLayout(grp_models)

        self.table_models = QTableWidget()
        self.table_models.setColumnCount(4)
        self.table_models.setHorizontalHeaderLabels(["Model", "Size", "Offline Status", "Action"])
        self.table_models.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_models.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_models.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_models.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        models_layout.addWidget(self.table_models)

        self.lbl_download_status = QLabel("")
        self.lbl_download_status.setStyleSheet(f"color: {'#4dabf7' if is_dark else '#0067c0'}; font-weight: bold;")
        models_layout.addWidget(self.lbl_download_status)

        layout.addWidget(grp_models)

        # Dialog Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _refresh_models_table(self):
        statuses = ModelManager.get_models_status()
        self.table_models.setRowCount(len(statuses))

        for row, (key, info) in enumerate(statuses.items()):
            # Model Name
            item_name = QTableWidgetItem(info["name"])
            self.table_models.setItem(row, 0, item_name)

            # Size
            item_size = QTableWidgetItem(f"~{info['size_mb']} MB")
            self.table_models.setItem(row, 1, item_size)

            # Status
            is_ready = info["available"]
            status_text = "✅ Ready Offline" if is_ready else "❌ Not Downloaded"
            item_status = QTableWidgetItem(status_text)
            self.table_models.setItem(row, 2, item_status)

            # Action
            btn = QPushButton("Re-download" if is_ready else "Download")
            btn.setProperty("model_key", key)
            btn.clicked.connect(lambda checked, k=key: self._download_model(k))
            self.table_models.setCellWidget(row, 3, btn)

    def _download_model(self, model_key: str):
        self.lbl_download_status.setText(f"Downloading '{model_key}'... Please wait.")
        self.download_worker = ModelDownloadWorker(model_key, self)
        self.download_worker.progress_updated.connect(self.lbl_download_status.setText)
        self.download_worker.download_finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_finished(self, success: bool, message: str):
        self.lbl_download_status.setText(message)
        self._refresh_models_table()
        if not success:
            QMessageBox.warning(self, "Download Error", f"Failed to download model:\n{message}")

    def _on_save(self):
        config.set("device", self.combo_device.currentData())
        config.set("model", self.combo_model.currentData())
        config.set("language", self.combo_lang.currentData())
        config.set("theme", self.combo_theme.currentData())
        config.set("diarization_enabled", self.chk_diar.isChecked())
        self.accept()


class AboutDialog(QDialog):
    """About VoiceNotes Dialog."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("About VoiceNotes")
        self.setFixedSize(450, 340)
        eff_theme = get_effective_theme(config.get("theme", "system"))
        self.setStyleSheet(get_stylesheet(eff_theme))
        is_dark = eff_theme == "dark"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("🎙️ VoiceNotes")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {'#4dabf7' if is_dark else '#0067c0'};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Offline Speech Transcriber with Speaker Tagging")
        subtitle.setStyleSheet(f"font-size: 13px; color: {'#a0aec0' if is_dark else '#666666'}; font-weight: 500;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        info = QLabel(
            "• <b>100% Offline & Private</b>: Runs entirely on your machine. No audio is ever sent to the cloud.<br>"
            "• <b>State-of-the-Art Whisper AI</b>: Ultra-fast transcription via Faster-Whisper.<br>"
            "• <b>Speaker Diarization</b>: Automatically identifies and labels different speakers.<br>"
            "• <b>Interactive Notepad</b>: Click any timestamp to jump and play audio from that moment.<br>"
            "• <b>Zero-Config Portability</b>: Built for non-technical users."
        )
        info.setWordWrap(True)
        info.setStyleSheet("line-height: 1.4;")
        layout.addWidget(info)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)


class SendVoiceDialog(QDialog):
    """
    Dialog to package, export, or send audio recordings and transcripts
    to developers for speech tuning, accent optimization, and diarization debugging.
    """

    def __init__(
        self,
        audio_path: Optional[str] = None,
        transcript_text: str = "",
        transcript_result: Optional[any] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Send Voice Sample for Tuning & Debugging")
        self.setMinimumSize(540, 520)

        self.audio_path = audio_path
        self.transcript_text = transcript_text
        self.transcript_result = transcript_result

        eff_theme = get_effective_theme(config.get("theme", "system"))
        self.setStyleSheet(get_stylesheet(eff_theme))

        self._init_ui()

    def _init_ui(self):
        eff_theme = get_effective_theme(config.get("theme", "system"))
        is_dark = eff_theme == "dark"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Title & Subtitle
        lbl_title = QLabel("Send Voice Sample for Tuning")
        lbl_title.setStyleSheet(
            f"font-size: 17px; font-weight: bold; color: {'#4dabf7' if is_dark else '#0067c0'};"
        )
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Share an audio clip and transcript with developers to help improve speech recognition "
            "accuracy, speaker separation, and vocabulary tuning for your recording setup."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"color: {'#cccccc' if is_dark else '#444444'}; font-size: 12px;")
        layout.addWidget(lbl_desc)

        # Privacy notice
        notice_box = QFrame()
        notice_layout = QVBoxLayout(notice_box)
        notice_layout.setContentsMargins(10, 8, 10, 8)
        notice_bg = "#232b38" if is_dark else "#eef6ff"
        notice_border = "#2f4562" if is_dark else "#b8d7ff"
        notice_text_col = "#c8e1ff" if is_dark else "#0d47a1"
        notice_box.setStyleSheet(
            f"background-color: {notice_bg}; border: 1px solid {notice_border}; border-radius: 5px;"
        )

        lbl_notice = QLabel(
            "<b>Privacy Notice:</b> VoiceNotes operates 100% offline. Files are only shared when you "
            "explicitly export or attach them. Please do not submit recordings containing confidential personal information."
        )
        lbl_notice.setWordWrap(True)
        lbl_notice.setStyleSheet(f"color: {notice_text_col}; font-size: 11px;")
        notice_layout.addWidget(lbl_notice)
        layout.addWidget(notice_box)

        # Sample Summary Group
        grp_summary = QGroupBox("Sample && Environment Details")
        form = QFormLayout(grp_summary)
        form.setSpacing(6)

        audio_name = Path(self.audio_path).name if self.audio_path and os.path.exists(self.audio_path) else "No audio loaded"
        audio_size_str = f" ({os.path.getsize(self.audio_path)/(1024*1024):.2f} MB)" if self.audio_path and os.path.exists(self.audio_path) else ""
        form.addRow("Audio Source:", QLabel(f"{audio_name}{audio_size_str}"))

        duration_val = getattr(self.transcript_result, "duration", None)
        dur_str = f"{format_timestamp(duration_val)} ({duration_val:.1f}s)" if duration_val else "N/A"
        form.addRow("Audio Duration:", QLabel(dur_str))

        model_name = config.get("model", "small")
        dev_name = config.get("device", "auto")
        form.addRow("Whisper Model / Device:", QLabel(f"{model_name} / {dev_name}"))

        spk_count = getattr(self.transcript_result, "num_speakers", 0)
        diar_str = f"Enabled ({spk_count} detected)" if config.get("diarization_enabled", True) else "Disabled"
        form.addRow("Speaker Diarization:", QLabel(diar_str))

        layout.addWidget(grp_summary)

        # Optional User Feedback / Notes
        grp_notes = QGroupBox("Feedback / What Needs Tuning? (Optional)")
        notes_layout = QVBoxLayout(grp_notes)
        self.edit_notes = QTextEdit()
        self.edit_notes.setPlaceholderText(
            "Example: Misheard words around 0:14, speaker attribution inverted, background noise, regional accent, etc."
        )
        self.edit_notes.setMaximumHeight(70)
        notes_layout.addWidget(self.edit_notes)
        layout.addWidget(grp_notes)

        # Delivery Action Buttons Group
        grp_actions = QGroupBox("Delivery Options")
        act_layout = QVBoxLayout(grp_actions)
        act_layout.setSpacing(8)

        # 1. Save ZIP bundle
        btn_row1 = QHBoxLayout()
        self.btn_save_zip = QPushButton("Save Debug Bundle (.zip)...")
        self.btn_save_zip.setToolTip("Create a .zip archive containing the audio, transcript, and system metadata on your computer.")
        self.btn_save_zip.clicked.connect(self._on_save_zip)
        btn_row1.addWidget(self.btn_save_zip)
        lbl_hint_zip = QLabel("Save package to folder of your choice")
        lbl_hint_zip.setStyleSheet("color: #888; font-size: 11px;")
        btn_row1.addWidget(lbl_hint_zip, stretch=1)
        act_layout.addLayout(btn_row1)

        # 2. Open GitHub Issue
        btn_row2 = QHBoxLayout()
        self.btn_github = QPushButton("Submit via GitHub Issue")
        self.btn_github.setToolTip("Create bundle and open GitHub Issues in your browser to attach the sample.")
        self.btn_github.clicked.connect(self._on_submit_github)
        btn_row2.addWidget(self.btn_github)
        lbl_hint_gh = QLabel("Opens https://github.com/angch/voicenotes/issues")
        lbl_hint_gh.setStyleSheet("color: #888; font-size: 11px;")
        btn_row2.addWidget(lbl_hint_gh, stretch=1)
        act_layout.addLayout(btn_row2)

        # 3. Send via Email
        btn_row3 = QHBoxLayout()
        self.btn_email = QPushButton("Send via Email")
        self.btn_email.setToolTip("Create bundle and open your email client addressed to ang.chin.han@gmail.com.")
        self.btn_email.clicked.connect(self._on_send_email)
        btn_row3.addWidget(self.btn_email)
        lbl_hint_email = QLabel("To: ang.chin.han@gmail.com")
        lbl_hint_email.setStyleSheet("color: #888; font-size: 11px;")
        btn_row3.addWidget(lbl_hint_email, stretch=1)
        act_layout.addLayout(btn_row3)

        layout.addWidget(grp_actions)

        # Bottom Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _build_bundle(self, target_zip_path: Path) -> bool:
        """Create a zip archive containing audio, transcript, metadata, and user notes."""
        try:
            target_zip_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 1. User feedback notes
                notes = self.edit_notes.toPlainText().strip()
                if notes:
                    zf.writestr("feedback_notes.txt", notes)

                # 2. Transcript plain text
                text = self.transcript_text.strip()
                if text:
                    zf.writestr("transcript.txt", text)

                # 3. Structured result JSON if present
                if self.transcript_result:
                    try:
                        if hasattr(self.transcript_result, "to_dict"):
                            zf.writestr(
                                "transcript.json",
                                json.dumps(self.transcript_result.to_dict(), indent=2),
                            )
                        else:
                            zf.writestr(
                                "transcript.json",
                                export_to_json(self.transcript_result),
                            )
                    except Exception:
                        pass

                # 4. Metadata and environment diagnostics
                meta = {
                    "app_name": "VoiceNotes",
                    "app_version": __version__,
                    "created_at": datetime.now().isoformat(),
                    "platform": {
                        "os": platform.system(),
                        "release": platform.release(),
                        "version": platform.version(),
                        "architecture": platform.machine(),
                        "processor": platform.processor(),
                        "python_version": platform.python_version(),
                    },
                    "config": {
                        "model": config.get("model", "small"),
                        "device": config.get("device", "auto"),
                        "language": config.get("language", "auto"),
                        "diarization_enabled": config.get("diarization_enabled", True),
                    },
                    "audio": {
                        "file_name": Path(self.audio_path).name if self.audio_path else None,
                        "file_size": os.path.getsize(self.audio_path)
                        if self.audio_path and os.path.exists(self.audio_path)
                        else None,
                        "duration": getattr(self.transcript_result, "duration", None),
                        "duration_seconds": getattr(self.transcript_result, "duration", None),
                        "num_speakers": getattr(self.transcript_result, "num_speakers", None),
                    },
                    "notes": notes,
                }
                zf.writestr("debug_metadata.json", json.dumps(meta, indent=2))

                # 5. Audio file if present
                if self.audio_path and os.path.exists(self.audio_path):
                    p = Path(self.audio_path)
                    zf.write(self.audio_path, arcname=f"audio{p.suffix}")

            return True
        except Exception as e:
            QMessageBox.critical(self, "Packaging Error", f"Failed to create debug bundle:\n{e}")
            return False

    def _reveal_file(self, file_path: Path):
        """Open the enclosing folder and highlight the created zip file."""
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", f"/select,{os.path.abspath(file_path)}"])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent.resolve())))
        except Exception:
            pass

    def _on_save_zip(self):
        default_name = f"voicenotes_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        last_dir = config.get("last_open_folder", str(Path.home()))
        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save VoiceNotes Tuning Bundle",
            str(Path(last_dir) / default_name),
            "ZIP Archives (*.zip);;All Files (*.*)",
        )
        if not dest_path:
            return

        p = Path(dest_path)
        if self._build_bundle(p):
            self._reveal_file(p)
            QMessageBox.information(
                self,
                "Bundle Saved",
                f"Tuning bundle saved successfully to:\n{p}\n\nThe folder has been opened in File Explorer.",
            )

    def _on_submit_github(self):
        downloads_dir = Path.home() / "Downloads"
        target_dir = downloads_dir if downloads_dir.exists() else Path(tempfile.gettempdir())
        default_name = f"voicenotes_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = target_dir / default_name

        if not self._build_bundle(zip_path):
            return

        self._reveal_file(zip_path)

        audio_name = Path(self.audio_path).name if self.audio_path else "Recorded Audio"
        model_name = config.get("model", "small")
        dev_name = config.get("device", "auto")
        notes = self.edit_notes.toPlainText().strip()

        issue_title = f"[Tuning Sample] {audio_name} ({model_name})"
        issue_body = f"""### Voice Sample for Model Tuning & Accuracy

**Recording & Settings**:
- Audio File: `{audio_name}`
- Model: `{model_name}` | Device: `{dev_name}`
- OS: `{platform.system()} {platform.release()} ({platform.machine()})`
- VoiceNotes Version: `{__version__}`

**User Notes & Feedback**:
{notes if notes else "(No additional notes provided)"}

---
*(Please drag-and-drop the generated `{zip_path.name}` file into this issue box to attach it!)*
"""
        params = urllib.parse.urlencode({"title": issue_title, "body": issue_body})
        issue_url = f"https://github.com/angch/voicenotes/issues/new?{params}"

        QDesktopServices.openUrl(QUrl(issue_url))
        QMessageBox.information(
            self,
            "GitHub Issue Opened",
            f"Bundle created:\n{zip_path}\n\nA new GitHub Issue page has been opened in your browser.\n"
            f"Please drag-and-drop the highlighted ZIP file into the GitHub issue box to attach it.",
        )

    def _on_send_email(self):
        downloads_dir = Path.home() / "Downloads"
        target_dir = downloads_dir if downloads_dir.exists() else Path(tempfile.gettempdir())
        default_name = f"voicenotes_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = target_dir / default_name

        if not self._build_bundle(zip_path):
            return

        self._reveal_file(zip_path)

        audio_name = Path(self.audio_path).name if self.audio_path else "Audio Sample"
        model_name = config.get("model", "small")
        notes = self.edit_notes.toPlainText().strip()

        email_to = "ang.chin.han@gmail.com"
        subject = f"VoiceNotes Tuning Sample: {audio_name}"
        body = f"""Hi Ang Chin Han,

Here is an audio and transcription sample for VoiceNotes model tuning:

- Audio: {audio_name}
- Model: {model_name}
- OS: {platform.system()} {platform.release()} ({platform.machine()})
- VoiceNotes: {__version__}

User Feedback:
{notes if notes else "(None)"}

I have attached the zip file ({zip_path.name}).
"""
        mailto_url = f"mailto:{email_to}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        QDesktopServices.openUrl(QUrl(mailto_url))
        QMessageBox.information(
            self,
            "Email Client Opened",
            f"Bundle created:\n{zip_path}\n\nYour default email client has been opened.\n"
            f"Please attach the highlighted ZIP file ({zip_path.name}) to the email.",
        )
