"""
Audio loading, preprocessing, feature extraction, and recording utilities.
"""

from __future__ import annotations

import os
import queue
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional, Tuple, Union

import numpy as np
import scipy.signal
try:
    import sounddevice as sd
except Exception:
    sd = None
import soundfile as sf


def format_timestamp(seconds: float, include_millis: bool = False) -> str:
    """Format seconds into HH:MM:SS or MM:SS (with optional milliseconds)."""
    if seconds is None or seconds < 0:
        seconds = 0.0
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - total_seconds) * 1000)

    if hours > 0:
        base = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        base = f"{minutes:02d}:{secs:02d}"

    if include_millis:
        return f"{base}.{millis:03d}"
    return base


def parse_timestamp(timestamp_str: str) -> Optional[float]:
    """Parse string timestamp like '01:23' or '01:23:45' or '01:23.450' into seconds."""
    try:
        parts = timestamp_str.strip("[] ").split(":")
        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except Exception:
        pass
    return None


def load_audio(
    file_path: Union[str, Path],
    target_sr: int = 16000,
) -> Tuple[np.ndarray, int]:
    """
    Load an audio or video file and return a mono 16kHz float32 numpy array.
    Supports WAV, MP3, FLAC, OGG, M4A, AAC, WEBM, MP4, etc.
    Tries soundfile first, falls back to PyAV container decoding.
    """
    file_path_str = str(file_path)

    # 1. Try soundfile (very fast for wav, flac, ogg)
    try:
        audio, sr = sf.read(file_path_str, dtype="float32")
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        if sr != target_sr:
            num_samples = int(len(audio) * target_sr / sr)
            audio = scipy.signal.resample(audio, num_samples).astype(np.float32)
        # Normalize audio amplitude safely
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            audio = audio / max_val
        return audio, target_sr
    except Exception:
        pass

    # 2. Fall back to PyAV container decoding (for mp4, m4a, etc.)
    try:
        import av

        container = av.open(file_path_str)
        audio_stream = next((s for s in container.streams if s.type == "audio"), None)
        if audio_stream is None:
            raise ValueError(f"No audio stream found in {file_path}")

        resampler = av.AudioResampler(format="flt", layout="mono", rate=target_sr)
        frames_list = []
        for frame in container.decode(audio_stream):
            resampled = resampler.resample(frame)
            if resampled:
                for r_frame in resampled:
                    frames_list.append(r_frame.to_ndarray().flatten())

        if not frames_list:
            raise ValueError(f"No audio frames decoded from {file_path}")

        audio = np.concatenate(frames_list).astype(np.float32)
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            audio = audio / max_val
        return audio, target_sr
    except Exception as e:
        raise RuntimeError(f"Failed to load audio from {file_path}: {e}") from e


def compute_fbank(
    waveform: np.ndarray,
    sr: int = 16000,
    num_mel_bins: int = 80,
    frame_length: int = 25,
    frame_shift: int = 10,
) -> np.ndarray:
    """
    Compute 80-dimensional log Mel filterbank features for CAM++ speaker embedding.
    Fully vectorized in NumPy / SciPy, Kaldi-compatible with CMVN.
    """
    n_fft = 512
    win_len = int(sr * frame_length / 1000)
    hop_len = int(sr * frame_shift / 1000)
    window = np.hamming(win_len)

    num_frames = 1 + int((len(waveform) - win_len) / hop_len)
    if num_frames <= 0:
        return np.zeros((1, num_mel_bins), dtype=np.float32)

    waveform = np.ascontiguousarray(waveform)
    frames = np.lib.stride_tricks.as_strided(
        waveform,
        shape=(num_frames, win_len),
        strides=(waveform.strides[0] * hop_len, waveform.strides[0]),
    )
    frames = frames * window
    mag = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2

    # Mel filterbank construction
    low_freq = 20.0
    high_freq = sr / 2.0
    mel_low = 1127.0 * np.log(1.0 + low_freq / 700.0)
    mel_high = 1127.0 * np.log(1.0 + high_freq / 700.0)
    mel_points = np.linspace(mel_low, mel_high, num_mel_bins + 2)
    hz_points = 700.0 * (np.exp(mel_points / 1127.0) - 1.0)
    bins = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    fbanks = np.zeros((num_mel_bins, int(n_fft / 2 + 1)), dtype=np.float32)
    for m in range(1, num_mel_bins + 1):
        f_m_minus = bins[m - 1]
        f_m = bins[m]
        f_m_plus = bins[m + 1]
        for k in range(f_m_minus, f_m):
            fbanks[m - 1, k] = (k - bins[m - 1]) / (bins[m] - bins[m - 1] + 1e-8)
        for k in range(f_m, f_m_plus):
            fbanks[m - 1, k] = (bins[m + 1] - k) / (bins[m + 1] - bins[m] + 1e-8)

    filter_banks = np.dot(mag, fbanks.T)
    filter_banks = np.where(filter_banks <= 0, 1e-12, filter_banks)
    log_mel = np.log(filter_banks)

    # Cepstral Mean Normalization (CMVN)
    log_mel -= np.mean(log_mel, axis=0)
    return log_mel.astype(np.float32)


