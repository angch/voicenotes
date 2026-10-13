"""
UI Themes and CSS Styling for VoiceNotes (Light and Dark Windows Notepad style).
"""

LIGHT_THEME = """
QMainWindow {
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
QCheckBox {
    spacing: 6px;
    font-weight: 500;
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
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
"""

DARK_THEME = """
QMainWindow {
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
"""


def get_stylesheet(theme: str = "light") -> str:
    """Return the CSS stylesheet for the requested theme."""
    return DARK_THEME if theme == "dark" else LIGHT_THEME
