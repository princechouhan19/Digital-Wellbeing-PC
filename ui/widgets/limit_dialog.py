from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame
)
from ui.theme import ThemeManager

class LimitReachedDialog(QDialog):
    close_app_requested = Signal(str)
    override_requested = Signal(str)
    
    def __init__(self, process_name: str, limit_seconds: int, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.process_name = process_name
        self.limit_seconds = limit_seconds
        
        self.setFixedSize(480, 320)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Smooth fade-in animation
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._setup_ui()
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        from ui.theme import ThemeManager, apply_mica
        apply_mica(int(self.winId()), ThemeManager.instance().is_dark)
        
    def showEvent(self, event):
        super().showEvent(event)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        bg_frame = QFrame()
        bg_frame.setObjectName("dialog_bg")
        
        layout = QVBoxLayout(bg_frame)
        layout.setContentsMargins(32, 32, 32, 24)
        layout.setSpacing(16)
        
        # Top Header (App Icon + Name)
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(12)
        
        from utils.icon_provider import AppIconProvider
        icon_lbl = QLabel()
        icon = AppIconProvider().get_icon(self.process_name)
        if icon and not icon.isNull():
            pixmap = icon.pixmap(64, 64)
            icon_lbl.setPixmap(pixmap)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_lbl)
        
        display_name = self.process_name.replace(".exe", "").title()
        name_lbl = QLabel(display_name)
        name_lbl.setObjectName("app_name")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(name_lbl)
        
        layout.addLayout(header_layout)
        
        # Status Text
        status_lbl = QLabel("Daily limit reached")
        status_lbl.setObjectName("status_title")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_lbl)
        
        # Stats
        stats_layout = QHBoxLayout()
        stats_layout.addStretch()
        
        tm = ThemeManager.instance()
        hrs = self.limit_seconds // 3600
        mins = (self.limit_seconds % 3600) // 60
        usage_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
        
        usage_lbl = QLabel(f"Today's usage: <span style='color: {tm.color('text_main')}; font-weight: bold;'>{usage_str}</span>")
        usage_lbl.setObjectName("stat_text")
        
        rem_lbl = QLabel(f"Remaining time: <span style='color: {tm.color('danger_text')}; font-weight: bold;'>0m</span>")
        rem_lbl.setObjectName("stat_text")
        
        stats_layout.addWidget(usage_lbl)
        stats_layout.addSpacing(24)
        stats_layout.addWidget(rem_lbl)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.btn_pin = QPushButton("Override with PIN")
        self.btn_pin.setObjectName("btn_secondary")
        self.btn_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pin.clicked.connect(self._on_enter_pin)
        
        self.btn_close = QPushButton("Close App")
        self.btn_close.setObjectName("btn_primary")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._on_close_app)
        
        btn_layout.addWidget(self.btn_pin)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        main_layout.addWidget(bg_frame)
        
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark=None):
        if is_dark is None:
            is_dark = ThemeManager.instance().is_dark
        
        bg_col = "#1A1A1C" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        app_name_col = "#F5F5F7" if is_dark else "#1D1D1F"
        stat_text_col = "#A1A1A6" if is_dark else "#48484A"
        btn_sec_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "#F5F5F7"
        btn_sec_color = "#F5F5F7" if is_dark else "#1D1D1F"
        btn_sec_border = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.12)"
        btn_sec_hover = "rgba(255, 255, 255, 0.09)" if is_dark else "#E5E5EA"

        self.setStyleSheet(f"""
            QFrame#dialog_bg {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 16px;
            }}
            QLabel#app_name {{
                font-size: 20px;
                font-weight: 700;
                color: {app_name_col};
                letter-spacing: -0.3px;
            }}
            QLabel#status_title {{
                font-size: 13px;
                font-weight: 700;
                color: #FF453A;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            QLabel#stat_text {{
                font-size: 13px;
                color: {stat_text_col};
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#btn_secondary {{
                background-color: {btn_sec_bg};
                color: {btn_sec_color};
                border: 1px solid {btn_sec_border};
            }}
            QPushButton#btn_secondary:hover {{
                background-color: {btn_sec_hover};
                border-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton#btn_primary {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF453A, stop:1 #FF3B30);
                color: #FFFFFF;
                border: 1px solid rgba(255, 69, 58, 0.4);
            }}
            QPushButton#btn_primary:hover {{
                background: #FF3B30;
                border-color: #FF453A;
            }}
        """)
        
    def _on_close_app(self) -> None:
        self.close_app_requested.emit(self.process_name)
        self.accept()
        
    def _on_enter_pin(self) -> None:
        self.override_requested.emit(self.process_name)
        self.accept()


