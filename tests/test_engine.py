"""
Unit tests for VoiceNotes transcription, diarization, and audio utilities.
"""

import os
from pathlib import Path

import pytest
import soundfile as sf

from voicenotes.config import get_app_icon_path
from voicenotes.engine.audio_utils import format_timestamp, load_audio, parse_timestamp
from voicenotes.engine.diarizer import SpeakerDiarizer
from voicenotes.engine.model_manager import ModelManager
from voicenotes.engine.transcriber import (
    SpeechTranscriber,
    get_cuda_device_name,
    is_cuda_available,
    setup_cuda_dll_paths,
)


def test_timestamp_formatting():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(65) == "01:05"
    assert format_timestamp(3665) == "01:01:05"
    assert format_timestamp(65.123, include_millis=True) == "01:05.123"


def test_timestamp_parsing():
    assert parse_timestamp("01:05") == 65.0
    assert parse_timestamp("01:01:05") == 3665.0
    assert parse_timestamp("[02:30]") == 150.0


def test_audio_loader_and_metadata():
    jfk_path = Path("samples/jfk.flac")
    assert jfk_path.exists()

    audio, sr = load_audio(jfk_path, target_sr=16000)
    assert sr == 16000
    assert audio.ndim == 1
    assert len(audio) > 0
    assert abs(len(audio) / 16000 - 11.0) < 0.5


def test_model_manager_status():
    if not ModelManager.is_diarization_model_available():
        ModelManager.download_diarization_model()
    status = ModelManager.get_models_status()
    assert "tiny" in status
    assert "base" in status
    assert "diarization" in status
    assert status["diarization"]["available"] is True


def test_diarizer_embedding_extraction():
    diarizer = SpeakerDiarizer()
    jfk_path = Path("samples/jfk.flac")
    audio, sr = load_audio(jfk_path, target_sr=16000)

    # Extract embedding from first 2 seconds
    chunk = audio[: 16000 * 2]
    emb = diarizer.extract_embedding(chunk, sr=sr)
    assert emb.shape == (512,)
    # Should be normalized
    assert abs(float(sum(emb**2)) - 1.0) < 0.05


def test_transcriber_single_speaker():
    transcriber = SpeechTranscriber()
    result = transcriber.transcribe(
        "samples/jfk.flac",
        model_name="tiny",
        diarize=False,
    )
    assert result is not None
    assert result.duration > 10.0
    assert len(result.segments) >= 1
    full_text = result.full_text.lower()
    assert "fellow americans" in full_text or "country" in full_text


def test_transcriber_multi_speaker_diarization():
    two_speakers_path = Path("samples/two_speakers_conversation.wav")
    assert two_speakers_path.exists()

    transcriber = SpeechTranscriber()
    result = transcriber.transcribe(
        two_speakers_path,
        model_name="tiny",
        diarize=True,
    )
    assert result is not None
    assert result.num_speakers >= 2
    speaker_set = {seg.speaker for seg in result.segments if seg.speaker}
    assert len(speaker_set) >= 2
    assert "Speaker 1" in speaker_set
    assert "Speaker 2" in speaker_set


def test_cuda_detection_and_dll_setup():
    added = setup_cuda_dll_paths()
    assert isinstance(added, list)
    cuda_avail = is_cuda_available()
    assert isinstance(cuda_avail, bool)
    device_name = get_cuda_device_name()
    if cuda_avail:
        assert device_name is not None
        assert "NVIDIA" in device_name.upper()


def test_app_icon_paths():
    icon_path = get_app_icon_path()
    assert icon_path.exists()
    assert icon_path.suffix.lower() in (".png", ".ico")
    assert Path("assets/app_icon.png").exists()
    assert Path("assets/app_icon.ico").exists()
    assert Path("assets/app_icon.ico").stat().st_size > 1000
