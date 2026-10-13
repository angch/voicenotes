"""
UI Themes and CSS Styling for VoiceNotes (Light and Dark Windows Notepad style).
"""

from __future__ import annotations

import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QGuiApplication, QPalette

LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #f9f9f9;
}
QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #1a1a1a;
}
QMenuBar {
    background-color: #f3f3f3;
    border-bottom: 1px solid #e0e0e0;
    padding: 2px 4px;
}
QMenuBar::item {
    background-color: transparent;
    padding: 5px 8px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #e5e5e5;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
    color: #1a1a1a;
}
QMenu::item:selected {
    background-color: #0067c0;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #e0e0e0;
    margin: 4px 8px;
}
QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e5e5;
    padding: 6px 10px;
    spacing: 8px;
}
QTextEdit {
    background-color: #ffffff;
    color: #1a1a1a;
    border: none;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 14px;
    line-height: 1.6;
    padding: 16px;
    selection-background-color: #b3d7ff;
    selection-color: #000000;
}
QPushButton {
    background-color: #fbfbfb;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #f0f0f0;
    border-color: #b0b0b0;
}
QPushButton:pressed {
    background-color: #e5e5e5;
}
QPushButton:disabled {
    background-color: #f0f0f0;
    color: #a0a0a0;
    border-color: #e0e0e0;
}
QPushButton#primaryButton {
    background-color: #0067c0;
    color: #ffffff;
    border: 1px solid #005fb8;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: #005a9e;
}
QPushButton#primaryButton:pressed {
    background-color: #004b87;
}
QPushButton#primaryButton:disabled {
    background-color: #9ac2e8;
    border-color: #9ac2e8;
}
QPushButton#recordButton {
    background-color: #fff1f0;
    color: #cf1322;
    border: 1px solid #ffa39e;
    font-weight: 600;
}
QPushButton#recordButton:hover {
    background-color: #ffccc7;
}
QComboBox {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    padding: 5px 10px;
    min-width: 110px;
}
QComboBox:hover {
    border-color: #a0a0a0;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1a1a1a;
    selection-background-color: #0067c0;
    selection-color: #ffffff;
    border: 1px solid #d0d0d0;
}
QCheckBox {
    spacing: 6px;
    font-weight: 500;
    color: #1a1a1a;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #0067c0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #0067c0;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #0067c0;
}
QProgressBar {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    text-align: center;
    background-color: #f0f0f0;
    height: 14px;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #0067c0;
    border-radius: 3px;
}
QStatusBar {
    background-color: #f3f3f3;
    border-top: 1px solid #e0e0e0;
    color: #555555;
    font-size: 12px;
    padding: 2px 10px;
}
QGroupBox {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    background-color: #ffffff;
    font-weight: 600;
    color: #1a1a1a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QLineEdit {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #b3d7ff;
    selection-color: #000000;
}
QLineEdit:focus {
    border-color: #0067c0;
}
QTableWidget {
    background-color: #ffffff;
    color: #1a1a1a;
    gridline-color: #e5e5e5;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    selection-background-color: #e7f3ff;
    selection-color: #000000;
}
QTableWidget QTableCornerButton::section {
    background-color: #f3f3f3;
    border: 1px solid #e0e0e0;
}
QHeaderView::section {
    background-color: #f3f3f3;
    color: #333333;
    padding: 5px 8px;
    border: 1px solid #e0e0e0;
    font-weight: 600;
    font-size: 12px;
}
QDialogButtonBox QPushButton {
    min-width: 72px;
    padding: 5px 14px;
    color: #1a1a1a;
    background-color: #fbfbfb;
    border: 1px solid #d0d0d0;
}
QDialogButtonBox QPushButton:hover {
    background-color: #f0f0f0;
}
QSplitter::handle {
    background-color: #e0e0e0;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
#speakersPanel, SpeakersPanel {
    background-color: #f7f9fa;
    border-left: 1px solid #e0e0e0;
}
#speakersScrollArea, #speakersContainer {
    background-color: transparent;
}
#findReplaceBar, FindReplaceBar {
    background-color: #f3f3f3;
    border-bottom: 1px solid #e0e0e0;
}
#findReplaceBar QPushButton {
    padding: 2px 6px;
    min-width: 24px;
    color: #1a1a1a;
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
}
#findReplaceBar QPushButton:hover {
    background-color: #e8e8e8;
    border-color: #a0a0a0;
}
#findReplaceBar QPushButton:checked {
    background-color: #e7f3ff;
    color: #0067c0;
    border-color: #0067c0;
    font-weight: 600;
}
#editorActionBar {
    background-color: #f7f9fa;
    border-bottom: 1px solid #e0e0e0;
    padding: 3px 8px;
}
#editorActionBar QPushButton {
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    color: #1a1a1a;
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
}
#editorActionBar QPushButton:hover {
    background-color: #f0f0f0;
    border-color: #b0b0b0;
}
#editorActionBar QPushButton#btnSendVoice {
    color: #0067c0;
    background-color: #f0f7ff;
    border: 1px solid #b8d7ff;
    font-weight: 600;
}
#editorActionBar QPushButton#btnSendVoice:hover {
    background-color: #e1effe;
    border-color: #0067c0;
}
"""

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #202020;
}
QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #e0e0e0;
}
QMenuBar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #333333;
    padding: 2px 4px;
}
QMenuBar::item {
    background-color: transparent;
    padding: 5px 8px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #333333;
}
QMenu {
    background-color: #262626;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
    color: #e0e0e0;
}
QMenu::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #3a3a3a;
    margin: 4px 8px;
}
QToolBar {
    background-color: #262626;
    border-bottom: 1px solid #333333;
    padding: 6px 10px;
    spacing: 8px;
}
QTextEdit {
    background-color: #1e1e1e;
    color: #f0f0f0;
    border: none;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 14px;
    line-height: 1.6;
    padding: 16px;
    selection-background-color: #004b87;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
    color: #f0f0f0;
}
QPushButton:hover {
    background-color: #383838;
    border-color: #505050;
}
QPushButton:pressed {
    background-color: #404040;
}
QPushButton:disabled {
    background-color: #252525;
    color: #666666;
    border-color: #333333;
}
QPushButton#primaryButton {
    background-color: #0078d4;
    color: #ffffff;
    border: 1px solid #0086ea;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: #1084d8;
}
QPushButton#primaryButton:pressed {
    background-color: #006cbe;
}
QPushButton#primaryButton:disabled {
    background-color: #004b87;
    border-color: #004b87;
    color: #8cb8df;
}
QPushButton#recordButton {
    background-color: #3f1a1a;
    color: #ff7875;
    border: 1px solid #5c2223;
    font-weight: 600;
}
QPushButton#recordButton:hover {
    background-color: #5c2223;
}
QComboBox {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    padding: 5px 10px;
    min-width: 110px;
    color: #f0f0f0;
}
QComboBox:hover {
    border-color: #555555;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #262626;
    selection-background-color: #0078d4;
    color: #f0f0f0;
    border: 1px solid #3d3d3d;
}
QCheckBox {
    spacing: 6px;
    font-weight: 500;
    color: #f0f0f0;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #3a3a3a;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #0078d4;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #0078d4;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #0078d4;
}
QProgressBar {
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    text-align: center;
    background-color: #262626;
    height: 14px;
    font-size: 11px;
    color: #e0e0e0;
}
QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}
QStatusBar {
    background-color: #1e1e1e;
    border-top: 1px solid #333333;
    color: #888888;
    font-size: 12px;
    padding: 2px 10px;
}
QGroupBox {
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    background-color: #262626;
    font-weight: 600;
    color: #f0f0f0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QLineEdit {
    background-color: #262626;
    color: #f0f0f0;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border-color: #0078d4;
}
QTableWidget {
    background-color: #1e1e1e;
    color: #f0f0f0;
    gridline-color: #333333;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    selection-background-color: #182a3d;
    selection-color: #ffffff;
}
QTableWidget QTableCornerButton::section {
    background-color: #262626;
    border: 1px solid #333333;
}
QHeaderView::section {
    background-color: #262626;
    color: #d0d0d0;
    padding: 5px 8px;
    border: 1px solid #333333;
    font-weight: 600;
    font-size: 12px;
}
QDialogButtonBox QPushButton {
    min-width: 72px;
    padding: 5px 14px;
    color: #f0f0f0;
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
}
QDialogButtonBox QPushButton:hover {
    background-color: #383838;
}
QSplitter::handle {
    background-color: #333333;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
#speakersPanel, SpeakersPanel {
    background-color: #202020;
    border-left: 1px solid #333333;
}
#speakersScrollArea, #speakersContainer {
    background-color: transparent;
}
#findReplaceBar, FindReplaceBar {
    background-color: #262626;
    border-bottom: 1px solid #333333;
}
#findReplaceBar QPushButton {
    padding: 2px 6px;
    min-width: 24px;
    color: #f0f0f0;
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}
#findReplaceBar QPushButton:hover {
    background-color: #383838;
    border-color: #505050;
}
#findReplaceBar QPushButton:checked {
    background-color: #182a3d;
    color: #4dabf7;
    border-color: #0078d4;
    font-weight: 600;
}
#editorActionBar {
    background-color: #252525;
    border-bottom: 1px solid #333333;
    padding: 3px 8px;
}
#editorActionBar QPushButton {
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    color: #e0e0e0;
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
}
#editorActionBar QPushButton:hover {
    background-color: #383838;
    border-color: #505050;
}
#editorActionBar QPushButton#btnSendVoice {
    color: #63b3ed;
    background-color: #162438;
    border: 1px solid #2b4c7e;
    font-weight: 600;
}
#editorActionBar QPushButton#btnSendVoice:hover {
    background-color: #1c3352;
    border-color: #3182ce;
}
"""


