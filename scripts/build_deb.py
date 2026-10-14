#!/usr/bin/env python3
"""
Automated Debian/Ubuntu (.deb) package generator for VoiceNotes.

Supports:
1. Single all-in-one .deb (application + models + acceleration)
2. Split .deb (package 1: python app/code, package 2: models + nvidia/amd acceleration)

Includes full support for:
- Ubuntu 22.04 / 24.04+ (Noble Numbat) and Debian 11/12
- Both Wayland and X11 display servers
- Hardware acceleration out-of-the-box: CPU (INT8), NVIDIA CUDA, and AMD ROCm
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build" / "deb"

APP_NAME = "voicenotes"
PACKAGE_VERSION = "0.5.1"


def get_version() -> str:
    """Read version from voicenotes/__init__.py."""
    try:
        from voicenotes import __version__
        return __version__
    except Exception:
        return PACKAGE_VERSION


def create_launcher_script() -> str:
    """Generate robust /usr/bin/voicenotes launcher script."""
    return """#!/usr/bin/env bash
# VoiceNotes Universal Linux Launcher (Wayland + X11, CPU/AMD/NVIDIA)
set -e

# Prefix detection (supports standard system /usr or custom prefix)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX="$(cd "$SCRIPT_DIR/.." && pwd)"

# 1. Wayland & X11 display server auto-configuration
if [ -z "$QT_QPA_PLATFORM" ]; then
    if [ -n "$WAYLAND_DISPLAY" ] || [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        # Native Wayland with seamless X11 (XWayland) fallback
        export QT_QPA_PLATFORM="wayland;xcb"
    elif [ -n "$DISPLAY" ] || [ "$XDG_SESSION_TYPE" = "x11" ]; then
        export QT_QPA_PLATFORM="xcb"
    fi
fi

# 2. Hardware acceleration search paths (NVIDIA CUDA & AMD ROCm)
LIB_CANDIDATES=(
    "$PREFIX/lib/voicenotes/lib"
    "$PREFIX/lib/voicenotes/voicenotes/lib"
    "$PREFIX/lib/voicenotes/accel"
    "$PREFIX/lib/voicenotes"
    "/usr/lib/voicenotes/lib"
    "/usr/lib/voicenotes/accel"
    "/usr/lib/voicenotes"
    "/opt/rocm/lib"
    "/opt/rocm/hip/lib"
    "/usr/lib/x86_64-linux-gnu/rocm"
    "/usr/local/cuda/lib64"
    "/usr/local/cuda/targets/x86_64-linux/lib"
)

EXTRA_LIBS=""
for p in "${LIB_CANDIDATES[@]}"; do
    if [ -d "$p" ]; then
        EXTRA_LIBS="$p${EXTRA_LIBS:+:$EXTRA_LIBS}"
    fi
done

if [ -n "$EXTRA_LIBS" ]; then
    export LD_LIBRARY_PATH="$EXTRA_LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

# 3. Model directory discovery
if [ -d "$PREFIX/share/voicenotes/models" ]; then
    export VOICENOTES_MODELS_DIR="$PREFIX/share/voicenotes/models"
elif [ -d "/usr/share/voicenotes/models" ]; then
    export VOICENOTES_MODELS_DIR="/usr/share/voicenotes/models"
fi

# 3b. Sample directory discovery
if [ -d "$PREFIX/share/voicenotes/samples" ]; then
    export VOICENOTES_SAMPLES_DIR="$PREFIX/share/voicenotes/samples"
elif [ -d "/usr/share/voicenotes/samples" ]; then
    export VOICENOTES_SAMPLES_DIR="/usr/share/voicenotes/samples"
fi

# 4. Launch executable
if [ -x "$PREFIX/lib/voicenotes/VoiceNotes" ]; then
    exec "$PREFIX/lib/voicenotes/VoiceNotes" "$@"
elif [ -x "/usr/lib/voicenotes/VoiceNotes" ]; then
    exec "/usr/lib/voicenotes/VoiceNotes" "$@"
elif [ -f "$PREFIX/lib/voicenotes/bin/python" ]; then
    exec "$PREFIX/lib/voicenotes/bin/python" -m voicenotes.app "$@"
elif [ -f "/usr/lib/voicenotes/bin/python" ]; then
    exec "/usr/lib/voicenotes/bin/python" -m voicenotes.app "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -m voicenotes.app "$@"
else
    echo "Error: VoiceNotes application runtime not found in $PREFIX/lib/voicenotes or /usr/lib/voicenotes." >&2
    exit 1
fi
"""


def create_desktop_file() -> str:
    """Generate standard FreeDesktop .desktop specification."""
    return """[Desktop Entry]
Version=1.0
Type=Application
Name=VoiceNotes
GenericName=Speech Transcriber & Notepad
Comment=Offline speech transcription and speaker diarization tool
Exec=voicenotes %F
Icon=voicenotes
Terminal=false
Categories=AudioVideo;Audio;Office;Utility;
MimeType=audio/wav;audio/x-wav;audio/mp3;audio/mpeg;audio/flac;audio/ogg;audio/x-m4a;video/mp4;video/quicktime;
Keywords=transcription;speech;whisper;voice;audio;diarization;notes;notepad;
StartupWMClass=voicenotes
StartupNotify=true
"""


def create_gpu_accel_helper() -> str:
    """Generate GPU acceleration information script."""
    return """#!/usr/bin/env bash
# VoiceNotes GPU Acceleration Detection Helper
echo "=== VoiceNotes Hardware Acceleration Status ==="
echo "Display Server : ${XDG_SESSION_TYPE:-Unknown} (WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-None}, DISPLAY=${DISPLAY:-None})"

# Check NVIDIA
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "NVIDIA Driver  : Available ($(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | tr '\\n' ', '))"
elif [ -e "/dev/nvidia0" ]; then
    echo "NVIDIA Device  : /dev/nvidia0 detected"
else
    echo "NVIDIA Driver  : Not detected"
fi

# Check AMD ROCm
if command -v rocm-smi >/dev/null 2>&1; then
    echo "AMD ROCm       : Available"
elif [ -e "/dev/kfd" ]; then
    echo "AMD ROCm       : Kernel node /dev/kfd detected"
else
    echo "AMD ROCm       : Not detected"
fi

echo "CPU Compute    : Optimized OpenMP INT8 execution always available"
echo "================================================"
"""


def generate_hicolor_icons(staging_dir: Path) -> None:
    """Generate icons in all standard hicolor dimensions."""
    src_icon = ROOT_DIR / "assets" / "app_icon.png"
    if not src_icon.exists():
        return

    im = Image.open(src_icon)
    sizes = [16, 24, 32, 48, 64, 128, 256, 512]
    icons_root = staging_dir / "usr" / "share" / "icons" / "hicolor"

    for size in sizes:
        size_dir = icons_root / f"{size}x{size}" / "apps"
        size_dir.mkdir(parents=True, exist_ok=True)
        dest = size_dir / "voicenotes.png"
        resized = im.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(dest, format="PNG")

    # Also install to /usr/share/pixmaps/voicenotes.png
    pixmaps_dir = staging_dir / "usr" / "share" / "pixmaps"
    pixmaps_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_icon, pixmaps_dir / "voicenotes.png")


def create_control_file(
    package_name: str,
    version: str,
    description_summary: str,
    description_body: str,
    depends: str = "",
    recommends: str = "",
    suggests: str = "",
    arch: str = "amd64",
) -> str:
    """Generate Debian control file."""
    lines = [
        f"Package: {package_name}",
        f"Version: {version}",
        "Section: sound",
        "Priority: optional",
        f"Architecture: {arch}",
        "Maintainer: VoiceNotes Contributors <https://github.com>",
    ]
    if depends:
        lines.append(f"Depends: {depends}")
    if recommends:
        lines.append(f"Recommends: {recommends}")
    if suggests:
        lines.append(f"Suggests: {suggests}")

    lines.append(f"Description: {description_summary}")
    for l in description_body.strip().splitlines():
        lines.append(f" {l}")

    return "\n".join(lines) + "\n"


def create_postinst_script() -> str:
    """Generate Debian postinst script."""
    return """#!/bin/sh
set -e

if [ "$1" = "configure" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
    fi
fi
exit 0
"""


def create_postrm_script() -> str:
    """Generate Debian postrm script."""
    return """#!/bin/sh
set -e

if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
    fi
fi
exit 0
"""


def copy_application_binaries(target_app_dir: Path, include_models: bool = True) -> None:
    """Copy compiled PyInstaller distribution into staging directory."""
    src_dist = DIST_DIR / "VoiceNotes"
    if not src_dist.exists():
        raise FileNotFoundError(
            f"PyInstaller build directory not found at {src_dist}. "
            "Please run 'python build_executable.py' first."
        )

    target_app_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dist.iterdir():
        if not include_models and item.name == "models":
            continue
        dest = target_app_dir / item.name
        if item.is_dir():
            shutil.copytree(
                item,
                dest,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("*.pyc", "__pycache__") if not include_models else None,
            )
            # If models should be excluded, remove models from inside _internal if present
            if not include_models:
                internal_models = dest / "models"
                if internal_models.exists():
                    shutil.rmtree(internal_models)
        else:
            shutil.copy2(item, dest)

    # Ensure executable permissions
    exe = target_app_dir / "VoiceNotes"
    if exe.exists():
        exe.chmod(0o755)


def copy_models_to_share(models_staging_dir: Path) -> None:
    """Copy models directory to /usr/share/voicenotes/models, excluding ephemeral caches."""
    src_models = ROOT_DIR / "models"
    dest_models = models_staging_dir / "usr" / "share" / "voicenotes" / "models"
    dest_models.mkdir(parents=True, exist_ok=True)

    if src_models.exists():
        for item in src_models.iterdir():
            if item.name.startswith(".") and item.name != ".gitkeep":
                continue
            dest = dest_models / item.name
            if item.is_dir():
                shutil.copytree(
                    item,
                    dest,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".cache", "*.lock", "*.metadata", "trees"),
                )
            else:
                shutil.copy2(item, dest)


def copy_samples_to_share(samples_staging_dir: Path) -> None:
    """Copy audio test samples to /usr/share/voicenotes/samples."""
    src_samples = ROOT_DIR / "samples"
    dest_samples = samples_staging_dir / "usr" / "share" / "voicenotes" / "samples"
    dest_samples.mkdir(parents=True, exist_ok=True)

    if src_samples.exists():
        for item in src_samples.iterdir():
            if item.is_file():
                shutil.copy2(item, dest_samples / item.name)


def install_base_system_files(staging_dir: Path, include_accel_helper: bool = True) -> None:
    """Install common launcher, desktop entry, and icon files."""
    # 1. Launcher: /usr/bin/voicenotes
    bin_dir = staging_dir / "usr" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher_file = bin_dir / "voicenotes"
    launcher_file.write_text(create_launcher_script(), encoding="utf-8")
    launcher_file.chmod(0o755)

    # 2. Desktop file: /usr/share/applications/voicenotes.desktop
    apps_dir = staging_dir / "usr" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = apps_dir / "voicenotes.desktop"
    desktop_file.write_text(create_desktop_file(), encoding="utf-8")
    desktop_file.chmod(0o644)

    # 3. Icons in hicolor theme and pixmaps
    generate_hicolor_icons(staging_dir)

    # 4. Acceleration helper script (optional per package)
    if include_accel_helper:
        accel_dir = staging_dir / "usr" / "lib" / "voicenotes" / "accel"
        accel_dir.mkdir(parents=True, exist_ok=True)
        helper = accel_dir / "gpu_check.sh"
        helper.write_text(create_gpu_accel_helper(), encoding="utf-8")
        helper.chmod(0o755)

        gpu_bin = bin_dir / "voicenotes-gpu-check"
        gpu_bin.write_text(create_gpu_accel_helper(), encoding="utf-8")
        gpu_bin.chmod(0o755)

    # 5. Samples
    copy_samples_to_share(staging_dir)


def package_deb(staging_dir: Path, output_deb_path: Path, compression: str = "gzip") -> None:
    """Invoke dpkg-deb to package staging directory into .deb."""
    print(f" -> Packaging {output_deb_path.name} from {staging_dir} (compression: {compression})...")
    output_deb_path.parent.mkdir(parents=True, exist_ok=True)
    if output_deb_path.exists():
        output_deb_path.unlink()

    cmd = ["dpkg-deb", f"-Z{compression}", "--build", "--root-owner-group", str(staging_dir), str(output_deb_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] dpkg-deb failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(result.returncode)

    size_mb = output_deb_path.stat().st_size / (1024 * 1024)
    print(f" -> [SUCCESS] Generated: {output_deb_path} ({size_mb:.2f} MB)")
    # Immediately reclaim disk space by removing staging directory
    shutil.rmtree(staging_dir, ignore_errors=True)


def build_all_in_one_deb(version: str, output_name: Optional[str] = None, compression: str = "gzip") -> Path:
    """Build a single .deb containing application, models, and GPU acceleration."""
    print("\n=======================================================")
    print(" Building All-in-One VoiceNotes Debian Package (.deb)   ")
    print("=======================================================")

    staging_dir = BUILD_DIR / "all-in-one"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    # Common system files
    install_base_system_files(staging_dir)

    # Application binaries (without duplicating models)
    app_lib_dir = staging_dir / "usr" / "lib" / "voicenotes"
    copy_application_binaries(app_lib_dir, include_models=False)

    # Place models in /usr/share/voicenotes/models
    copy_models_to_share(staging_dir)

    # DEBIAN directory
    debian_dir = staging_dir / "DEBIAN"
    debian_dir.mkdir(parents=True, exist_ok=True)

    control_content = create_control_file(
        package_name="voicenotes",
        version=version,
        description_summary="Offline speech transcription and speaker diarization (All-in-One)",
        description_body=(
            "VoiceNotes is a desktop speech-to-text application with a clean\n"
            "Notepad-style interface, offline Whisper transcription, CAM++ speaker\n"
            "diarization, and clickable timestamps.\n"
            "This all-in-one package includes pre-bundled offline models (Whisper\n"
            "and CAM++) and supports CPU, NVIDIA CUDA, and AMD ROCm acceleration out of the box\n"
            "on both X11 and Wayland."
        ),
        depends="libportaudio2, libxcb-cursor0, libasound2t64 | libasound2",
        recommends="nvidia-driver-535 | nvidia-driver-550 | rocm-hip-runtime",
        suggests="pipewire-audio | pulseaudio",
    )
    (debian_dir / "control").write_text(control_content, encoding="utf-8")

    postinst = debian_dir / "postinst"
    postinst.write_text(create_postinst_script(), encoding="utf-8")
    postinst.chmod(0o755)

    postrm = debian_dir / "postrm"
    postrm.write_text(create_postrm_script(), encoding="utf-8")
    postrm.chmod(0o755)

    out_name = output_name or f"voicenotes_{version}_amd64.deb"
    out_deb = DIST_DIR / out_name
    package_deb(staging_dir, out_deb, compression=compression)
    return out_deb


def build_split_debs(version: str, compression: str = "gzip") -> tuple[Path, Path]:
    """Build two .deb packages: (1) application code, (2) models + acceleration."""
    print("\n=======================================================")
    print(" Building Split VoiceNotes Debian Packages (2x .deb)   ")
    print("=======================================================")

    # 1. Package 1: voicenotes (App code)
    print("\n--- 1. Building Application Package (voicenotes) ---")
    app_staging = BUILD_DIR / "split-app"
    if app_staging.exists():
        shutil.rmtree(app_staging)

    # Base system files without GPU check helper (accel package owns it)
    install_base_system_files(app_staging, include_accel_helper=False)
    app_lib_dir = app_staging / "usr" / "lib" / "voicenotes"
    copy_application_binaries(app_lib_dir, include_models=False)

    app_debian = app_staging / "DEBIAN"
    app_debian.mkdir(parents=True, exist_ok=True)
    app_control = create_control_file(
        package_name="voicenotes",
        version=version,
        description_summary="Offline speech transcription and speaker diarization tool",
        description_body=(
            "VoiceNotes desktop speech-to-text application with a clean\n"
            "Notepad-style interface, offline Faster-Whisper engine, CAM++ speaker\n"
            "diarization, and interactive audio playback.\n"
            "Supports Wayland and X11 display servers.\n"
            "Install 'voicenotes-models-accel' for pre-bundled offline models and\n"
            "enhanced GPU acceleration (NVIDIA CUDA & AMD ROCm)."
        ),
        depends="libportaudio2, libxcb-cursor0, libasound2t64 | libasound2",
        recommends="voicenotes-models-accel",
        suggests="nvidia-driver-535 | nvidia-driver-550 | rocm-hip-runtime",
    )
    (app_debian / "control").write_text(app_control, encoding="utf-8")

    postinst = app_debian / "postinst"
    postinst.write_text(create_postinst_script(), encoding="utf-8")
    postinst.chmod(0o755)

    postrm = app_debian / "postrm"
    postrm.write_text(create_postrm_script(), encoding="utf-8")
    postrm.chmod(0o755)

    app_deb = DIST_DIR / f"voicenotes_{version}_amd64.deb"
    package_deb(app_staging, app_deb, compression=compression)

    # Also provide clearly named alias voicenotes-app_... for clarity in dual distributions
    app_alias = DIST_DIR / f"voicenotes-app_{version}_amd64.deb"
    try:
        if app_alias.exists():
            app_alias.unlink()
        os.link(app_deb, app_alias)
    except Exception:
        shutil.copy2(app_deb, app_alias)

    # 2. Package 2: voicenotes-models-accel
    print("\n--- 2. Building Models & Acceleration Package (voicenotes-models-accel) ---")
    accel_staging = BUILD_DIR / "split-models-accel"
    if accel_staging.exists():
        shutil.rmtree(accel_staging)

    copy_models_to_share(accel_staging)

    accel_lib = accel_staging / "usr" / "lib" / "voicenotes" / "accel"
    accel_lib.mkdir(parents=True, exist_ok=True)
    helper = accel_lib / "gpu_check.sh"
    helper.write_text(create_gpu_accel_helper(), encoding="utf-8")
    helper.chmod(0o755)

    bin_dir = accel_staging / "usr" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    gpu_bin = bin_dir / "voicenotes-gpu-check"
    gpu_bin.write_text(create_gpu_accel_helper(), encoding="utf-8")
    gpu_bin.chmod(0o755)

    accel_debian = accel_staging / "DEBIAN"
    accel_debian.mkdir(parents=True, exist_ok=True)
    accel_control = create_control_file(
        package_name="voicenotes-models-accel",
        version=version,
        description_summary="Offline AI speech models and GPU acceleration (NVIDIA/AMD)",
        description_body=(
            "Pre-bundled offline models and hardware acceleration configurations\n"
            "for VoiceNotes. Includes Whisper models, CAM++ ONNX speaker diarization\n"
            "model, and GPU runtime discovery for NVIDIA CUDA and AMD ROCm."
        ),
        recommends="voicenotes",
        suggests="nvidia-driver-535 | nvidia-driver-550 | rocm-hip-runtime",
    )
    (accel_debian / "control").write_text(accel_control, encoding="utf-8")

    accel_deb = DIST_DIR / f"voicenotes-models-accel_{version}_amd64.deb"
    package_deb(accel_staging, accel_deb, compression=compression)

    return app_deb, accel_deb


def main():
    parser = argparse.ArgumentParser(description="VoiceNotes Debian/Ubuntu Package (.deb) Builder")
    parser.add_argument(
        "--mode",
        choices=["all-in-one", "split", "both"],
        default="all-in-one",
        help="Packaging mode: 'all-in-one' (single deb), 'split' (2 debs: app + models/accel), or 'both'. Default: all-in-one",
    )
    parser.add_argument(
        "--compression",
        choices=["gzip", "xz", "zstd"],
        default="gzip",
        help="Compression type for dpkg-deb ('gzip' for high compatibility and speed, 'xz' for maximum compression, 'zstd'). Default: gzip",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Package version string (defaults to project version)",
    )
    args = parser.parse_args()
    version = args.version or get_version()

    print("=========================================================")
    print(f" VoiceNotes Debian (.deb) Package Builder v{version}     ")
    print(f" Mode: {args.mode.upper()}                               ")
    print("=========================================================")

    # Ensure standalone binary exists
    if not (DIST_DIR / "VoiceNotes" / "VoiceNotes").exists():
        print("Standalone binary not found. Running build_executable.py...")
        cmd = [sys.executable, "build_executable.py"]
        res = subprocess.run(cmd, cwd=str(ROOT_DIR))
        if res.returncode != 0:
            print("[ERROR] Build executable failed.", file=sys.stderr)
            sys.exit(res.returncode)

    if args.mode == "all-in-one":
        deb = build_all_in_one_deb(version, compression=args.compression)
        # Also provide alias voicenotes_..._all-in-one_amd64.deb
        aio_alias = DIST_DIR / f"voicenotes_{version}_all-in-one_amd64.deb"
        try:
            if aio_alias.exists():
                aio_alias.unlink()
            os.link(deb, aio_alias)
        except Exception:
            shutil.copy2(deb, aio_alias)

        print("\n=========================================================")
        print(" [SUCCESS] All-in-One .deb package created successfully!")
        print(f" File: {deb} ({deb.stat().st_size / (1024*1024):.2f} MB)")
        print(f" Install via: sudo dpkg -i {deb}")
        print("=========================================================")
    elif args.mode == "split":
        app_deb, accel_deb = build_split_debs(version, compression=args.compression)
        print("\n=========================================================")
        print(" [SUCCESS] Split .deb packages created successfully!")
        print(f" 1. App Package   : {app_deb} ({app_deb.stat().st_size / (1024*1024):.2f} MB)")
        print(f" 2. Models & Accel: {accel_deb} ({accel_deb.stat().st_size / (1024*1024):.2f} MB)")
        print(f" Install via: sudo dpkg -i {app_deb} {accel_deb}")
        print("=========================================================")
    elif args.mode == "both":
        # Build split debs first
        app_deb, accel_deb = build_split_debs(version, compression=args.compression)
        # Build all-in-one with explicit name so both coexist in dist/
        all_in_one_deb = build_all_in_one_deb(version, output_name=f"voicenotes_{version}_all-in-one_amd64.deb", compression=args.compression)
        print("\n=========================================================")
        print(" [SUCCESS] All packages generated:")
        print(f" - Single all-in-one : {all_in_one_deb} ({all_in_one_deb.stat().st_size / (1024*1024):.2f} MB)")
        print(f" - Split App         : {app_deb} ({app_deb.stat().st_size / (1024*1024):.2f} MB)")
        print(f" - Split Models/Accel: {accel_deb} ({accel_deb.stat().st_size / (1024*1024):.2f} MB)")
        print("=========================================================")


if __name__ == "__main__":
    main()