class PinOverrideDialog(QDialog):
    override_granted = Signal(str, int)  # process_name, override_minutes
    
    def __init__(self, process_name: str, pin_manager, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.process_name = process_name
        self._pin_manager = pin_manager
        
        self.setFixedSize(400, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._setup_ui()
        
    def showEvent(self, event):
        super().showEvent(event)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        bg_frame = QFrame()
        bg_frame.setObjectName("dialog_bg")
        
        layout = QVBoxLayout(bg_frame)
        layout.setContentsMargins(32, 32, 32, 24)
        layout.setSpacing(16)
        
        title = QLabel("Require PIN Override")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Enter PIN")
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pin_input)
        
        self.error_lbl = QLabel()
        self.error_lbl.setObjectName("error")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_lbl)
        
        dur_layout = QHBoxLayout()
        dur_layout.setSpacing(8)
        for text, mins in [("15m", 15), ("30m", 30), ("1h", 60), ("Unlimited", 0)]:
            btn = QPushButton(text)
            btn.setObjectName("btn_dur")
            btn.clicked.connect(lambda _, m=mins: self._try_override(m))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dur_layout.addWidget(btn)
        
        layout.addLayout(dur_layout)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(bg_frame)
        
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark=None):
        if is_dark is None:
            is_dark = ThemeManager.instance().is_dark
            
        bg_col = "#1A1A1C" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        title_col = "#F5F5F7" if is_dark else "#1D1D1F"
        input_bg = "#232326" if is_dark else "#F5F5F7"
        input_border = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.14)"
        input_col = "#F5F5F7" if is_dark else "#1D1D1F"
        btn_dur_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "#F5F5F7"
        btn_dur_color = "#F5F5F7" if is_dark else "#1D1D1F"
        btn_dur_border = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.1)"
        cancel_col = "#A1A1A6" if is_dark else "#6E6E73"
        cancel_hover = "#F5F5F7" if is_dark else "#1D1D1F"

        self.setStyleSheet(f"""
            QFrame#dialog_bg {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 16px;
            }}
            QLabel#title {{
                font-size: 18px;
                font-weight: 700;
                color: {title_col};
                letter-spacing: -0.3px;
            }}
            QLabel#error {{
                color: #FF453A;
                font-size: 12px;
                font-weight: 700;
            }}
            QLineEdit {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 8px;
                color: {input_col};
                padding: 10px;
                font-size: 18px;
                letter-spacing: 5px;
            }}
            QLineEdit:focus {{
                border: 1px solid #0A84FF;
                background-color: {input_bg};
            }}
            QPushButton#btn_dur {{
                background-color: {btn_dur_bg};
                color: {btn_dur_color};
                border: 1px solid {btn_dur_border};
                border-radius: 8px;
                padding: 8px 0;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton#btn_dur:hover {{
                background-color: #0A84FF;
                color: #FFFFFF;
                border-color: #0A84FF;
            }}
            QPushButton#btn_cancel {{
                background-color: transparent;
                color: {cancel_col};
                border: none;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton#btn_cancel:hover {{
                color: {cancel_hover};
            }}
        """)
        
    def _try_override(self, minutes: int) -> None:
        pin = self.pin_input.text().strip()
        if not pin:
            self.error_lbl.setText("PIN cannot be empty")
            return
            
        if self._pin_manager.verify_pin(pin):
            self.override_granted.emit(self.process_name, minutes)
            self.accept()
        else:
            self.error_lbl.setText("Incorrect PIN")
            self.pin_input.clear()