def get_system_theme() -> str:
    """
    Detect whether the host OS is currently configured for dark or light mode.
    Queries Qt 6 style hints first, followed by OS-specific APIs/registries.
    """
    # 1. Qt 6 styleHints colorScheme (Windows 10/11, macOS, Linux portal)
    try:
        app = QGuiApplication.instance()
        if app is not None:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
            if scheme == Qt.ColorScheme.Light:
                return "light"
    except Exception:
        pass

    # 2. Windows registry: AppsUseLightTheme (0 = Dark, 1 = Light)
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "dark" if value == 0 else "light"
        except Exception:
            pass

    # 3. macOS defaults
    if sys.platform == "darwin":
        try:
            import subprocess

            out = subprocess.check_output(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            if "Dark" in out:
                return "dark"
        except Exception:
            pass

    # 4. Linux desktop color-scheme
    if sys.platform.startswith("linux"):
        try:
            import subprocess

            out = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            if "prefer-dark" in out:
                return "dark"
        except Exception:
            pass

    return "light"


def get_effective_theme(theme_preference: Optional[str] = None) -> str:
    """
    Resolve the concrete theme ('light' or 'dark').
    If theme_preference is 'system' (or omitted/None), resolves to the current OS theme.
    """
    if not theme_preference or theme_preference == "system":
        return get_system_theme()
    return "dark" if theme_preference == "dark" else "light"


def create_palette(theme: str = "light") -> QPalette:
    """
    Create a Qt standard QPalette for unstyled or native Qt widgets
    matching the resolved light or dark color scheme.
    """
    pal = QPalette()
    if theme == "dark":
        pal.setColor(QPalette.ColorRole.Window, QColor("#202020"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#262626"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2d2d2d"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#2d2d2d"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#f0f0f0"))
        pal.setColor(QPalette.ColorRole.BrightText, QColor("#ff4d4f"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#0078d4"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    else:
        pal.setColor(QPalette.ColorRole.Window, QColor("#f9f9f9"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f3f3f3"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#fbfbfb"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1a1a1a"))
        pal.setColor(QPalette.ColorRole.BrightText, QColor("#cf1322"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#0067c0"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    return pal


def get_stylesheet(theme: str = "light") -> str:
    """Return the CSS stylesheet for the requested or resolved theme."""
    eff = get_effective_theme(theme)
    return DARK_THEME if eff == "dark" else LIGHT_THEME

