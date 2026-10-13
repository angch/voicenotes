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
    Dual-stage streaming live microphone transcription worker thread.
    - Stage 1 (Real-time Draft Pass): Processes ~250ms audio slices with rewind context,
      emitting tentative draft hypotheses with ultra-low latency (~250ms lag).
    - Stage 2 (Refinement Pass): Concurrently rewinds to re-transcribe completed phrases/utterances
      with full acoustic context, high accuracy, and online speaker diarization.
    """

    draft_ready = pyqtSignal(str, float)  # (draft_text, utterance_start_seconds)
    segment_ready = pyqtSignal(TranscriptionSegment)  # (refined/committed segment)
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
        chunk_seconds: float = 0.25,  # 250ms real-time cadence
        draft_model_name: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.transcriber = transcriber
        self.model_name = model_name
        self.language = language
        self.diarize = diarize
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.draft_model_name = draft_model_name or (
            "tiny" if model_name in ("small", "medium", "base") else model_name
        )

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
        import concurrent.futures
        import os
        import queue
        import tempfile
        import time
        import sounddevice as sd
        import soundfile as sf
        from voicenotes.engine.diarizer import SpeakerDiarizer

        try:
            self.status_updated.emit("Initializing speech models for 250ms streaming...")
            draft_model = self.transcriber.load_model(self.draft_model_name)
            if self.model_name == self.draft_model_name:
                refine_model = draft_model
            else:
                refine_model = self.transcriber.load_model(self.model_name)

            diarizer = None
            speaker_centroids: list[tuple[np.ndarray, str]] = []
            if self.diarize:
                try:
                    diarizer = SpeakerDiarizer()
                except Exception as de:
                    logger.warning(f"Could not initialize live diarizer: {de}")

            self.status_updated.emit("🔴 Live Dictating: Speak into microphone (real-time)...")

            block_samples = int(self.sample_rate * 0.05)  # 50ms blocks for low audio latency

            def audio_callback(indata, frames, time_info, status):
                if not self._stop_requested:
                    self._audio_queue.put(indata.copy())

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=audio_callback,
                blocksize=block_samples,
            )
            self._stream.start()

            buffer: list[np.ndarray] = []
            total_samples = 0
            committed_time = 0.0
            last_draft_time = 0.0
            last_speech_time = 0.0
            seg_counter = 0

            lang_param = None if (self.language in (None, "", "auto")) else self.language

            def _refine_task(audio_slice: np.ndarray, start_t: float, end_t: float) -> list[TranscriptionSegment]:
                refined_list = []
                try:
                    raw_gen, _ = refine_model.transcribe(
                        audio_slice,
                        language=lang_param,
                        beam_size=2,
                        best_of=2,
                        temperature=0.0,
                        vad_filter=True,
                        word_timestamps=True,
                    )
                    for s in raw_gen:
                        txt = s.text.strip()
                        if not txt:
                            continue
                        s_start = max(start_t, start_t + s.start)
                        s_end = min(end_t, start_t + s.end)
                        if s_end <= s_start:
                            s_end = s_start + max(0.2, s.end - s.start)

                        spk_label = None
                        if diarizer is not None and len(audio_slice) >= int(self.sample_rate * 0.15):
                            try:
                                emb = diarizer.extract_embedding(audio_slice, sr=self.sample_rate)
                                if not speaker_centroids:
                                    speaker_centroids.append((emb, "Speaker 1"))
                                    spk_label = "Speaker 1"
                                else:
                                    sims = [float(np.dot(emb, c_emb)) for c_emb, _ in speaker_centroids]
                                    best_idx = int(np.argmax(sims))
                                    if sims[best_idx] >= 0.65:
                                        spk_label = speaker_centroids[best_idx][1]
                                        new_c = 0.8 * speaker_centroids[best_idx][0] + 0.2 * emb
                                        norm = np.linalg.norm(new_c)
                                        if norm > 0:
                                            new_c = new_c / norm
                                        speaker_centroids[best_idx] = (new_c, spk_label)
                                    else:
                                        spk_label = f"Speaker {len(speaker_centroids) + 1}"
                                        speaker_centroids.append((emb, spk_label))
                            except Exception:
                                pass

                        refined_list.append(
                            TranscriptionSegment(
                                id=0,
                                start=s_start,
                                end=s_end,
                                text=txt,
                                speaker=spk_label,
                            )
                        )
                except Exception as ex:
                    logger.warning(f"Error in refine task: {ex}")
                return refined_list

            refine_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            active_future: Optional[concurrent.futures.Future] = None
            pending_committed_advance = None

            while not self._stop_requested:
                try:
                    block = self._audio_queue.get(timeout=0.05)
                    buffer.append(block)
                    self._full_audio_chunks.append(block)
                    total_samples += len(block)
                except queue.Empty:
                    pass

                # Check background refinement task completion
                if active_future is not None and active_future.done():
                    try:
                        res_segs = active_future.result()
                        for r_seg in res_segs:
                            seg_counter += 1
                            r_seg.id = seg_counter
                            self._collected_segments.append(r_seg)
                            self.segment_ready.emit(r_seg)
                            committed_time = max(committed_time, r_seg.end)
                    except Exception as fe:
                        logger.warning(f"Refinement future exception: {fe}")
                    if pending_committed_advance is not None:
                        committed_time = max(committed_time, pending_committed_advance)
                        pending_committed_advance = None
                    active_future = None

                if not buffer:
                    continue

                current_time = total_samples / self.sample_rate
                uncommitted_sec = current_time - committed_time

                # Detect speech activity in recent ~250ms
                recent_window = np.concatenate(buffer[-5:], axis=0).flatten() if len(buffer) >= 5 else buffer[-1].flatten()
                recent_rms = np.sqrt(np.mean(recent_window**2)) if len(recent_window) > 0 else 0.0

                if recent_rms > 0.005:
                    last_speech_time = current_time

                time_since_speech = current_time - last_speech_time
                is_speaking = time_since_speech < 0.35

                # Trigger Refinement Pass when:
                # 1. User paused (VAD pause >= 0.35s after speech) and uncommitted >= 0.4s
                # 2. Or uncommitted audio >= 2.5s (continuous speech limit)
                should_refine = (
                    active_future is None
                    and uncommitted_sec >= 0.4
                    and (not is_speaking or uncommitted_sec >= 2.5)
                )

                full_curr_audio = None
                if should_refine:
                    full_curr_audio = np.concatenate(self._full_audio_chunks, axis=0).flatten()
                    r_start = committed_time
                    r_end = current_time
                    r_slice = full_curr_audio[int(r_start * self.sample_rate) : int(r_end * self.sample_rate)]
                    r_rms = np.sqrt(np.mean(r_slice**2)) if len(r_slice) > 0 else 0.0

                    if r_rms > 0.004:
                        pending_committed_advance = r_end
                        active_future = refine_executor.submit(_refine_task, r_slice, r_start, r_end)
                    else:
                        committed_time = r_end

                # Trigger Real-time Draft Pass (~250ms cadence)
                if (current_time - last_draft_time) >= self.chunk_seconds:
                    last_draft_time = current_time
                    if uncommitted_sec >= 0.2:
                        if full_curr_audio is None:
                            full_curr_audio = np.concatenate(self._full_audio_chunks, axis=0).flatten()
                        d_start = committed_time
                        d_end = current_time
                        d_slice = full_curr_audio[int(d_start * self.sample_rate) : int(d_end * self.sample_rate)]
                        d_rms = np.sqrt(np.mean(d_slice**2)) if len(d_slice) > 0 else 0.0
                        if d_rms > 0.004:
                            try:
                                d_gen, _ = draft_model.transcribe(
                                    d_slice,
                                    language=lang_param,
                                    beam_size=1,
                                    best_of=1,
                                    temperature=0.0,
                                    vad_filter=True,
                                    without_timestamps=True,
                                )
                                d_text = " ".join(s.text.strip() for s in d_gen if s.text.strip())
                                if d_text:
                                    self.draft_ready.emit(d_text, d_start)
                                else:
                                    self.draft_ready.emit("", d_start)
                            except Exception:
                                pass
                        else:
                            self.draft_ready.emit("", d_start)

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

            # Wait for any in-flight refinement task
            if active_future is not None:
                try:
                    res_segs = active_future.result(timeout=5.0)
                    for r_seg in res_segs:
                        seg_counter += 1
                        r_seg.id = seg_counter
                        self._collected_segments.append(r_seg)
                        self.segment_ready.emit(r_seg)
                        committed_time = max(committed_time, r_seg.end)
                except Exception as ex:
                    logger.warning(f"Error waiting for refinement future: {ex}")

            refine_executor.shutdown(wait=False)

            # Transcribe tail chunk if uncommitted audio remains
            if self._full_audio_chunks:
                full_audio = np.concatenate(self._full_audio_chunks, axis=0).flatten()
            else:
                full_audio = np.zeros(int(self.sample_rate * 0.1), dtype=np.float32)

            total_duration = len(full_audio) / self.sample_rate
            if (total_duration - committed_time) >= 0.3:
                tail_slice = full_audio[int(committed_time * self.sample_rate) :]
                tail_rms = np.sqrt(np.mean(tail_slice**2)) if len(tail_slice) > 0 else 0.0
                if tail_rms > 0.004:
                    tail_segs = _refine_task(tail_slice, committed_time, total_duration)
                    for ts in tail_segs:
                        seg_counter += 1
                        ts.id = seg_counter
                        self._collected_segments.append(ts)
                        self.segment_ready.emit(ts)

            # Save full recording to temp WAV
            fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="voicenotes_rec_")
            os.close(fd)
            sf.write(wav_path, full_audio, self.sample_rate)

            # Final global diarization pass if requested
            unique_speakers = 1
            if self.diarize and self._collected_segments:
                self.status_updated.emit("Finalizing speaker clustering...")
                try:
                    diarizer = SpeakerDiarizer()
                    raw_seg_dicts = [
                        {
                            "id": s.id,
                            "start": s.start,
                            "end": s.end,
                            "text": s.text,
                            "words": [],
                            "speaker": s.speaker,
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
                except Exception as de:
                    logger.warning(f"Final diarization error: {de}")

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