class AudioRecorder:
    """Handles microphone recording via sounddevice."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self._queue: queue.Queue = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._audio_chunks: list[np.ndarray] = []
        self._start_time: float = 0.0

    def start(self) -> None:
        """Start recording from default microphone."""
        if sd is None:
            raise RuntimeError(
                "Audio recording is unavailable because PortAudio could not be loaded. "
                "Ensure libportaudio2 is installed or bundled."
            )
        self._audio_chunks = []
        self.recording = True
        self._start_time = time.time()

        def audio_callback(indata, frames, time_info, status):
            if self.recording:
                self._queue.put(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            callback=audio_callback,
        )
        self._stream.start()

    def get_elapsed_seconds(self) -> float:
        """Return elapsed recording duration in seconds."""
        if not self.recording:
            return 0.0
        return time.time() - self._start_time

    def stop(self) -> np.ndarray:
        """Stop recording and return collected audio waveform."""
        self.recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        while not self._queue.empty():
            self._audio_chunks.append(self._queue.get())

        if not self._audio_chunks:
            return np.zeros(0, dtype=np.float32)

        audio = np.concatenate(self._audio_chunks, axis=0)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        return audio.flatten()

    def save_to_temp_file(self, target_format: str = "wav") -> str:
        """Stop recording and save to a temporary file (wav, ogg, or mp3)."""
        audio = self.stop()
        fmt = target_format.lower().lstrip(".")
        if fmt not in ("wav", "ogg", "mp3"):
            fmt = "wav"
        fd, path = tempfile.mkstemp(suffix=f".{fmt}", prefix="voicenotes_rec_")
        os.close(fd)
        sf_format = "OGG" if fmt == "ogg" else ("MP3" if fmt == "mp3" else "WAV")
        sf.write(path, audio, self.sample_rate, format=sf_format)
        return path


def compress_audio_file(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    target_format: str = "ogg",
    target_sr: int = 16000,
) -> Path:
    """
    Compress an audio file to .ogg (default) or .mp3 for efficient archival and transmission.

    Args:
        input_path: Path to existing audio file.
        output_path: Optional destination path. If None, a temporary file is created.
        target_format: 'ogg' or 'mp3'.
        target_sr: Sample rate in Hz (default 16000 Hz, voice standard).

    Returns:
        Path to the resulting compressed audio file.
    """
    input_p = Path(input_path).resolve()
    if not input_p.exists():
        raise FileNotFoundError(f"Source audio file not found: {input_path}")

    fmt = target_format.lower().lstrip(".")
    if fmt not in ("ogg", "mp3"):
        fmt = "ogg"

    if output_path is None:
        fd, temp_dest = tempfile.mkstemp(suffix=f".{fmt}", prefix="voicenotes_compressed_")
        os.close(fd)
        out_p = Path(temp_dest)
    else:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

    audio, sr = load_audio(input_p, target_sr=target_sr)
    sf_format = "OGG" if fmt == "ogg" else "MP3"
    sf.write(str(out_p), audio, sr, format=sf_format)
    return out_p

