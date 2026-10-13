"""
Background worker thread for running Whisper transcription and diarization.
Keeps the GUI completely responsive.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from voicenotes.engine.transcriber import (
    SpeechTranscriber,
    TranscriptionResult,
    TranscriptionSegment,
)

logger = logging.getLogger(__name__)


class TranscriptionWorker(QThread):
    """
    Background worker thread executing offline transcription and diarization.
    """

    progress_updated = pyqtSignal(str, int)  # (status_message, percent)
    segment_ready = pyqtSignal(TranscriptionSegment)  # streamed segment
    finished_success = pyqtSignal(TranscriptionResult)  # full result
    error_occurred = pyqtSignal(str)  # error message

    def __init__(
        self,
        transcriber: SpeechTranscriber,
        audio_source: Union[str, Path, np.ndarray],
        model_name: str = "base",
        language: Optional[str] = None,
        diarize: bool = True,
        num_speakers: Optional[Union[int, str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.transcriber = transcriber
        self.audio_source = audio_source
        self.model_name = model_name
        self.language = language
        self.diarize = diarize
        self.num_speakers = num_speakers
        self._is_cancelled = False

    def cancel(self) -> None:
        """Request worker thread cancellation."""
        self._is_cancelled = True

    def run(self) -> None:
        try:

            def on_progress(msg: str, pct: int):
                if not self._is_cancelled:
                    self.progress_updated.emit(msg, pct)

            def on_segment(seg: TranscriptionSegment):
                if not self._is_cancelled:
                    self.segment_ready.emit(seg)

            result = self.transcriber.transcribe(
                audio_source=self.audio_source,
                model_name=self.model_name,
                language=self.language,
                diarize=self.diarize,
                num_speakers=self.num_speakers,
                progress_callback=on_progress,
                segment_callback=on_segment,
            )

            if not self._is_cancelled:
                self.finished_success.emit(result)
        except Exception as e:
            logger.exception("Error during transcription worker execution")
            self.error_occurred.emit(str(e))
