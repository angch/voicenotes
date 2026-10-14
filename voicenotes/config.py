"""
Application configuration and path resolution for VoiceNotes.
Handles paths for both standard execution and PyInstaller-frozen builds.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


def get_app_dir() -> Path:
    """Return the base directory of the application."""
    if getattr(sys, "frozen", False):
        # Running inside PyInstaller bundle
        return Path(sys.executable).parent.resolve()
    # Running from source tree
    return Path(__file__).resolve().parent.parent


def get_bundle_dir() -> Path:
    """Return the bundled resources directory (sys._MEIPASS if frozen)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return get_app_dir()


def get_app_icon_path() -> Path:
    """Return the path to the application icon."""
    for base in (get_bundle_dir(), get_app_dir()):
        png = base / "assets" / "app_icon.png"
        if png.exists():
            return png
        ico = base / "assets" / "app_icon.ico"
        if ico.exists():
            return ico
    return get_app_dir() / "assets" / "app_icon.png"


def get_models_dir() -> Path:
    """
    Return the directory where offline models are stored.
    Checks bundled models first, then app_dir/models, then user cache.
    """
    # 1. Local models folder in app dir (for portable distribution)
    app_models = get_app_dir() / "models"
    if app_models.exists():
        return app_models

    # 2. Bundled models folder (if packaged inside PyInstaller internal)
    bundle_models = get_bundle_dir() / "models"
    if bundle_models.exists():
        return bundle_models

    # 3. User cache directory
    user_cache = Path(os.path.expanduser("~")) / ".cache" / "voicenotes" / "models"
    user_cache.mkdir(parents=True, exist_ok=True)
    return user_cache


def get_samples_dir() -> Path:
    """Return the directory containing audio test samples."""
    samples = get_bundle_dir() / "samples"
    if samples.exists():
        return samples
    app_samples = get_app_dir() / "samples"
    if app_samples.exists():
        return app_samples
    return get_app_dir() / "samples"


# Whisper Model Catalog
AVAILABLE_WHISPER_MODELS = {
    "tiny": {
        "name": "Tiny",
        "description": "Ultra fast (~75 MB), lower memory, best for quick notes",
        "size_mb": 75,
        "default_compute": "int8",
    },
    "base": {
        "name": "Base",
        "description": "Fast & lightweight (~145 MB), good for clean audio",
        "size_mb": 145,
        "default_compute": "int8",
    },
    "small": {
        "name": "Small (Recommended)",
        "description": "High accuracy (~480 MB), optimized for near real-time streaming",
        "size_mb": 480,
        "default_compute": "int8",
    },
    "medium": {
        "name": "Medium",
        "description": "Very high accuracy (~1.5 GB), slower on low-end CPUs",
        "size_mb": 1500,
        "default_compute": "int8",
    },
}

SUPPORTED_LANGUAGES = [
    ("auto", "Auto-Detect Language"),
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("ru", "Russian"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("sv", "Swedish"),
    ("tr", "Turkish"),
    ("uk", "Ukrainian"),
    ("vi", "Vietnamese"),
]

DEFAULT_SETTINGS: Dict[str, Any] = {
    "model": "small",
    "language": "auto",
    "device": "auto",  # 'auto', 'cuda', 'cpu'
    "diarization_enabled": True,
    "num_speakers": "auto",  # 'auto' or integer (2, 3, etc.)
    "diarization_threshold": 0.65,
    "theme": "system",  # 'system' (follow OS), 'light', or 'dark'
    "font_size": 13,
    "font_family": "Segoe UI",
    "word_wrap": True,
    "timestamp_format": "[{start} - {end}]",
    "last_open_folder": "",
    "vocabulary_replacements": [],
}


class ConfigManager:
    """Manages persistent user configuration."""

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_dir = Path(os.path.expanduser("~")) / ".config" / "voicenotes"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "settings.json"
        else:
            self.config_file = config_path

        self._settings = self._load()

    def _load(self) -> Dict[str, Any]:
        settings = dict(DEFAULT_SETTINGS)
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    settings.update(data)
            except Exception:
                pass
        return settings

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save()

    def save(self) -> None:
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass


# Global config instance
config = ConfigManager()
