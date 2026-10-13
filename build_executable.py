"""
Automated build script to package VoiceNotes into a self-contained,
portable Windows distribution folder (dist/VoiceNotes/VoiceNotes.exe).
No Python installation is required on the user's machine.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="VoiceNotes Standalone Executable & Model Bundler")
    parser.add_argument(
        "--models",
        default="tiny,base,diarization",
        help="Comma-separated models to pre-bundle (e.g. 'tiny,base,diarization', 'all', or 'none'). Default: tiny,base,diarization",
    )
    parser.add_argument(
        "--skip-pyinstaller",
        action="store_true",
        help="Download models into ./models/ without executing PyInstaller",
    )
    return parser.parse_args()


def build():
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"

    print("=========================================================")
    print(" VoiceNotes Standalone Executable Builder (Zero-Python)  ")
    print("=========================================================")

    # Clean previous build artifacts safely
    def safe_remove_dir(d: Path):
        if not d.exists():
            return
        for root, dirs, files in os.walk(d, topdown=False):
            for f in files:
                p = os.path.join(root, f)
                try:
                    os.chmod(p, 0o777)
                    os.remove(p)
                except Exception:
                    pass
            for dir_name in dirs:
                p = os.path.join(root, dir_name)
                try:
                    os.rmdir(p)
                except Exception:
                    pass
        try:
            os.rmdir(d)
        except Exception:
            pass

    safe_remove_dir(dist_dir)

    # 1. Ensure requested models are pre-bundled in models/
    models_dir = root_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    models_str = args.models.strip().lower()
    if models_str == "none":
        selected_models = []
    elif models_str == "all":
        selected_models = ["tiny", "base", "small", "medium", "diarization"]
    else:
        selected_models = [m.strip() for m in models_str.split(",") if m.strip()]

    print(f"\n[Models Configuration] Selected for bundling: {', '.join(selected_models) if selected_models else 'None'}")
    from voicenotes.engine.model_manager import ModelManager

    for m in selected_models:
        if m == "diarization":
            cam_dest = models_dir / "voxceleb_CAM++.onnx"
            if not cam_dest.exists():
                print(" -> Pre-downloading CAM++ speaker diarization model...")
                ModelManager.download_diarization_model(target_dir=models_dir, progress_callback=print)
            else:
                print(f" -> CAM++ Diarization model ready ({cam_dest.stat().st_size / (1024*1024):.1f} MB)")
        else:
            w_dest = models_dir / f"whisper-{m}"
            if not (w_dest / "model.bin").exists():
                print(f" -> Pre-downloading Whisper '{m}' model into models/whisper-{m}...")
                ModelManager.download_whisper_model(m, target_dir=w_dest, progress_callback=print)
            else:
                bin_size = (w_dest / "model.bin").stat().st_size / (1024*1024)
                print(f" -> Whisper '{m}' model ready ({bin_size:.1f} MB)")

    if args.skip_pyinstaller:
        print("\n[Done] Models downloaded successfully. Skipping PyInstaller (--skip-pyinstaller).")
        return

    # 2. Run PyInstaller
    print("\nRunning PyInstaller with VoiceNotes.spec...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "VoiceNotes.spec"]
    result = subprocess.run(cmd, cwd=str(root_dir))
    if result.returncode != 0:
        print(f"\n[ERROR] Build failed with return code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)

    output_exe = dist_dir / "VoiceNotes" / "VoiceNotes.exe"
    if output_exe.exists():
        size_mb = os.path.getsize(output_exe) / (1024 * 1024)
        print("\n=========================================================")
        print(" [SUCCESS] BUILD COMPLETE!")
        print(f" Standalone Application: {output_exe}")
        print(f" Executable Size: {size_mb:.2f} MB")
        print(" Portable Directory: dist/VoiceNotes/")
        print(" Anyone can run this without Python installed!")
        print("=========================================================")
    else:
        print(f"\n[ERROR] Output executable not found at {output_exe}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    build()
