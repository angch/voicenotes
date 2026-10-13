"""
Application dialogs: Settings & Model Manager, Audio Recording, and About.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
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
    QVBoxLayout,
    QWidget,
)

from voicenotes.config import (
    AVAILABLE_WHISPER_MODELS,
    SUPPORTED_LANGUAGES,
    config,
    get_models_dir,
)
from voicenotes.engine.audio_utils import AudioRecorder, format_timestamp
from voicenotes.engine.model_manager import ModelManager
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
