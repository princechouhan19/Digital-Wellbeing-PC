"""
update_dialog.py - UI for displaying update available and downloading.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QProgressBar, QMessageBox, QWidget
)

class UpdateDialog(QDialog):
    update_now = Signal()
    later = Signal()

    def __init__(self, current_version: str, new_version: str, notes: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.new_version = new_version
        self.notes = notes
        self._setup_ui()
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self):
        from core.constants import APP_NAME
        self.setWindowTitle("Update Available")
        self.setFixedSize(520, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        # Title Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title_lbl = QLabel(f"{APP_NAME} Update Available")
        title_lbl.setObjectName("page_title")
        title_lbl.setWordWrap(True)
        title_font = title_lbl.font()
        title_font.setPixelSize(22)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        
        subtitle_lbl = QLabel(f"A newer version of {APP_NAME} is ready to be installed.")
        subtitle_lbl.setObjectName("subtitle")
        sub_font = subtitle_lbl.font()
        sub_font.setPixelSize(14)
        subtitle_lbl.setFont(sub_font)
        
        header_layout.addWidget(title_lbl)
        header_layout.addWidget(subtitle_lbl)
        layout.addLayout(header_layout)

        # Version Comparison Container
        version_container = QWidget()
        version_container.setObjectName("version_container")
        version_layout = QHBoxLayout(version_container)
        version_layout.setContentsMargins(16, 16, 16, 16)
        
        # Current
        cur_layout = QVBoxLayout()
        cur_layout.setSpacing(2)
        cur_title = QLabel("Current version")
        cur_title.setObjectName("version_label")
        cur_val = QLabel(self.current_version)
        cur_val.setObjectName("version_val")
        cur_layout.addWidget(cur_title, alignment=Qt.AlignmentFlag.AlignCenter)
        cur_layout.addWidget(cur_val, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Arrow
        arrow_lbl = QLabel("↓")
        arrow_lbl.setObjectName("arrow")
        arrow_font = arrow_lbl.font()
        arrow_font.setPixelSize(24)
        arrow_lbl.setFont(arrow_font)
        
        # New
        new_layout = QVBoxLayout()
        new_layout.setSpacing(2)
        new_title = QLabel("New version")
        new_title.setObjectName("version_label")
        new_val = QLabel(self.new_version)
        new_val.setObjectName("new_version_val")
        new_layout.addWidget(new_title, alignment=Qt.AlignmentFlag.AlignCenter)
        new_layout.addWidget(new_val, alignment=Qt.AlignmentFlag.AlignCenter)
        
        version_layout.addStretch()
        version_layout.addLayout(cur_layout)
        version_layout.addStretch()
        version_layout.addWidget(arrow_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        version_layout.addStretch()
        version_layout.addLayout(new_layout)
        version_layout.addStretch()
        
        layout.addWidget(version_container)

        # Release Notes
        notes_lbl = QLabel("What's New")
        notes_lbl.setObjectName("notes_title")
        notes_font = notes_lbl.font()
        notes_font.setPixelSize(14)
        notes_font.setBold(True)
        notes_lbl.setFont(notes_font)
        layout.addWidget(notes_lbl)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setMarkdown(self.notes)
        layout.addWidget(self.notes_text, stretch=1)

        # Progress bar (hidden initially)
        self.progress_layout = QVBoxLayout()
        self.progress_layout.setSpacing(8)
        self.progress_lbl = QLabel("Downloading update...")
        self.progress_lbl.setVisible(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_layout.addWidget(self.progress_lbl)
        self.progress_layout.addWidget(self.progress_bar)
        layout.addLayout(self.progress_layout)

        # Buttons
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(12)
        
        from ui.widgets.fluent import FluentButton
        self.later_btn = FluentButton("Later", primary=False)
        self.later_btn.setMinimumWidth(120)
        self.later_btn.clicked.connect(self._on_later_clicked)
        
        self.update_btn = FluentButton("Update Now", primary=True)
        self.update_btn.setMinimumWidth(120)
        self.update_btn.clicked.connect(self._on_update_clicked)

        self.btn_layout.addWidget(self.later_btn)
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.update_btn)
        layout.addLayout(self.btn_layout)

    def _apply_theme(self, is_dark=None):
        try:
            from ui.theme import ThemeManager
            if is_dark is None:
                is_dark = ThemeManager.instance().is_dark
                
            bg_col = "#1A1A1C" if is_dark else "#FFFFFF"
            border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
            text_main = "#F5F5F7" if is_dark else "#1D1D1F"
            text_sub = "#A1A1A6" if is_dark else "#48484A"
            text_muted = "#6E6E73" if is_dark else "#6E6E73"
            card_bg = "#232326" if is_dark else "#F5F5F7"
            card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
            notes_bg = "#1A1A1C" if is_dark else "#F5F5F7"
            notes_border = "rgba(255, 255, 255, 0.07)" if is_dark else "rgba(0, 0, 0, 0.09)"
            scrollbar_handle = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.16)"

            self.setStyleSheet(f"""
                UpdateDialog, QDialog {{
                    background-color: {bg_col};
                    border: 1px solid {border_col};
                    border-radius: 14px;
                }}
                QLabel {{ 
                    color: {text_main}; 
                }}
                QLabel#subtitle {{
                    color: {text_sub};
                }}
                QLabel#version_label {{
                    color: {text_muted};
                    font-size: 12px;
                }}
                QLabel#version_val {{
                    color: {text_main};
                    font-size: 16px;
                    font-weight: 600;
                }}
                QLabel#new_version_val {{
                    color: #0A84FF;
                    font-size: 18px;
                    font-weight: 700;
                }}
                QLabel#arrow {{
                    color: #0A84FF;
                }}
                QWidget#version_container {{
                    background-color: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 12px;
                }}
                QTextEdit {{
                    background-color: {notes_bg};
                    color: {text_sub};
                    border: 1px solid {notes_border};
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 13px;
                }}
                QScrollBar:vertical {{
                    background: transparent;
                    width: 6px;
                    margin: 4px 2px 4px 0px;
                    border-radius: 3px;
                }}
                QScrollBar::handle:vertical {{
                    background: {scrollbar_handle};
                    min-height: 24px;
                    border-radius: 3px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: #0A84FF;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                    background: none;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: none;
                }}
                QProgressBar {{
                    background: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 6px;
                    text-align: center;
                    color: {text_main};
                }}
                QProgressBar::chunk {{
                    background-color: #0A84FF;
                    border-radius: 6px;
                }}
            """)
        except Exception:
            pass

    def _on_later_clicked(self):
        self.later.emit()
        self.reject()

    def _on_update_clicked(self):
        self.update_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.notes_text.setEnabled(False)
        
        self.progress_lbl.setVisible(True)
        self.progress_bar.setVisible(True)
        
        self.update_now.emit()

    def set_progress(self, percent: int):
        clean_ver = str(self.new_version).lstrip("vV")
        self.progress_bar.setValue(percent)
        self.progress_lbl.setText(f"Downloading Digital Wellbeing {clean_ver}... {percent}%")

    def set_installing(self, version: str = ""):
        clean_ver = str(version or self.new_version).lstrip("vV")
        self.progress_bar.setValue(100)
        self.progress_lbl.setText(f"Installing Digital Wellbeing {clean_ver}...")
        self.update_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.notes_text.setEnabled(False)

    def show_error(self, msg: str):
        self.progress_lbl.setVisible(False)
        self.progress_bar.setVisible(False)
        self.update_btn.setEnabled(True)
        self.later_btn.setEnabled(True)
        self.notes_text.setEnabled(True)
        QMessageBox.warning(self, "Update Failed", f"Update couldn't be completed.\n{msg}")
        self.reject()
