"""
Cross-platform compatibility layer for VoiceNotes.
Handles runtime library loading, Wayland/X11 display detection,
and GPU acceleration discovery (CPU, NVIDIA CUDA, AMD ROCm).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import os
import platform
import sys
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_PLATFORM_INITIALIZED = False
_ORIGINAL_FIND_LIBRARY = ctypes.util.find_library


def get_bundled_lib_dirs() -> List[Path]:
    """Return list of candidate directories containing bundled runtime libraries."""
    dirs: List[Path] = []

    # 1. PyInstaller frozen environment
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        dirs.extend([
            base / "voicenotes" / "lib",
            base / "lib",
            base,
        ])

    # 2. Source / installed package directory
    pkg_dir = Path(__file__).resolve().parent
    dirs.extend([
        pkg_dir / "lib",
        pkg_dir.parent / "lib",
    ])

    # 3. Standard Debian / system package install locations
    dirs.extend([
        Path("/usr/lib/voicenotes/lib"),
        Path("/usr/lib/voicenotes"),
        Path("/opt/voicenotes/lib"),
    ])

    return [d for d in dirs if d.is_dir()]


def _setup_linux_display_environment() -> None:
    """Configure Qt platform plugin for Wayland and X11 display servers."""
    if sys.platform != "linux":
        return

    # Check if user explicitly chose a platform
    current_qpa = os.environ.get("QT_QPA_PLATFORM")
    if current_qpa:
        return

    wayland_display = os.environ.get("WAYLAND_DISPLAY")
    xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    x11_display = os.environ.get("DISPLAY")

    if wayland_display or xdg_session == "wayland":
        # Native Wayland with seamless X11 (XWayland) fallback
        os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    elif x11_display or xdg_session == "x11":
        # Standard X11
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def _preload_linux_library(lib_name: str, candidate_paths: List[Path]) -> bool:
    """Attempt to preload a shared library using ctypes RTLD_GLOBAL."""
    # First check if the library is already loadable via system linker
    try:
        ctypes.CDLL(lib_name, mode=ctypes.RTLD_GLOBAL)
        return True
    except Exception:
        pass

    # Try explicit candidate file paths
    for base_dir in candidate_paths:
        target = base_dir / lib_name
        if target.exists():
            try:
                ctypes.CDLL(str(target), mode=ctypes.RTLD_GLOBAL)
                return True
            except Exception as e:
                logger.debug(f"Failed to preload {target}: {e}")

        # Also check versioned or unversioned variants (e.g. libxcb-cursor.so.0*)
        for match in base_dir.glob(f"{lib_name}*"):
            try:
                ctypes.CDLL(str(match), mode=ctypes.RTLD_GLOBAL)
                return True
            except Exception:
                pass

    return False


def _setup_linux_libraries() -> None:
    """Preload necessary runtime libraries like libxcb-cursor and libportaudio on Linux."""
    if sys.platform != "linux":
        return

    lib_dirs = get_bundled_lib_dirs()

    # 1. libxcb-cursor (needed by Qt 6 XCB platform plugin on Ubuntu 24.04+ / Debian)
    _preload_linux_library("libxcb-cursor.so.0", lib_dirs)

    # 2. PortAudio (libportaudio.so.2) for sounddevice recording
    portaudio_path: Optional[str] = None
    for d in lib_dirs:
        for match in d.glob("libportaudio.so*"):
            if match.is_file():
                portaudio_path = str(match)
                try:
                    ctypes.CDLL(portaudio_path, mode=ctypes.RTLD_GLOBAL)
                    break
                except Exception:
                    pass
        if portaudio_path:
            break

    # Hook find_library so sounddevice can discover portaudio if not registered in ldconfig
    def custom_find_library(name: str) -> Optional[str]:
        res = _ORIGINAL_FIND_LIBRARY(name)
        if res is not None:
            return res
        if name == "portaudio" and portaudio_path:
            return portaudio_path
        return None

    ctypes.util.find_library = custom_find_library


def _setup_cuda_libraries() -> List[str]:
    """Register CUDA library paths (NVIDIA cuBLAS, cuDNN, CUDA 12)."""
    added_paths: List[str] = []

    # Windows DLL directory registration
    if sys.platform == "win32":
        prefixes = [sys.prefix]
        base_p = getattr(sys, "base_prefix", None)
        if base_p and base_p != sys.prefix:
            prefixes.append(base_p)

        import glob
        for prefix in prefixes:
            pattern = os.path.join(prefix, "Lib", "site-packages", "nvidia", "*", "bin")
            for p in glob.glob(pattern):
                if os.path.isdir(p):
                    try:
                        os.add_dll_directory(p)
                        added_paths.append(p)
                    except Exception:
                        pass

        cuda_path = os.environ.get("CUDA_PATH")
        if cuda_path:
            bin_dir = os.path.join(cuda_path, "bin")
            if os.path.isdir(bin_dir):
                try:
                    os.add_dll_directory(bin_dir)
                    added_paths.append(bin_dir)
                except Exception:
                    pass

    # Linux shared library registration
    elif sys.platform == "linux":
        candidate_dirs: List[str] = []

        # Pip package directories (nvidia-cublas-cu12, nvidia-cudnn-cu12, etc.)
        prefixes = [sys.prefix]
        base_p = getattr(sys, "base_prefix", None)
        if base_p and base_p != sys.prefix:
            prefixes.append(base_p)

        for prefix in prefixes:
            site_pkgs = Path(prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
            nvidia_dir = site_pkgs / "nvidia"
            if nvidia_dir.is_dir():
                for sub in nvidia_dir.iterdir():
                    lib_sub = sub / "lib"
                    if lib_sub.is_dir():
                        candidate_dirs.append(str(lib_sub))

        # Standard CUDA Toolkit paths
        for std_cuda in ("/usr/local/cuda/lib64", "/usr/lib/x86_64-linux-gnu", "/opt/cuda/lib64"):
            if os.path.isdir(std_cuda):
                candidate_dirs.append(std_cuda)

        # Preload essential CUDA libraries if found
        for cdir in candidate_dirs:
            p = Path(cdir)
            for lib_name in ("libcublas.so.12", "libcublasLt.so.12", "libcudnn.so.9", "libcudnn.so.8", "libnvrtc.so.12"):
                target = p / lib_name
                if target.exists():
                    try:
                        ctypes.CDLL(str(target), mode=ctypes.RTLD_GLOBAL)
                    except Exception:
                        pass

        # Update LD_LIBRARY_PATH in current process environment
        if candidate_dirs:
            current_ld = os.environ.get("LD_LIBRARY_PATH", "")
            ld_parts = [p for p in current_ld.split(":") if p]
            for cdir in candidate_dirs:
                if cdir not in ld_parts:
                    ld_parts.append(cdir)
            os.environ["LD_LIBRARY_PATH"] = ":".join(ld_parts)
            added_paths.extend(candidate_dirs)

    return added_paths


def _setup_rocm_libraries() -> List[str]:
    """Register AMD ROCm / HIP library paths."""
    added_paths: List[str] = []
    if sys.platform != "linux":
        return added_paths

    rocm_dirs = [
        "/opt/rocm/lib",
        "/opt/rocm/hip/lib",
        "/usr/lib/x86_64-linux-gnu/rocm",
    ]

    found_dirs = [d for d in rocm_dirs if os.path.isdir(d)]
    for rdir in found_dirs:
        p = Path(rdir)
        for lib_name in ("libamdhip64.so", "librocblas.so", "libMIGraphX.so"):
            target = p / lib_name
            if target.exists():
                try:
                    ctypes.CDLL(str(target), mode=ctypes.RTLD_GLOBAL)
                except Exception:
                    pass

    if found_dirs:
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        ld_parts = [p for p in current_ld.split(":") if p]
        for rdir in found_dirs:
            if rdir not in ld_parts:
                ld_parts.append(rdir)
        os.environ["LD_LIBRARY_PATH"] = ":".join(ld_parts)
        added_paths.extend(found_dirs)

    return added_paths


def init_platform_compat() -> None:
    """Initialize all platform-specific compatibility hooks once."""
    global _PLATFORM_INITIALIZED
    if _PLATFORM_INITIALIZED:
        return

    _setup_linux_display_environment()
    _setup_linux_libraries()
    _setup_cuda_libraries()
    _setup_rocm_libraries()

    _PLATFORM_INITIALIZED = True


# --- Hardware Acceleration Discovery API ---

def is_cuda_available() -> bool:
    """Return True if NVIDIA CUDA acceleration is usable."""
    init_platform_compat()
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() <= 0:
            return False

        # Verify cuBLAS runtime loading
        if sys.platform == "win32":
            for dll in ("cublas64_12.dll", "cublas64_11.dll"):
                try:
                    ctypes.CDLL(dll)
                    return True
                except Exception:
                    pass
        else:
            for so in ("libcublas.so.12", "libcublas.so.11", "libcublas.so"):
                try:
                    ctypes.CDLL(so)
                    return True
                except Exception:
                    pass
        return False
    except Exception:
        return False


def get_cuda_device_name() -> Optional[str]:
    """Return the name of the active NVIDIA CUDA GPU."""
    if not is_cuda_available():
        return None

    # Try NVML via ctypes
    lib_names = ["nvml.dll"] if sys.platform == "win32" else ["libnvidia-ml.so.1", "libnvidia-ml.so"]
    for lib_name in lib_names:
        try:
            nvml = ctypes.CDLL(lib_name)
            nvml.nvmlInit()
            handle = ctypes.c_void_p()
            nvml.nvmlDeviceGetHandleByIndex(0, ctypes.byref(handle))
            name_buf = ctypes.create_string_buffer(128)
            nvml.nvmlDeviceGetName(handle, name_buf, 128)
            nvml.nvmlShutdown()
            name = name_buf.value.decode("utf-8").strip()
            if name:
                return name
        except Exception:
            pass

    # Fallback to nvidia-smi command
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
        first_line = out.splitlines()[0].strip() if out else ""
        if first_line:
            return first_line
    except Exception:
        pass

    return "NVIDIA CUDA GPU"


def is_rocm_available() -> bool:
    """Return True if AMD ROCm / HIP acceleration is usable."""
    init_platform_compat()
    if sys.platform != "linux":
        return False

    # Check for ROCm kernel device node
    if not os.path.exists("/dev/kfd"):
        return False

    # Check for HIP runtime library
    try:
        hip = ctypes.CDLL("libamdhip64.so")
        count = ctypes.c_int()
        # hipGetDeviceCount(&count)
        if hasattr(hip, "hipGetDeviceCount"):
            status = hip.hipGetDeviceCount(ctypes.byref(count))
            if status == 0 and count.value > 0:
                return True
    except Exception:
        pass

    # Check rocm-smi
    try:
        import subprocess
        subprocess.check_output(
            ["rocm-smi", "--showid"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return True
    except Exception:
        pass

    return False


def get_rocm_device_name() -> Optional[str]:
    """Return the name of the active AMD ROCm GPU."""
    if not is_rocm_available():
        return None

    try:
        import subprocess
        out = subprocess.check_output(
            ["rocm-smi", "--showproductname"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
        for line in out.splitlines():
            if "Card series:" in line or "Product Name:" in line:
                return line.split(":", 1)[1].strip()
    except Exception:
        pass

    try:
        # lspci search for AMD VGA/Display
        import subprocess
        out = subprocess.check_output(
            ["lspci"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
        for line in out.splitlines():
            if ("VGA" in line or "3D" in line or "Display" in line) and ("AMD" in line or "Radeon" in line):
                parts = line.split(":", 2)
                return parts[-1].strip() if len(parts) >= 3 else line.strip()
    except Exception:
        pass

    return "AMD ROCm GPU"


def get_hardware_acceleration_info() -> Tuple[str, str]:
    """
    Return (status_label, tooltip) describing current hardware acceleration engine.
    Supports NVIDIA CUDA, AMD ROCm, Apple Silicon (NEON), and CPU INT8.
    """
    if is_cuda_available():
        gpu_name = get_cuda_device_name() or "NVIDIA CUDA GPU"
        return f"⚡ NVIDIA CUDA ({gpu_name})", f"Hardware Acceleration active: {gpu_name} (float16)"

    if is_rocm_available():
        gpu_name = get_rocm_device_name() or "AMD ROCm GPU"
        return f"⚡ AMD ROCm ({gpu_name})", f"Hardware Acceleration active: {gpu_name} (float16)"

    if sys.platform == "darwin":
        try:
            import subprocess
            brand = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if brand:
                return f"⚡ Offline Ready ({brand} INT8)", f"Execution mode: {brand} (Accelerated INT8 / NEON)"
        except Exception:
            pass
        machine = platform.machine()
        if "arm" in machine.lower():
            return "⚡ Offline Ready (Apple Silicon INT8)", "Execution mode: Apple Silicon (Accelerated INT8 / NEON)"

    return "⚡ Offline Ready (CPU INT8)", "Execution mode: Optimized CPU (INT8 quantization)"
