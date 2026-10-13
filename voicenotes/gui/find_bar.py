"""
Inline Find & Replace Bar for VoiceNotes Notepad Lite.
Modeled after the sleek modern Windows Notepad / VS Code inline search bar.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class FindReplaceBar(QFrame):
    """
    Inline search and replace toolbar that embeds above or below the notepad editor.
    Supports Next/Previous, Match Case, Replace, Replace All, and live match counters.
    """

    closed = pyqtSignal()

    def __init__(self, editor: QTextEdit, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.editor = editor
        self.setObjectName("findReplaceBar")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._init_ui()
        self.hide()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)

        # Row 1: Find controls
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        lbl_icon = QLabel("🔍")
        row1.addWidget(lbl_icon)

        self.edit_find = QLineEdit()
        self.edit_find.setPlaceholderText("Find in note... (Enter for next, Shift+Enter for prev)")
        self.edit_find.setMinimumWidth(220)
        self.edit_find.textChanged.connect(self._on_find_text_changed)
        self.edit_find.returnPressed.connect(self.find_next)
        row1.addWidget(self.edit_find, stretch=1)

        self.lbl_match_count = QLabel("")
        self.lbl_match_count.setStyleSheet("color: #777; font-size: 11px;")
        self.lbl_match_count.setMinimumWidth(70)
        row1.addWidget(self.lbl_match_count)

        self.btn_match_case = QPushButton("Aa")
        self.btn_match_case.setCheckable(True)
        self.btn_match_case.setToolTip("Match Case")
        self.btn_match_case.setMinimumWidth(32)
        self.btn_match_case.toggled.connect(self._on_find_text_changed)
        row1.addWidget(self.btn_match_case)

        self.btn_prev = QPushButton("↑")
        self.btn_prev.setToolTip("Previous match (Shift+Enter / Shift+F3)")
        self.btn_prev.setMinimumWidth(30)
        self.btn_prev.clicked.connect(self.find_prev)
        row1.addWidget(self.btn_prev)

        self.btn_next = QPushButton("↓")
        self.btn_next.setToolTip("Next match (Enter / F3)")
        self.btn_next.setMinimumWidth(30)
        self.btn_next.clicked.connect(self.find_next)
        row1.addWidget(self.btn_next)

        self.btn_toggle_replace = QPushButton("⇄ Replace")
        self.btn_toggle_replace.setCheckable(True)
        self.btn_toggle_replace.setToolTip("Toggle Replace Mode (Ctrl+H)")
        self.btn_toggle_replace.toggled.connect(self._on_toggle_replace)
        row1.addWidget(self.btn_toggle_replace)

        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Close Find (Esc)")
        self.btn_close.setMinimumWidth(28)
        self.btn_close.clicked.connect(self.close_bar)
        row1.addWidget(self.btn_close)

        main_layout.addLayout(row1)

        # Row 2: Replace controls (hidden by default)
        self.frame_replace = QWidget()
        row2 = QHBoxLayout(self.frame_replace)
        row2.setContentsMargins(20, 0, 0, 0)
        row2.setSpacing(6)

        self.edit_replace = QLineEdit()
        self.edit_replace.setPlaceholderText("Replace with...")
        self.edit_replace.setMinimumWidth(220)
        self.edit_replace.returnPressed.connect(self.replace_current)
        row2.addWidget(self.edit_replace, stretch=1)

        self.btn_replace = QPushButton("Replace")
        self.btn_replace.setToolTip("Replace current match")
        self.btn_replace.clicked.connect(self.replace_current)
        row2.addWidget(self.btn_replace)

        self.btn_replace_all = QPushButton("Replace All")
        self.btn_replace_all.setToolTip("Replace all occurrences in note")
        self.btn_replace_all.clicked.connect(self.replace_all)
        row2.addWidget(self.btn_replace_all)

        self.frame_replace.setVisible(False)
        main_layout.addWidget(self.frame_replace)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        super().keyPressEvent(event)

    def show_find(self, initial_query: str = ""):
        """Open the find bar, optionally pre-filling with selected text."""
        self.show()
        if initial_query:
            self.edit_find.setText(initial_query)
        self.edit_find.selectAll()
        self.edit_find.setFocus()
        self._update_match_count()

    def show_replace(self, initial_query: str = ""):
        """Open the find bar with replace controls visible."""
        self.btn_toggle_replace.setChecked(True)
        self.show_find(initial_query)

    def close_bar(self):
        """Close bar and return focus to editor."""
        self.hide()
        self.editor.setFocus()
        self.closed.emit()

    def _on_toggle_replace(self, checked: bool):
        self.frame_replace.setVisible(checked)

    def _get_find_flags(self, backward: bool = False) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        if self.btn_match_case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def _on_find_text_changed(self):
        query = self.edit_find.text()
        if not query:
            self.lbl_match_count.setText("")
            return
        self._update_match_count()
        # Find first occurrence from current position or wrap
        self.find_next(select_only=True)

    def _update_match_count(self):
        query = self.edit_find.text()
        if not query:
            self.lbl_match_count.setText("")
            return

        doc = self.editor.document()
        flags = self._get_find_flags(backward=False)

        count = 0
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(query, cursor, flags)
            if cursor.isNull():
                break
            count += 1

        if count == 0:
            self.lbl_match_count.setText("No matches")
            self.lbl_match_count.setStyleSheet("color: #d9383a; font-size: 11px;")
        else:
            self.lbl_match_count.setText(f"{count} {'match' if count == 1 else 'matches'}")
            self.lbl_match_count.setStyleSheet("color: #0067c0; font-size: 11px;")

    def find_next(self, select_only: bool = False):
        """Find next occurrence, wrapping around document if needed."""
        query = self.edit_find.text()
        if not query:
            return False

        flags = self._get_find_flags(backward=False)
        found = self.editor.find(query, flags)

        if not found:
            # Wrap around from top
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            found = self.editor.find(query, flags)

        if found:
            self.editor.ensureCursorVisible()
        return found

    def find_prev(self):
        """Find previous occurrence, wrapping around document if needed."""
        query = self.edit_find.text()
        if not query:
            return False

        flags = self._get_find_flags(backward=True)
        found = self.editor.find(query, flags)

        if not found:
            # Wrap around from end
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(cursor)
            found = self.editor.find(query, flags)

        if found:
            self.editor.ensureCursorVisible()
        return found

    def replace_current(self):
        """Replace current matching selection and jump to next."""
        query = self.edit_find.text()
        replacement = self.edit_replace.text()
        if not query:
            return

        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            match = (
                selected == query
                if self.btn_match_case.isChecked()
                else selected.lower() == query.lower()
            )
            if match:
                cursor.insertText(replacement)
                self.find_next()
                self._update_match_count()
                return

        # If no active match selection, find next match first
        if self.find_next():
            cursor = self.editor.textCursor()
            cursor.insertText(replacement)
            self.find_next()
            self._update_match_count()

    def replace_all(self):
        """Replace all occurrences in document."""
        query = self.edit_find.text()
        replacement = self.edit_replace.text()
        if not query:
            return

        doc = self.editor.document()
        flags = self._get_find_flags(backward=False)

        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        replacements = 0

        while True:
            cursor = doc.find(query, cursor, flags)
            if cursor.isNull():
                break
            cursor.insertText(replacement)
            replacements += 1

        cursor.endEditBlock()
        self._update_match_count()
        self.lbl_match_count.setText(f"Replaced {replacements}")
