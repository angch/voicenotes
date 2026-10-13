"""
Automated build script to package VoiceNotes into a self-contained,
portable Windows distribution folder (dist/VoiceNotes/VoiceNotes.exe).
No Python installation is required on the user's machine.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build():
    root_dir = Path(__file__).resolve().parent
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"

    print("=========================================================")
    print(" VoiceNotes Standalone Executable Builder (Zero-Python)  ")
    print("=========================================================")

    # 1. Ensure models directory has CAM++ diarization model
    models_dir = root_dir / "models"
    cam_model = models_dir / "voxceleb_CAM++.onnx"
    if not cam_model.exists():
        print("Pre-downloading CAM++ speaker diarization model...")
        from voicenotes.engine.model_manager import ModelManager

        ModelManager.download_diarization_model()

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
