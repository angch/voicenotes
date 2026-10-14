"""
Vocabulary Panel widget for VoiceNotes.
Displays active voice -> preferred text replacement rules below the Speakers panel.
Enables quick adding, editing, and deletion of custom vocabulary, terms, and names.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from voicenotes.config import config
from voicenotes.gui.dialogs import SetPreferredSpellingDialog
from voicenotes.gui.styles import get_effective_theme


class VocabularyCard(QFrame):
    """Card representing a single voice -> preferred text rule."""

    deleted = pyqtSignal(str)  # (original)
    edited = pyqtSignal(str, str, bool)  # (original, replacement, case_sensitive)

    def __init__(
        self,
        original: str,
        replacement: str,
        case_sensitive: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.original = original
        self.replacement = replacement
        self.case_sensitive = case_sensitive

        is_dark = get_effective_theme(config.get("theme", "system")) == "dark"
        bg_color = "#25282e" if is_dark else "#f3f6f9"
        border_col = "#383c44" if is_dark else "#dbe1e8"
        accent_col = "#4dabf7" if is_dark else "#0067c0"
        orig_col = "#e2e8f0" if is_dark else "#2d3748"
        btn_del_col = "#e53e3e" if is_dark else "#c53030"

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"""
            VocabularyCard {{
                background-color: {bg_color};
                border: 1px solid {border_col};
                border-left: 3px solid {accent_col};
                border-radius: 5px;
                margin-bottom: 4px;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Content layout: original ➔ replacement
        content_box = QVBoxLayout()
        content_box.setContentsMargins(0, 0, 0, 0)
        content_box.setSpacing(2)

        row_text = QHBoxLayout()
        row_text.setSpacing(6)

        lbl_orig = QLabel(self.original)
        lbl_orig.setStyleSheet(f"font-weight: 600; color: {orig_col}; font-size: 12px;")
        lbl_orig.setToolTip(f"Original / Misheard text: '{self.original}'")
        row_text.addWidget(lbl_orig)

        lbl_arrow = QLabel("➔")
        lbl_arrow.setStyleSheet("color: #888888; font-weight: bold; font-size: 11px;")
        row_text.addWidget(lbl_arrow)

        lbl_repl = QLabel(self.replacement)
        lbl_repl.setStyleSheet(f"font-weight: bold; color: {accent_col}; font-size: 12px;")
        lbl_repl.setToolTip(f"Preferred spelling: '{self.replacement}'")
        row_text.addWidget(lbl_repl)

        row_text.addStretch(1)
        content_box.addLayout(row_text)

        if self.case_sensitive:
            lbl_case = QLabel("Match exact case")
            lbl_case.setStyleSheet("color: #888888; font-size: 10px; font-style: italic;")
            content_box.addWidget(lbl_case)

        layout.addLayout(content_box, stretch=1)

        # Action Buttons: Edit and Delete
        btn_edit = QPushButton("✏")
        btn_edit.setFixedSize(22, 22)
        btn_edit.setToolTip("Edit preferred spelling rule")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; font-size: 11px; color: {orig_col}; }} "
            f"QPushButton:hover {{ background-color: {'#333842' if is_dark else '#e2e8f0'}; border-radius: 3px; }}"
        )
        btn_edit.clicked.connect(self._on_edit)
        layout.addWidget(btn_edit)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(22, 22)
        btn_del.setToolTip("Delete this rule")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; font-weight: bold; font-size: 12px; color: {btn_del_col}; }} "
            f"QPushButton:hover {{ background-color: {'#4a2020' if is_dark else '#fed7d7'}; border-radius: 3px; }}"
        )
        btn_del.clicked.connect(lambda: self.deleted.emit(self.original))
        layout.addWidget(btn_del)

    def _on_edit(self):
        dlg = SetPreferredSpellingDialog(
            original=self.original,
            replacement=self.replacement,
            case_sensitive=self.case_sensitive,
            parent=self.window(),
        )
        if dlg.exec():
            orig, repl, case_sens = dlg.get_data()
            self.edited.emit(orig, repl, case_sens)


