"""
Utility script to pre-download Whisper models and Diarization models
into the local ./models/ directory for 100% offline packaging.
"""

import argparse
import sys
from pathlib import Path

from voicenotes.engine.model_manager import ModelManager


def main():
    parser = argparse.ArgumentParser(description="Download offline models for VoiceNotes")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["tiny", "base", "diarization"],
        help="Models to download (tiny, base, small, medium, diarization, all)",
    )
    args = parser.parse_args()

    models_to_download = args.models
    if "all" in models_to_download:
        models_to_download = ["tiny", "base", "small", "medium", "diarization"]

    print("=== VoiceNotes Offline Model Downloader ===")
    print(f"Target directory: {ModelManager.get_models_directory()}")

    for m in models_to_download:
        if m == "diarization":
            print("\nDownloading CAM++ Speaker Diarization model...")
            p = ModelManager.download_diarization_model(
                progress_callback=lambda msg: print(f"  {msg}")
            )
            print(f"  Saved to: {p}")
        else:
            print(f"\nDownloading Whisper '{m}' model...")
            p = ModelManager.download_whisper_model(
                m,
                progress_callback=lambda msg: print(f"  {msg}"),
            )
            print(f"  Saved to: {p}")

    print("\nAll requested models downloaded and ready for offline use!")


if __name__ == "__main__":
    sys.exit(main())
