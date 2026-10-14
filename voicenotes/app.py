"""
Application launcher and entry point for VoiceNotes.
Supports both GUI mode (default for desktop users) and CLI mode (for automated workflows).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from voicenotes import __app_name__, __version__
from voicenotes.config import get_app_icon_path
from voicenotes.engine.transcriber import SpeechTranscriber, setup_cuda_dll_paths
from voicenotes.export.exporters import save_export_to_file
from voicenotes.gui.main_window import MainWindow


def run_cli(args: argparse.Namespace) -> int:
    """Run transcription in CLI headless mode."""
    setup_cuda_dll_paths()
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}", file=sys.stderr)
        return 1

    print(f"[{__app_name__} CLI v{__version__}]")
    print(f"Processing: {audio_path.name}")
    print(f"Model: {args.model} | Diarization: {args.diarize} | Language: {args.language}")

    transcriber = SpeechTranscriber()

    def progress_cb(msg: str, pct: int):
        print(f"[{pct:3d}%] {msg}")

    result = transcriber.transcribe(
        audio_source=audio_path,
        model_name=args.model,
        language=args.language,
        diarize=args.diarize,
        num_speakers=args.speakers,
        progress_callback=progress_cb,
    )

    print("\n--- TRANSCRIPTION RESULT ---")
    print(result.full_text)
    print("----------------------------\n")

    if args.output:
        out_path = Path(args.output)
        fmt = args.format or out_path.suffix.lstrip(".").lower() or "txt"
        save_export_to_file(result, out_path, format_type=fmt)
        print(f"Saved output to: {out_path} ({fmt.upper()})")

    return 0


def setup_macos_app_name():
    """Ensure the macOS system menu bar displays 'VoiceNotes' instead of 'Python'."""
    if sys.platform != "darwin":
        return

    try:
        from Foundation import NSBundle, NSProcessInfo

        proc = NSProcessInfo.processInfo()
        proc.setProcessName_(__app_name__)

        bundle = NSBundle.mainBundle()
        info = bundle.infoDictionary()
        if info is not None:
            info["CFBundleName"] = __app_name__
            info["CFBundleDisplayName"] = __app_name__
    except Exception:
        pass


def update_macos_main_menu():
    """Update Cocoa NSApplication main menu title if running on macOS."""
    if sys.platform != "darwin":
        return

    try:
        from AppKit import NSApplication

        ns_app = NSApplication.sharedApplication()
        menu = ns_app.mainMenu()
        if menu and menu.numberOfItems() > 0:
            first_item = menu.itemAtIndex_(0)
            first_item.setTitle_(__app_name__)
            if first_item.hasSubmenu():
                first_item.submenu().setTitle_(__app_name__)
    except Exception:
        pass


def run_gui(initial_audio: str | None = None) -> int:
    """Run desktop application GUI."""
    setup_cuda_dll_paths()
    setup_macos_app_name()

    # Windows high-DPI and taskbar integration
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "VoiceNotes.NotepadLite.App.1.0"
            )
        except Exception:
            pass

    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtGui import QGuiApplication

    QCoreApplication.setApplicationName(__app_name__)
    QCoreApplication.setOrganizationName("VoiceNotes")

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    QGuiApplication.setApplicationDisplayName(__app_name__)

    icon_path = get_app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    if initial_audio and Path(initial_audio).exists():
        window.load_audio_file(str(Path(initial_audio).resolve()))

    window.show()
    update_macos_main_menu()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="voicenotes",
        description=f"{__app_name__} - Offline Speech Transcriber with Speaker Diarization",
    )
    parser.add_argument("audio", nargs="?", help="Audio or video file to open or transcribe")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode instead of GUI")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium"], help="Whisper model to use")
    parser.add_argument("--language", default="auto", help="Language code (e.g. en, es, zh, auto)")
    parser.add_argument("--no-diarize", dest="diarize", action="store_false", help="Disable speaker diarization")
    parser.add_argument("--speakers", default="auto", help="Number of speakers hint (auto, 2, 3...)")
    parser.add_argument("-o", "--output", help="Output file path (e.g. transcript.txt, transcript.srt)")
    parser.add_argument("-f", "--format", choices=["txt", "srt", "vtt", "json", "md"], help="Export format")
    parser.set_defaults(diarize=True)

    args = parser.parse_args()

    if args.cli:
        if not args.audio:
            parser.error("Audio file path required when using --cli mode")
        return run_cli(args)

    return run_gui(initial_audio=args.audio)


if __name__ == "__main__":
    sys.exit(main())
