from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QDialog, QLineEdit, QComboBox, QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont, QIcon
from ui.widgets.fluent import FluentLabel
from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager
from ui.icons import get_icon, get_pixmap
from utils.website_icon_provider import WebsiteIconProvider

class WebsiteTimerItem(QFrame):
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, domain: str, limit_s: int, used_s: float, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.limit_s = limit_s
        self.used_s = used_s
        self._provider = WebsiteIconProvider()
        self.setObjectName("website_item")
        # Removing absolute height, let it size automatically
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setup_ui()
        self._apply_theme()
        self._provider.icon_ready.connect(self._on_icon_ready)

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # Website Logo / Favicon
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(32, 32)
        icon = self._provider.get_icon(self.domain, size=32)
        if not icon.isNull():
            self.icon_lbl.setPixmap(icon.pixmap(QSize(32, 32)))
        layout.addWidget(self.icon_lbl)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        tm = ThemeManager.instance()
        
        self.domain_lbl = QLabel(self.domain)
        self.domain_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {tm.color('text_main')};")
        
        limit_str = AnalyticsEngine.format_duration_short(self.limit_s)
        used_str = AnalyticsEngine.format_duration_short(self.used_s)
        self.stats_lbl = QLabel(f"Used {used_str} of {limit_str}")
        self.stats_lbl.setStyleSheet(f"font-size: 13px; color: {tm.color('text_sub')};")
        
        info_layout.addWidget(self.domain_lbl)
        info_layout.addWidget(self.stats_lbl)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("btn_delete")
        self.btn_delete.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.domain))
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.domain))
        
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_icon_ready(self, domain: str, icon: QIcon) -> None:
        if WebsiteIconProvider.normalize_domain(domain) == WebsiteIconProvider.normalize_domain(self.domain):
            if not icon.isNull():
                self.icon_lbl.setPixmap(icon.pixmap(QSize(32, 32)))

    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#website_item {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#website_item:hover {{
                background-color: {tm.color('card_hover')};
                border: 1px solid {tm.color('border_hover')};
            }}
            QPushButton {{
                background-color: {tm.color('window_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 6px;
                color: {tm.color('text_main')};
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {tm.color('card_hover')};
                border: 1px solid {tm.color('border_hover')};
            }}
            QPushButton:pressed {{
                background-color: {tm.color('card_pressed')};
            }}
            QPushButton#btn_delete {{
                color: {tm.color('danger_text')};
            }}
            QPushButton#btn_delete:hover {{
                background-color: {tm.color('danger_bg')};
                border: 1px solid {tm.color('danger_border')};
            }}
        """)

class WebsiteTimerConfigDialog(QDialog):
    """
    Apple-style modal sheet for configuring website daily time limits.
    Supports smooth mouse drag-to-move, live favicon preview, Apple duration presets,
    and works with both `rule: dict` and `limit_s: int` caller arguments.
    """

    def __init__(
        self,
        parent=None,
        domain: str = "",
        rule: dict = None,
        browser_name: str = "",
        browser_process: str = "",
        limit_s: int = 0,
    ):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.domain = domain
        self.rule = dict(rule) if rule else {}
        if limit_s > 0 and "limit_seconds" not in self.rule:
            self.rule["limit_seconds"] = limit_s
        self.browser_name = browser_name
        self.browser_process = browser_process
        self._drag_pos = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 460)
        self.setup_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos") and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _set_preset(self, h: int, m: int):
        self.hours_combo.setCurrentText(str(h))
        self.mins_combo.setCurrentText(str(m))

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)  # Space for drop shadow

        self.container = QFrame()
        self.container.setObjectName("dialogContainer")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 1. Apple Draggable Header Bar
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)

        icon_frame = QFrame()
        icon_frame.setFixedSize(36, 36)
        icon_frame.setObjectName("hdr_icon_frame")
        if_layout = QVBoxLayout(icon_frame)
        if_layout.setContentsMargins(0, 0, 0, 0)
        if_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        globe_icon = QLabel()
        globe_icon.setPixmap(get_pixmap("globe", color="#30D158", size=20))
        if_layout.addWidget(globe_icon)
        hdr_row.addWidget(icon_frame)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        if self.browser_name:
            title_text = f"Configure Website Limit — {self.browser_name}"
        elif self.domain:
            title_text = "Configure Website Limit"
        else:
            title_text = "Add Website Limit"

        title = QLabel(title_text)
        title.setObjectName("titleLbl")
        subtitle = QLabel("Set a daily usage allowance across web browsers.")
        subtitle.setObjectName("subLbl")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hdr_row.addLayout(title_box, 1)

        # Close button in top-right
        self.btn_close = QPushButton()
        self.btn_close.setObjectName("apple_close_btn")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setIcon(get_icon("close", color="#8E8E93", size=11))
        self.btn_close.clicked.connect(self.reject)
        hdr_row.addWidget(self.btn_close)

        layout.addLayout(hdr_row)

        # 2. Inset Grouped Section for Domain
        domain_card = QFrame()
        domain_card.setObjectName("apple_inset_card")
        domain_card_layout = QVBoxLayout(domain_card)
        domain_card_layout.setContentsMargins(16, 14, 16, 14)
        domain_card_layout.setSpacing(8)

        lbl_domain = QLabel("WEBSITE DOMAIN")
        lbl_domain.setObjectName("section_eyebrow")
        domain_card_layout.addWidget(lbl_domain)

        domain_input_layout = QHBoxLayout()
        domain_input_layout.setSpacing(10)

        self.domain_icon_lbl = QLabel()
        self.domain_icon_lbl.setFixedSize(28, 28)
        domain_input_layout.addWidget(self.domain_icon_lbl)

        self.domain_input = QLineEdit()
        self.domain_input.setObjectName("apple_input")
        self.domain_input.setPlaceholderText("e.g. instagram.com or youtube.com")
        if self.domain:
            self.domain_input.setText(self.domain)
            self.domain_input.setEnabled(False)

        domain_input_layout.addWidget(self.domain_input, 1)
        domain_card_layout.addLayout(domain_input_layout)
        layout.addWidget(domain_card)

        self._provider = WebsiteIconProvider()
        self._provider.icon_ready.connect(self._on_dialog_icon_ready)
        self.domain_input.textChanged.connect(self._on_domain_text_changed)
        self._update_icon_preview(self.domain_input.text())

        # 3. Inset Grouped Section for Daily Limit
        limit_card = QFrame()
        limit_card.setObjectName("apple_inset_card")
        limit_card_layout = QVBoxLayout(limit_card)
        limit_card_layout.setContentsMargins(16, 14, 16, 14)
        limit_card_layout.setSpacing(12)

        lbl_limit = QLabel("DAILY TIME ALLOWANCE")
        lbl_limit.setObjectName("section_eyebrow")
        limit_card_layout.addWidget(lbl_limit)

        time_h_layout = QHBoxLayout()
        time_h_layout.setSpacing(16)

        self.hours_combo = QComboBox()
        self.hours_combo.setObjectName("apple_combo")
        self.hours_combo.addItems([str(i) for i in range(24)])
        self.mins_combo = QComboBox()
        self.mins_combo.setObjectName("apple_combo")
        self.mins_combo.addItems([str(i) for i in range(0, 60, 5)])

        limit_s = self.rule.get("limit_seconds", 1800)
        h = limit_s // 3600
        m = (limit_s % 3600) // 60
        self.hours_combo.setCurrentText(str(h))
        m_snap = (m // 5) * 5
        self.mins_combo.setCurrentText(str(m_snap))

        # Hours Picker Box
        h_layout = QHBoxLayout()
        h_layout.setSpacing(6)
        h_layout.addWidget(self.hours_combo, 1)
        h_unit = QLabel("hours")
        h_unit.setObjectName("unit_lbl")
        h_layout.addWidget(h_unit)

        # Minutes Picker Box
        m_layout = QHBoxLayout()
        m_layout.setSpacing(6)
        m_layout.addWidget(self.mins_combo, 1)
        m_unit = QLabel("minutes")
        m_unit.setObjectName("unit_lbl")
        m_layout.addWidget(m_unit)

        time_h_layout.addLayout(h_layout)
        time_h_layout.addLayout(m_layout)
        limit_card_layout.addLayout(time_h_layout)

        # Apple Segmented Presets Capsule
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        presets = [("15m", 0, 15), ("30m", 0, 30), ("1h", 1, 0), ("2h", 2, 0), ("No Limit", 0, 0)]
        for plabel, ph, pm_val in presets:
            pbtn = QPushButton(plabel)
            pbtn.setObjectName("presetPillBtn")
            pbtn.setCursor(Qt.CursorShape.PointingHandCursor)
            pbtn.clicked.connect(lambda _, h_val=ph, m_val=pm_val: self._set_preset(h_val, m_val))
            preset_row.addWidget(pbtn)
        limit_card_layout.addLayout(preset_row)

        layout.addWidget(limit_card)

        layout.addStretch()

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_cancel_pill")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Set Limit")
        self.btn_save.setObjectName("btn_primary_pill")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        main_layout.addWidget(self.container)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark=None):
        if is_dark is None:
            is_dark = ThemeManager.instance().is_dark
        tm = ThemeManager.instance()

        bg_col = "#1E1E20" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"
        card_bg = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.035)"
        card_border = "rgba(255, 255, 255, 0.07)" if is_dark else "rgba(0, 0, 0, 0.07)"
        input_bg = "#28282B" if is_dark else "#F5F5F7"
        input_border = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.12)"
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")

        self.btn_close.setIcon(get_icon("close", color=text_sub, size=11))

        self.setStyleSheet(f"""
            QFrame#dialogContainer {{
                background-color: {bg_col};
                border-radius: 20px;
                border: 1px solid {border_col};
            }}
            QFrame#hdr_icon_frame {{
                background-color: rgba(48, 209, 88, 0.14);
                border: 1px solid rgba(48, 209, 88, 0.32);
                border-radius: 10px;
            }}
            QLabel#titleLbl {{
                font-size: 18px;
                font-weight: 700;
                letter-spacing: -0.4px;
                color: {text_main};
                font-family: "Inter Display", "Inter", sans-serif;
            }}
            QLabel#subLbl {{
                font-size: 12px;
                font-weight: 500;
                color: {text_sub};
            }}
            QLabel#section_eyebrow {{
                font-size: 10px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.2px;
            }}
            QLabel#unit_lbl {{
                font-size: 13px;
                font-weight: 600;
                color: {text_sub};
            }}
            QFrame#apple_inset_card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 14px;
            }}
            QLineEdit#apple_input, QComboBox#apple_combo {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 9px;
                color: {text_main};
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QLineEdit#apple_input:focus, QComboBox#apple_combo:focus {{
                border: 1.5px solid #0A84FF;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QPushButton#apple_close_btn {{
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }}
            QPushButton#apple_close_btn:hover {{
                background-color: rgba(255, 69, 58, 0.18);
                border-color: rgba(255, 69, 58, 0.4);
            }}
            QPushButton#presetPillBtn {{
                background-color: {input_bg};
                color: {text_sub};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#presetPillBtn:hover {{
                background-color: rgba(10, 132, 255, 0.16);
                color: #0A84FF;
                border-color: #0A84FF;
            }}
            QPushButton#btn_cancel_pill {{
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid {card_border};
                border-radius: 19px;
                color: {text_sub};
                font-size: 13px;
                font-weight: 600;
                padding: 9px 20px;
            }}
            QPushButton#btn_cancel_pill:hover {{
                background-color: {tm.color('card_hover')};
                color: {text_main};
            }}
            QPushButton#btn_primary_pill {{
                background-color: #0A84FF;
                border: none;
                border-radius: 19px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 24px;
            }}
            QPushButton#btn_primary_pill:hover {{
                background-color: #409CFF;
            }}
        """)

    def _on_domain_text_changed(self, text: str) -> None:
        self._update_icon_preview(text)

    def _update_icon_preview(self, text: str) -> None:
        norm = WebsiteIconProvider.normalize_domain(text)
        if norm and "." in norm:
            icon = self._provider.get_icon(norm, size=28)
            if not icon.isNull():
                self.domain_icon_lbl.setPixmap(icon.pixmap(QSize(28, 28)))
                self.domain_icon_lbl.show()
                return
        self.domain_icon_lbl.hide()

    def _on_dialog_icon_ready(self, domain: str, icon: QIcon) -> None:
        current = WebsiteIconProvider.normalize_domain(self.domain_input.text())
        if current and current == WebsiteIconProvider.normalize_domain(domain):
            if not icon.isNull():
                self.domain_icon_lbl.setPixmap(icon.pixmap(QSize(28, 28)))
                self.domain_icon_lbl.show()

    def get_data(self):
        h = int(self.hours_combo.currentText())
        m = int(self.mins_combo.currentText())
        limit_s = h * 3600 + m * 60
        domain = self.domain_input.text().strip().lower()
        if domain.startswith("http"):
            domain = domain.split("//")[-1].split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]

        return domain, {
            "limit_seconds": limit_s,
            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
            "notifications": [15, 10, 5, 1],
            "on_expire": "lock",
        }

class WebsiteTimersSection(QWidget):
    def __init__(self, protection_manager, process_name: str, parent=None):
        super().__init__(parent)
        self.pm = protection_manager
        self.process_name = process_name
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        title = FluentLabel("Website Timers", FluentLabel.Style.HEADING)
        self.btn_add = QPushButton("+ Add Website")
        self.btn_add.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        tm = ThemeManager.instance()
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {tm.color('accent')};
                color: white;
                border-radius: 16px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {tm.color('accent_hover')}; }}
            QPushButton:pressed {{ background-color: {tm.color('accent')}; }}
        """)
        self.btn_add.clicked.connect(self._on_add)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_add)
        
        self.layout.addLayout(header_layout)
        
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(12)
        self.layout.addLayout(self.list_layout)
        
        self.refresh()

    def refresh(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not self.pm:
            return
            
        limits = self.pm.website_limits.get_all_limits(self.process_name)
        if not limits:
            lbl = QLabel("No website timers configured.\nClick '+ Add Website' to create one.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tm = ThemeManager.instance()
            lbl.setStyleSheet(f"color: {tm.color('text_sub')}; font-size: 14px; padding: 40px; background: {tm.color('card_bg')}; border-radius: 12px; border: 1px dashed {tm.color('border')};")
            self.list_layout.addWidget(lbl)
            return
            
        for domain, rule in limits.items():
            limit_s = rule.get("limit_seconds", 0)
            used_s = self.pm.website_timer.get_time(domain)
            item = WebsiteTimerItem(domain, limit_s, used_s)
            item.edit_requested.connect(self._on_edit)
            item.delete_requested.connect(self._on_delete)
            self.list_layout.addWidget(item)

    def _on_add(self):
        dialog = WebsiteTimerConfigDialog(self.window())
        if dialog.exec():
            domain, rule = dialog.get_data()
            if domain and rule["limit_seconds"] > 0:
                self.pm.website_limits.set_limit_rule(self.process_name, domain, rule)
                self.refresh()

    def _on_edit(self, domain: str):
        rule = self.pm.website_limits.get_all_limits(self.process_name).get(domain, {})
        dialog = WebsiteTimerConfigDialog(self.window(), domain=domain, rule=rule)
        if dialog.exec():
            _, rule = dialog.get_data()
            if rule["limit_seconds"] > 0:
                self.pm.website_limits.set_limit_rule(self.process_name, domain, rule)
                self.refresh()

    def _on_delete(self, domain: str):
        self.pm.website_limits.set_limit_rule(self.process_name, domain, None)
        self.refresh()
