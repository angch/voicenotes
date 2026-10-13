"""
High-performance offline speech transcription engine using Faster-Whisper.
Handles hardware acceleration (CUDA with seamless CPU fallback),
word and segment timestamps, and integrates offline speaker diarization.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
from faster_whisper import WhisperModel

from voicenotes.config import AVAILABLE_WHISPER_MODELS, get_models_dir
from voicenotes.engine.audio_utils import format_timestamp, load_audio
from voicenotes.engine.diarizer import SpeakerDiarizer
from voicenotes.engine.model_manager import ModelManager

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionWord:
    word: str
    start: float
    end: float
    probability: float


@dataclass
class TranscriptionSegment:
    id: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: List[TranscriptionWord] = field(default_factory=list)

    @property
    def timestamp_str(self) -> str:
        return f"[{format_timestamp(self.start)} - {format_timestamp(self.end)}]"

    def to_formatted_line(self, include_speaker: bool = True) -> str:
        text_clean = self.text.strip()
        if include_speaker and self.speaker:
            return f"{self.timestamp_str} {self.speaker}: {text_clean}"
        return f"{self.timestamp_str} {text_clean}"


@dataclass
class TranscriptionResult:
    audio_path: Optional[str]
    duration: float
    language: str
    language_probability: float
    segments: List[TranscriptionSegment]
    model_name: str
    num_speakers: int = 1
    diarization_enabled: bool = False

    @property
    def full_text(self) -> str:
        """Return the formatted full text suitable for the notepad editor."""
        lines = []
        for seg in self.segments:
            lines.append(seg.to_formatted_line(include_speaker=self.diarization_enabled))
        return "\n".join(lines)

    @property
    def plain_text(self) -> str:
        """Return plain speech text without timestamps or speaker labels."""
        return " ".join(seg.text.strip() for seg in self.segments)


class SpeechTranscriber:
    """Offline Whisper transcription and speaker diarization engine."""

    def __init__(self):
        self._current_model_name: Optional[str] = None
        self._current_device: Optional[str] = None
        self._model: Optional[WhisperModel] = None
        self._diarizer: Optional[SpeakerDiarizer] = None

    def _get_device_and_compute(self, requested_device: str = "auto") -> tuple[str, str]:
        """Determine device and compute type with automatic fallback."""
        if requested_device == "cpu":
            return "cpu", "int8"

        if requested_device in ("auto", "cuda"):
            try:
                import ctranslate2
                import ctypes

                if ctranslate2.get_cuda_device_count() > 0:
                    # Verify cuBLAS DLL is available on Windows before attempting CUDA
                    can_load_cublas = False
                    for dll_name in ("cublas64_12.dll", "cublas64_11.dll"):
                        try:
                            ctypes.CDLL(dll_name)
                            can_load_cublas = True
                            break
                        except Exception:
                            pass

                    if can_load_cublas:
                        return "cuda", "float16"
                    else:
                        logger.info("NVIDIA GPU detected but cuBLAS DLL not installed; using optimized CPU INT8.")
            except Exception:
                pass

        return "cpu", "int8"

    def load_model(
        self,
        model_name: str = "small",
        device: str = "auto",
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> WhisperModel:
        """Load or switch Whisper model."""
        target_device, target_compute = self._get_device_and_compute(device)

        if (
            self._model is not None
            and self._current_model_name == model_name
            and self._current_device == target_device
        ):
            return self._model

        models_dir = ModelManager.get_models_directory()
        models_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(f"Loading Whisper '{model_name}' on {target_device.upper()}...")

        try:
            self._model = WhisperModel(
                model_name,
                device=target_device,
                compute_type=target_compute,
                download_root=str(models_dir),
            )
            self._current_device = target_device
        except Exception as e:
            if target_device == "cuda":
                logger.warning(f"CUDA initialization failed ({e}), falling back to CPU.")
                if progress_callback:
                    progress_callback("CUDA unavailable, switching to CPU (INT8)...")
                self._model = WhisperModel(
                    model_name,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(models_dir),
                )
                self._current_device = "cpu"
            else:
                raise e

        self._current_model_name = model_name
        return self._model

    def transcribe(
        self,
        audio_source: Union[str, Path, np.ndarray],
        model_name: str = "small",
        language: Optional[str] = None,
        diarize: bool = True,
        num_speakers: Optional[Union[int, str]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        segment_callback: Optional[Callable[[TranscriptionSegment], None]] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file or numpy array, optionally performing speaker diarization.

        Parameters:
        - audio_source: file path or 1D 16kHz float32 numpy array
        - model_name: 'tiny', 'base', 'small', 'medium'
        - language: language code ('en', 'es', etc.) or None / 'auto'
        - diarize: whether to perform speaker diarization
        - num_speakers: 'auto' or integer (2, 3...)
        - progress_callback: callback(status_message, percent_complete)
        - segment_callback: callback(transcription_segment) streamed in real-time
        """
        start_time = time.time()
        audio_path_str = str(audio_source) if isinstance(audio_source, (str, Path)) else None

        if progress_callback:
            progress_callback("Loading and preparing audio...", 5)

        if isinstance(audio_source, (str, Path)):
            audio, sr = load_audio(audio_source, target_sr=16000)
        else:
            audio = audio_source
            sr = 16000

        duration = len(audio) / sr

        if progress_callback:
            progress_callback("Initializing Whisper speech model...", 15)

        model = self.load_model(
            model_name=model_name,
            progress_callback=lambda msg: progress_callback(msg, 20) if progress_callback else None,
        )

        lang_param = None if (language in (None, "", "auto")) else language

        if progress_callback:
            progress_callback("Transcribing speech...", 25)

        try:
            raw_segments_gen, info = model.transcribe(
                audio,
                language=lang_param,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400),
                word_timestamps=True,
            )
            detected_lang = info.language
            lang_prob = info.language_probability
        except Exception as e:
            if self._current_device == "cuda":
                logger.warning(f"CUDA execution failed ({e}), falling back to CPU.")
                if progress_callback:
                    progress_callback("CUDA failed, falling back to CPU...", 25)
                model = self.load_model(model_name=model_name, device="cpu")
                raw_segments_gen, info = model.transcribe(
                    audio,
                    language=lang_param,
                    beam_size=1,
                    best_of=1,
                    temperature=0.0,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400),
                    word_timestamps=True,
                )
                detected_lang = info.language
                lang_prob = info.language_probability
            else:
                raise e

        collected_segments: List[Dict[str, Any]] = []
        seg_idx = 0

        for seg in raw_segments_gen:
            seg_idx += 1
            words = []
            if seg.words:
                for w in seg.words:
                    words.append(
                        TranscriptionWord(
                            word=w.word,
                            start=w.start,
                            end=w.end,
                            probability=w.probability,
                        )
                    )

            seg_dict = {
                "id": seg_idx,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "words": words,
                "speaker": None,
            }
            collected_segments.append(seg_dict)

            # Stream segment live in real-time
            seg_obj = TranscriptionSegment(
                id=seg_idx,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                speaker=None,
                words=words,
            )
            if segment_callback:
                segment_callback(seg_obj)

            if duration > 0:
                pct = min(75, 25 + int(50 * (seg.end / duration)))
            else:
                pct = 50
            if progress_callback:
                progress_callback(
                    f"Transcribing ({format_timestamp(seg.end)} / {format_timestamp(duration)})...",
                    pct,
                )

        # Diarization step
        unique_speakers = 1
        if diarize and collected_segments:
            if progress_callback:
                progress_callback("Identifying speakers (diarization)...", 80)

            if self._diarizer is None:
                self._diarizer = SpeakerDiarizer()

            parsed_num_speakers = None
            if num_speakers not in (None, "", "auto"):
                try:
                    parsed_num_speakers = int(num_speakers)
                except ValueError:
                    parsed_num_speakers = None

            collected_segments = self._diarizer.diarize_segments(
                audio=audio,
                segments=collected_segments,
                sr=sr,
                num_speakers=parsed_num_speakers,
            )

            # Count unique speakers
            speakers_set = {s.get("speaker") for s in collected_segments if s.get("speaker")}
            unique_speakers = len(speakers_set)

        # Merge consecutive segments with the same speaker for natural readability
        merged_segments: List[TranscriptionSegment] = []
        for s in collected_segments:
            seg_obj = TranscriptionSegment(
                id=s["id"],
                start=s["start"],
                end=s["end"],
                text=s["text"],
                speaker=s.get("speaker"),
                words=s.get("words", []),
            )

            if (
                diarize
                and merged_segments
                and merged_segments[-1].speaker == seg_obj.speaker
                and (seg_obj.start - merged_segments[-1].end) < 1.8
            ):
                # Merge into previous segment
                prev = merged_segments[-1]
                prev.end = seg_obj.end
                prev.text = prev.text.rstrip() + " " + seg_obj.text.lstrip()
                prev.words.extend(seg_obj.words)
            else:
                merged_segments.append(seg_obj)

        if progress_callback:
            elapsed = time.time() - start_time
            progress_callback(f"Completed in {elapsed:.1f}s!", 100)

        return TranscriptionResult(
            audio_path=audio_path_str,
            duration=duration,
            language=detected_lang,
            language_probability=lang_prob,
            segments=merged_segments,
            model_name=model_name,
            num_speakers=unique_speakers,
            diarization_enabled=diarize,
        )
