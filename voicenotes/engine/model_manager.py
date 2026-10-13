"""
Manages offline model storage, verification, and pre-downloads.
Supports Whisper models and CAM++ speaker diarization ONNX model.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict, Optional

from huggingface_hub import hf_hub_download

from voicenotes.config import AVAILABLE_WHISPER_MODELS, get_models_dir


class ModelManager:
    """Manages local offline models for Whisper and Speaker Diarization."""

    CAM_PLUS_REPO = "Wespeaker/wespeaker-voxceleb-campplus"
    CAM_PLUS_FILENAME = "voxceleb_CAM++.onnx"

    @classmethod
    def get_models_directory(cls) -> Path:
        return get_models_dir()

    @classmethod
    def get_diarization_model_path(cls) -> Optional[Path]:
        """Locate CAM++ ONNX model locally, or None if not found."""
        models_dir = cls.get_models_directory()
        candidate = models_dir / cls.CAM_PLUS_FILENAME
        if candidate.exists():
            return candidate

        # Check default huggingface hub cache location
        try:
            from huggingface_hub.file_download import try_to_load_from_cache

            cached = try_to_load_from_cache(
                repo_id=cls.CAM_PLUS_REPO,
                filename=cls.CAM_PLUS_FILENAME,
            )
            if cached and isinstance(cached, str) and os.path.exists(cached):
                return Path(cached)
        except Exception:
            pass

        return None

    @classmethod
    def is_diarization_model_available(cls) -> bool:
        return cls.get_diarization_model_path() is not None

    @classmethod
    def download_diarization_model(cls, progress_callback: Optional[Callable[[str], None]] = None) -> Path:
        """Download CAM++ ONNX speaker model into the models directory."""
        models_dir = cls.get_models_directory()
        models_dir.mkdir(parents=True, exist_ok=True)
        dest = models_dir / cls.CAM_PLUS_FILENAME

        if dest.exists():
            return dest

        # If already cached in HF cache, copy it locally without downloading
        cached = cls.get_diarization_model_path()
        if cached and cached.exists() and cached.resolve() != dest.resolve():
            import shutil

            shutil.copy2(cached, dest)
            return dest

        if progress_callback:
            progress_callback(f"Downloading speaker diarization model ({cls.CAM_PLUS_FILENAME})...")

        downloaded_path = hf_hub_download(
            repo_id=cls.CAM_PLUS_REPO,
            filename=cls.CAM_PLUS_FILENAME,
            local_dir=str(models_dir),
        )
        return Path(downloaded_path)

    @classmethod
    def get_whisper_model_path(cls, model_name: str) -> Optional[str]:
        """Locate Whisper model directory locally, or None if not found."""
        from faster_whisper.utils import download_model

        models_dir = cls.get_models_directory()

        # 1. Check local models dir (bundled or pre-downloaded)
        candidate_dirs = [
            models_dir / f"whisper-{model_name}",
            models_dir / f"models--Systran--faster-whisper-{model_name}",
            models_dir,
        ]
        for c in candidate_dirs:
            if c.exists() and (c / "model.bin").exists():
                return str(c)

        # 2. Check default HF cache
        try:
            path = download_model(model_name, local_files_only=True)
            if path and (Path(path) / "model.bin").exists():
                return path
        except Exception:
            pass

        return None

    @classmethod
    def is_whisper_model_available(cls, model_name: str) -> bool:
        """Check if a Whisper model is already available locally."""
        return cls.get_whisper_model_path(model_name) is not None

    @classmethod
    def download_whisper_model(
        cls,
        model_name: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Pre-download a Whisper model so it is ready offline."""
        from faster_whisper.utils import download_model

        # Return immediately if already available offline
        cached_path = cls.get_whisper_model_path(model_name)
        if cached_path is not None:
            return cached_path

        if progress_callback:
            progress_callback(f"Downloading Whisper {model_name} model for offline use...")

        models_dir = cls.get_models_directory()
        target_dir = models_dir / f"whisper-{model_name}"
        target_dir.mkdir(parents=True, exist_ok=True)
        model_path = download_model(model_name, output_dir=str(target_dir))
        return model_path

    @classmethod
    def get_models_status(cls) -> Dict[str, Dict[str, any]]:
        """Return download status of all available models."""
        status = {}
        for key, info in AVAILABLE_WHISPER_MODELS.items():
            status[key] = {
                "name": info["name"],
                "size_mb": info["size_mb"],
                "available": cls.is_whisper_model_available(key),
                "type": "whisper",
            }
        status["diarization"] = {
            "name": "Speaker Diarization (CAM++)",
            "size_mb": 28,
            "available": cls.is_diarization_model_available(),
            "type": "diarization",
        }
        return status