class VocabularyPanel(QWidget):
    """
    Panel widget displayed beneath the Speakers panel.
    Lists all active voice -> preferred text mappings and provides direct management.
    """

    rule_added = pyqtSignal(str, str, bool)
    rule_deleted = pyqtSignal(str)
    rule_edited = pyqtSignal(str, str, bool)
    vocabulary_imported = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("vocabularyPanel")
        self.setMinimumWidth(210)

        self._init_ui()
        self.reload_rules()

    def _init_ui(self):
        is_dark = get_effective_theme(config.get("theme", "system")) == "dark"
        bg_color = "#202020" if is_dark else "#f7f9fa"
        border_color = "#333333" if is_dark else "#e0e0e0"

        self.setStyleSheet(
            f"#vocabularyPanel {{ background-color: {bg_color}; border-left: 1px solid {border_color}; border-top: 1px solid {border_color}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header Row 1: Title + Count + Add button
        header = QHBoxLayout()
        header.setSpacing(4)

        lbl_icon = QLabel("🔤")
        lbl_icon.setStyleSheet("font-size: 14px;")
        header.addWidget(lbl_icon)

        self.lbl_title = QLabel("Preferred Words")
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 12px;")
        header.addWidget(self.lbl_title)

        self.lbl_count = QLabel("(0)")
        self.lbl_count.setStyleSheet("color: #888888; font-size: 11px;")
        header.addWidget(self.lbl_count)

        header.addStretch(1)

        self.btn_add = QPushButton("+ Add")
        self.btn_add.setToolTip("Add a new voice -> preferred spelling rule")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setStyleSheet(
            """
            QPushButton {
                font-size: 11px;
                font-weight: 600;
                padding: 3px 6px;
                border-radius: 4px;
            }
            """
        )
        self.btn_add.clicked.connect(self._on_add_clicked)
        header.addWidget(self.btn_add)

        layout.addLayout(header)

        # Header Row 2: Import & Export quick action buttons
        tools_row = QHBoxLayout()
        tools_row.setSpacing(4)

        self.btn_import = QPushButton("📥 Import...")
        self.btn_import.setToolTip("Import vocabulary rules from a JSON, CSV, or TXT file")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.setStyleSheet("font-size: 11px; padding: 2px 6px; border-radius: 4px;")
        self.btn_import.clicked.connect(self._on_import_clicked)
        tools_row.addWidget(self.btn_import)

        self.btn_export = QPushButton("📤 Export...")
        self.btn_export.setToolTip("Export current vocabulary rules to a JSON or CSV file")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet("font-size: 11px; padding: 2px 6px; border-radius: 4px;")
        self.btn_export.clicked.connect(self._on_export_clicked)
        tools_row.addWidget(self.btn_export)

        tools_row.addStretch(1)
        layout.addLayout(tools_row)

        # Scroll Area for rules
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("vocabScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.viewport().setObjectName("vocabViewport")
        self.scroll_area.viewport().setAutoFillBackground(False)

        self.cards_container = QWidget()
        self.cards_container.setObjectName("vocabContainer")
        self.cards_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(2, 2, 2, 2)
        self.cards_layout.setSpacing(4)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, stretch=1)

    def _on_add_clicked(self):
        dlg = SetPreferredSpellingDialog(parent=self.window())
        if dlg.exec():
            orig, repl, case_sens = dlg.get_data()
            self.rule_added.emit(orig, repl, case_sens)

    def _on_export_clicked(self):
        rules = config.get("vocabulary_replacements", [])
        if not rules:
            QMessageBox.information(
                self.window(),
                "Export Vocabulary",
                "There are no vocabulary rules to export. Add some rules first!",
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.window(),
            "Export Vocabulary Rules",
            "custom_vocabulary.json",
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*.*)",
        )
        if file_path:
            from voicenotes.engine.vocabulary import VocabularyManager

            vm = VocabularyManager()
            count = vm.export_to_file(file_path)
            QMessageBox.information(
                self.window(),
                "Export Complete",
                f"Successfully exported {count} vocabulary rule(s) to:\n{file_path}",
            )

    def _on_import_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.window(),
            "Import Vocabulary Rules",
            "",
            "Vocabulary Files (*.json *.csv *.tsv *.txt);;JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)",
        )
        if not file_path:
            return

        from voicenotes.engine.vocabulary import VocabularyManager

        vm = VocabularyManager()
        existing_count = len(vm.get_rules())

        merge = True
        if existing_count > 0:
            res = QMessageBox.question(
                self.window(),
                "Import Vocabulary",
                f"You currently have {existing_count} active vocabulary rule(s).\n\n"
                "Do you want to merge imported rules with your existing vocabulary?\n\n"
                "• Click 'Yes' to Merge (keep existing and add/update imported)\n"
                "• Click 'No' to Replace all existing rules\n"
                "• Click 'Cancel' to abort",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if res == QMessageBox.StandardButton.Cancel:
                return
            merge = res == QMessageBox.StandardButton.Yes

        try:
            imported_count, total_count = vm.import_from_file(file_path, merge=merge)
            self.reload_rules()
            self.vocabulary_imported.emit(imported_count)
            QMessageBox.information(
                self.window(),
                "Import Complete",
                f"Successfully imported {imported_count} rule(s).\nTotal active rules: {total_count}",
            )
        except Exception as e:
            QMessageBox.critical(
                self.window(),
                "Import Error",
                f"Failed to import vocabulary rules:\n{e}",
            )

    def reload_rules(self):
        """Populate panel with current rules from configuration."""
        raw_rules = config.get("vocabulary_replacements", [])
        rules = [r for r in raw_rules if isinstance(r, dict) and r.get("original") and r.get("replacement")]

        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.hide()
                widget.deleteLater()

        self.lbl_count.setText(f"({len(rules)})")

        if not rules:
            lbl_placeholder = QLabel(
                "No preferred words yet.\nSelect any word in the transcript to set its spelling, or click '+ Add'."
            )
            lbl_placeholder.setWordWrap(True)
            lbl_placeholder.setStyleSheet(
                "color: #888888; font-style: italic; font-size: 11px; padding: 12px 4px;"
            )
            self.cards_layout.addWidget(lbl_placeholder)
            return

        for r in rules:
            card = VocabularyCard(
                original=r["original"],
                replacement=r["replacement"],
                case_sensitive=bool(r.get("case_sensitive", False)),
            )
            card.deleted.connect(self.rule_deleted.emit)
            card.edited.connect(self.rule_edited.emit)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch(1)

    def refresh(self):
        """Refresh panel styling to match current theme."""
        is_dark = get_effective_theme(config.get("theme", "system")) == "dark"
        bg_color = "#202020" if is_dark else "#f7f9fa"
        border_color = "#333333" if is_dark else "#e0e0e0"

        self.setStyleSheet(
            f"#vocabularyPanel {{ background-color: {bg_color}; border-left: 1px solid {border_color}; border-top: 1px solid {border_color}; }}"
        )
        self.scroll_area.setStyleSheet(
            f"#vocabScrollArea {{ background-color: {bg_color}; border: none; }}"
        )
        self.scroll_area.viewport().setStyleSheet(
            f"#vocabViewport {{ background-color: {bg_color}; border: none; }}"
        )
        self.cards_container.setStyleSheet(
            f"#vocabContainer {{ background-color: {bg_color}; border: none; }}"
        )

        self.reload_rules()
