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
        model_name: str = "small",
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


class LiveTranscriptionWorker(QThread):
    """
    Live streaming microphone transcription worker thread.
    Records from the system microphone, transcribes speech chunks in near real-time,
    and emits segments directly to the notepad editor as the user speaks.
    """

    segment_ready = pyqtSignal(TranscriptionSegment)  # Emitted live as phrases are transcribed
    recording_finished = pyqtSignal(str, TranscriptionResult)  # (saved_wav_file, final_result)
    error_occurred = pyqtSignal(str)
    status_updated = pyqtSignal(str)

    def __init__(
        self,
        transcriber: SpeechTranscriber,
        model_name: str = "small",
        language: Optional[str] = None,
        diarize: bool = True,
        sample_rate: int = 16000,
        chunk_seconds: float = 2.5,
        parent=None,
    ):
        super().__init__(parent)
        self.transcriber = transcriber
        self.model_name = model_name
        self.language = language
        self.diarize = diarize
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds

        self._stop_requested = False
        import queue

        self._audio_queue: queue.Queue = queue.Queue()
        self._stream = None
        self._collected_segments: list[TranscriptionSegment] = []
        self._full_audio_chunks: list[np.ndarray] = []

    def stop_recording(self) -> None:
        """Signal worker to stop recording and finalize transcription."""
        self._stop_requested = True

    def run(self) -> None:
        import os
        import queue
        import tempfile
        import time
        import sounddevice as sd
        import soundfile as sf
        from voicenotes.engine.diarizer import SpeakerDiarizer

        try:
            self.status_updated.emit("Initializing speech model...")
            model = self.transcriber.load_model(self.model_name)

            self.status_updated.emit("🔴 Live Dictating: Speak into microphone...")

            def audio_callback(indata, frames, time_info, status):
                if not self._stop_requested:
                    self._audio_queue.put(indata.copy())

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.2),  # 200ms blocks
            )
            self._stream.start()

            buffer: list[np.ndarray] = []
            accumulated_samples = 0
            chunk_target_samples = int(self.sample_rate * self.chunk_seconds)
            current_audio_time = 0.0
            seg_counter = 0

            lang_param = None if (self.language in (None, "", "auto")) else self.language

            while not self._stop_requested:
                try:
                    block = self._audio_queue.get(timeout=0.2)
                    buffer.append(block)
                    self._full_audio_chunks.append(block)
                    accumulated_samples += len(block)
                except queue.Empty:
                    continue

                if accumulated_samples >= chunk_target_samples:
                    chunk_audio = np.concatenate(buffer, axis=0).flatten()
                    chunk_start = current_audio_time
                    chunk_duration = len(chunk_audio) / self.sample_rate
                    chunk_end = chunk_start + chunk_duration

                    rms = np.sqrt(np.mean(chunk_audio**2))
                    if rms > 0.005:
                        raw_gen, _ = model.transcribe(
                            chunk_audio,
                            language=lang_param,
                            beam_size=1,
                            best_of=1,
                            temperature=0.0,
                            vad_filter=True,
                            word_timestamps=False,
                        )
                        for s in raw_gen:
                            txt = s.text.strip()
                            if txt:
                                seg_counter += 1
                                seg_start = chunk_start + s.start
                                seg_end = min(chunk_end, chunk_start + s.end)
                                seg = TranscriptionSegment(
                                    id=seg_counter,
                                    start=seg_start,
                                    end=seg_end,
                                    text=txt,
                                    speaker=None,
                                )
                                self._collected_segments.append(seg)
                                self.segment_ready.emit(seg)

                    current_audio_time = chunk_end
                    buffer = []
                    accumulated_samples = 0

            # Stop input stream
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            # Drain queue
            while not self._audio_queue.empty():
                b = self._audio_queue.get_nowait()
                buffer.append(b)
                self._full_audio_chunks.append(b)

            # Transcribe tail chunk
            if buffer:
                tail_audio = np.concatenate(buffer, axis=0).flatten()
                if len(tail_audio) > self.sample_rate * 0.4:
                    rms = np.sqrt(np.mean(tail_audio**2))
                    if rms > 0.005:
                        chunk_start = current_audio_time
                        raw_gen, _ = model.transcribe(
                            tail_audio,
                            language=lang_param,
                            beam_size=1,
                            best_of=1,
                            temperature=0.0,
                            vad_filter=True,
                            word_timestamps=False,
                        )
                        for s in raw_gen:
                            txt = s.text.strip()
                            if txt:
                                seg_counter += 1
                                seg = TranscriptionSegment(
                                    id=seg_counter,
                                    start=chunk_start + s.start,
                                    end=chunk_start + s.end,
                                    text=txt,
                                    speaker=None,
                                )
                                self._collected_segments.append(seg)
                                self.segment_ready.emit(seg)

            # Save full recording
            if self._full_audio_chunks:
                full_audio = np.concatenate(self._full_audio_chunks, axis=0).flatten()
            else:
                full_audio = np.zeros(int(self.sample_rate * 0.1), dtype=np.float32)

            total_duration = len(full_audio) / self.sample_rate

            fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="voicenotes_rec_")
            os.close(fd)
            sf.write(wav_path, full_audio, self.sample_rate)

            # Diarize full recording if requested
            unique_speakers = 1
            if self.diarize and self._collected_segments:
                self.status_updated.emit("Identifying speakers across recording...")
                diarizer = SpeakerDiarizer()
                raw_seg_dicts = [
                    {
                        "id": s.id,
                        "start": s.start,
                        "end": s.end,
                        "text": s.text,
                        "words": [],
                        "speaker": None,
                    }
                    for s in self._collected_segments
                ]
                diarized = diarizer.diarize_segments(
                    audio=full_audio,
                    segments=raw_seg_dicts,
                    sr=self.sample_rate,
                )
                self._collected_segments = [
                    TranscriptionSegment(
                        id=d["id"],
                        start=d["start"],
                        end=d["end"],
                        text=d["text"],
                        speaker=d.get("speaker"),
                        words=[],
                    )
                    for d in diarized
                ]
                speakers_set = {s.speaker for s in self._collected_segments if s.speaker}
                unique_speakers = len(speakers_set)

            result = TranscriptionResult(
                audio_path=wav_path,
                duration=total_duration,
                language=self.language or "en",
                language_probability=1.0,
                segments=self._collected_segments,
                model_name=self.model_name,
                num_speakers=unique_speakers,
                diarization_enabled=self.diarize,
            )

            self.recording_finished.emit(wav_path, result)

        except Exception as e:
            logger.exception("Error in LiveTranscriptionWorker")
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
            self.error_occurred.emit(str(e))

