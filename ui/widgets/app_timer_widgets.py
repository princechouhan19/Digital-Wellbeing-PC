from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QRectF, QPointF, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialog, QFrame, QScrollArea, QGraphicsOpacityEffect, QSpinBox,
    QGraphicsDropShadowEffect, QLineEdit
)

from ui.theme import ThemeManager
from ui.icons import get_icon, get_pixmap
from ui.widgets.fluent import FluentButton, FluentLabel, ToggleSwitch

class WheelPicker(QWidget):
    """A modern, animated scroll wheel picker."""
    value_changed = Signal(int)

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 160)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._items = items
        self._current_index = 0
        self._scroll_offset = 0.0  # in pixels
        self._item_height = 40
        self._is_dragging = False
        self._last_y = 0
        
        self._anim = QPropertyAnimation(self, b"scroll_offset", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(0.0)

    @Property(float)
    def scroll_offset(self):
        return self._scroll_offset

    @scroll_offset.setter
    def scroll_offset(self, val):
        self._scroll_offset = val
        self.update()

    def set_index(self, index: int):
        self._current_index = max(0, min(len(self._items) - 1, index))
        self._scroll_offset = self._current_index * self._item_height
        self.update()

    def get_index(self) -> int:
        return self._current_index
        
    def _snap_to_index(self):
        idx = round(self._scroll_offset / self._item_height)
        idx = max(0, min(len(self._items) - 1, idx))
        self._current_index = idx
        self.value_changed.emit(idx)
        
        self._anim.stop()
        self._anim.setStartValue(self._scroll_offset)
        self._anim.setEndValue(idx * self._item_height)
        self._anim.start()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        self._scroll_offset -= delta * 0.2
        
        # Clamp bounds
        max_offset = (len(self._items) - 1) * self._item_height
        self._scroll_offset = max(0, min(max_offset, self._scroll_offset))
        self.update()
        
        if hasattr(self, "_snap_timer"):
            self._snap_timer.stop()
        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.timeout.connect(self._snap_to_index)
        self._snap_timer.start(200)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._last_y = event.position().y()
            self._anim.stop()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging:
            dy = event.position().y() - self._last_y
            self._scroll_offset -= dy
            self._last_y = event.position().y()
            
            max_offset = (len(self._items) - 1) * self._item_height
            self._scroll_offset = max(-self._item_height, min(max_offset + self._item_height, self._scroll_offset))
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._snap_to_index()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        
        h = self.height()
        w = self.width()
        center_y = h / 2.0
        
        font = self.font()
        font.setPixelSize(22)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        
        for i, item in enumerate(self._items):
            item_y_center = center_y + (i * self._item_height) - self._scroll_offset
            dist = abs(center_y - item_y_center)
            
            if dist > h / 2.0 + self._item_height:
                continue
                
            scale = max(0.6, 1.0 - (dist / (h / 1.2)))
            alpha = max(0, int(255 * (1.0 - (dist / (h / 2.0)))))
            
            painter.save()
            painter.translate(w/2, item_y_center)
            painter.scale(scale, scale)
            
            color = QColor(tm.color('text_main'))
            color.setAlpha(alpha)
            painter.setPen(color)
            
            rect = QRectF(-w/2, -self._item_height/2, w, self._item_height)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, item)
            painter.restore()


class CircularChip(QPushButton):
    """An animated circular chip for selecting repeat days."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(28, 28)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._bg_alpha = 0.0
        self._anim = QPropertyAnimation(self, b"bg_alpha", self)
        self._anim.setDuration(180)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        
        self.toggled.connect(self._on_toggled)

    @Property(float)
    def bg_alpha(self):
        return self._bg_alpha

    @bg_alpha.setter
    def bg_alpha(self, val):
        self._bg_alpha = val
        self.update()

    def _on_toggled(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._bg_alpha)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        
        # Draw background circle
        bg_color = QColor(tm.color('accent'))
        bg_color.setAlpha(int(255 * self._bg_alpha))
        
        painter.setPen(Qt.PenStyle.NoPen)
        if self._bg_alpha > 0:
            painter.setBrush(QBrush(bg_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
        painter.drawEllipse(1, 1, self.width()-2, self.height()-2)
        
        # Draw outline if not fully selected
        if self._bg_alpha < 1.0:
            border_color = QColor(tm.color('border'))
            painter.setPen(QPen(border_color, 1))
            painter.drawEllipse(1, 1, self.width()-2, self.height()-2)

        # Draw text
        text_color = QColor("#FFFFFF") if self._bg_alpha > 0.5 else QColor(tm.color('text_main'))
        painter.setPen(text_color)
        font = self.font()
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class RepeatDaysPicker(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self._days = ["M", "T", "W", "T", "F", "S", "S"]
        self._chips = []
        for d in self._days:
            chip = CircularChip(d)
            chip.setChecked(True)
            self._chips.append(chip)
            layout.addWidget(chip)
            
        layout.addStretch()

    def get_selected_days(self) -> list[int]:
        return [i for i, c in enumerate(self._chips) if c.isChecked()]

    def set_selected_days(self, days: list[int]):
        for i, c in enumerate(self._chips):
            c.setChecked(i in days)
            c._bg_alpha = 1.0 if c.isChecked() else 0.0


class SegmentedActionChoice(QWidget):
    """Compact Apple-style 3-way segmented control for expiry action."""
    action_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._selected = "lock"
        self._buttons = {}
        
        actions = [
            ("Close App", "close"),
            ("Lock Screen", "lock"),
            ("PIN Override", "pin"),
        ]
        for label, val in actions:
            btn = QPushButton(label)
            btn.setObjectName("action_segment_btn")
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, v=val: self.set_selected(v))
            self._buttons[val] = btn
            self._layout.addWidget(btn, 1)

    def set_selected(self, val: str):
        if val not in self._buttons:
            val = "lock"
        self._selected = val
        for v, b in self._buttons.items():
            is_active = (v == val)
            b.setChecked(is_active)
            b.setProperty("active", "true" if is_active else "false")
            b.style().unpolish(b)
            b.style().polish(b)
        self.action_changed.emit(val)

    def get_selected(self) -> str:
        return self._selected


class RadioCard(QFrame):
    """A beautiful Apple-styled radio card for selections."""
    clicked = Signal(str)
    
    def __init__(self, title: str, desc: str, value: str, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        self.value = value
        self._is_selected = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 48, 10)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.desc_lbl = QLabel(desc)
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.desc_lbl)
        
        self._scale = 1.0
        self._anim = QPropertyAnimation(self, b"scale", self)
        self._anim.setDuration(150)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.97)
        
    @Property(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val
        self.update()

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update()

    def mousePressEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(0.97)
        self._anim.start()

    def mouseReleaseEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.clicked.emit(self.value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        
        center = QRectF(self.rect()).center()
        painter.translate(center)
        painter.scale(self._scale, self._scale)
        
        rect = QRectF(-self.width()/2, -self.height()/2, self.width(), self.height())
        
        card_bg = "#2C2C2E" if is_dark else "#FFFFFF"
        card_hover_bg = "#353538" if is_dark else "#F5F5F7"
        border_col = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        accent_col = tm.color('accent', '#0A84FF')
        
        if self._is_selected:
            painter.setBrush(QBrush(QColor(card_hover_bg)))
            painter.setPen(QPen(QColor(accent_col), 1.5))
            self.title_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {accent_col};")
        else:
            painter.setBrush(QBrush(QColor(card_bg)))
            painter.setPen(QPen(QColor(border_col), 1))
            self.title_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {tm.color('text_main')};")
            
        self.desc_lbl.setStyleSheet(f"font-size: 12px; color: {tm.color('text_sub')};")
            
        painter.drawRoundedRect(rect, 10, 10)
        
        # Draw radio circle indicator on right
        radio_r = 8.0
        radio_cx = self.width() / 2 - 24
        radio_cy = 0.0
        if self._is_selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(accent_col)))
            painter.drawEllipse(QPointF(radio_cx, radio_cy), radio_r, radio_r)
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawEllipse(QPointF(radio_cx, radio_cy), 3.0, 3.0)
        else:
            unsel_border = "rgba(255, 255, 255, 0.3)" if is_dark else "rgba(0, 0, 0, 0.25)"
            painter.setPen(QPen(QColor(unsel_border), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(radio_cx, radio_cy), radio_r, radio_r)


class RadioCardGroup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        self._cards = []

    def add_card(self, title: str, desc: str, value: str):
        card = RadioCard(title, desc, value)
        card.clicked.connect(self.set_selected)
        self._cards.append(card)
        self.layout.addWidget(card)

    def set_selected(self, value: str):
        for card in self._cards:
            card.set_selected(card.value == value)

    def get_selected(self) -> str:
        for card in self._cards:
            if card._is_selected:
                return card.value
        return ""


class TwoDigitSpinBox(QSpinBox):
    """Custom spin box formatted with zero-padding (e.g. 01, 15) and compact Apple proportions."""
    def __init__(self, max_val: int, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setRange(0, max_val)
        self.setObjectName("duration_spin")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(34)
        self.setFixedWidth(54)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool = True):
        tm = ThemeManager.instance()
        bg = "#080C14" if is_dark else "#FFFFFF"
        border = "rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.15)"
        text_col = "#FFFFFF" if is_dark else "#1D1D1F"
        focus_bg = "#0E131E" if is_dark else "#F5F5F7"
        accent = tm.color("accent", "#0A84FF")
        self.setStyleSheet(f"""
            QSpinBox#duration_spin {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 7px;
                color: {text_col};
                font-size: 16px;
                font-weight: 700;
                padding: 2px;
            }}
            QSpinBox#duration_spin:focus {{
                border: 1.5px solid {accent};
                background-color: {focus_bg};
            }}
        """)

    def textFromValue(self, val: int) -> str:
        return f"{val:02d}"

    def valueFromText(self, text: str) -> int:
        try:
            return int(text.strip())
        except Exception:
            return 0


class PresetChipRow(QWidget):
    preset_selected = Signal(int)  # minutes, or -1 for custom
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self._btn_map = {}
        presets = [("15m", 15), ("30m", 30), ("1h", 60), ("2h", 120), ("None", 0)]
        for label, val in presets:
            btn = QPushButton(label)
            btn.setObjectName("preset_chip")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, v=val: self._on_btn_clicked(v))
            layout.addWidget(btn)
            self._btn_map[val] = btn
            
        layout.addStretch()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _on_btn_clicked(self, val: int):
        self.set_active_value(val)
        if val != -1:
            self.preset_selected.emit(val)

    def set_active_value(self, val: int):
        target = val if val in self._btn_map else -1
        for v, btn in self._btn_map.items():
            is_match = (v == target)
            btn.setChecked(is_match)
            btn.setProperty("active", "true" if is_match else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
    def _apply_theme(self, is_dark):
        tm = ThemeManager.instance()
        chip_bg = "#3A3A3C" if is_dark else "#E5E5EA"
        chip_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        chip_color = "#E5E5EA" if is_dark else "#3A3A3C"
        chip_hover = "#48484A" if is_dark else "#D1D1D6"
        accent = tm.color("accent", "#0A84FF")
        self.setStyleSheet(f"""
            QPushButton#preset_chip {{
                background: {chip_bg};
                border: 1px solid {chip_border};
                border-radius: 13px;
                padding: 0 11px;
                color: {chip_color};
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton#preset_chip:hover {{
                background: {chip_hover};
                color: {tm.color('text_main')};
            }}
            QPushButton#preset_chip[active="true"], QPushButton#preset_chip:checked {{
                background: rgba(10, 132, 255, 0.22);
                border: 1.5px solid {accent};
                color: {accent};
                font-weight: 700;
            }}
        """)


class MultiSelectChipRow(QWidget):
    def __init__(self, items: list[tuple[str, int]], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self._chips = []
        for label, val in items:
            btn = QPushButton(label)
            btn.setObjectName("alert_chip")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(26)
            btn.setProperty("val", val)
            self._chips.append(btn)
            layout.addWidget(btn)
            
        layout.addStretch()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark):
        tm = ThemeManager.instance()
        chip_bg = "#3A3A3C" if is_dark else "#E5E5EA"
        chip_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        chip_color = "#E5E5EA" if is_dark else "#3A3A3C"
        chip_hover = "#48484A" if is_dark else "#D1D1D6"
        accent = tm.color("accent", "#0A84FF")
        self.setStyleSheet(f"""
            QPushButton#alert_chip {{
                background: {chip_bg};
                border: 1px solid {chip_border};
                border-radius: 13px;
                padding: 0 10px;
                color: {chip_color};
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton#alert_chip:hover {{
                background: {chip_hover};
                color: {tm.color('text_main')};
            }}
            QPushButton#alert_chip:checked {{
                background: {accent};
                color: #FFFFFF;
                border: none;
                font-weight: 700;
            }}
        """)
        
    def get_selected(self) -> list[int]:
        return [btn.property("val") for btn in self._chips if btn.isChecked()]
        
    def set_selected(self, values: list[int]):
        for btn in self._chips:
            btn.setChecked(btn.property("val") in values)


class TimerConfigDialog(QDialog):
    """
    Apple-style compact modal sheet for configuring an application daily timer.
    Optimized for zero-horizontal and zero-vertical scrolling on standard screens,
    mouse drag-to-move, macOS Sequoia grouped cards, and compact controls.
    """
    def __init__(self, parent=None, current_rule: dict = None):
        if parent is not None and hasattr(parent, "window"):
            parent = parent.window()
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 520)
        self._drag_pos = None
        
        self.current_rule = current_rule or {}
        
        self._setup_ui()
        self._populate_data()

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

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)  # Space for soft Apple drop shadow
        
        self.container = QFrame()
        self.container.setObjectName("dialogContainer")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 16, 20, 16)
        container_layout.setSpacing(10)
        
        # 1. Header Row
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(10)
        
        icon_frame = QFrame()
        icon_frame.setFixedSize(32, 32)
        icon_frame.setObjectName("hdr_icon_frame")
        if_layout = QVBoxLayout(icon_frame)
        if_layout.setContentsMargins(0, 0, 0, 0)
        if_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_icon = QLabel()
        t_icon.setPixmap(get_pixmap("timer", color="#FF9F0A", size=18))
        if_layout.addWidget(t_icon)
        hdr_row.addWidget(icon_frame)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Configure App Timer")
        title.setObjectName("titleLbl")
        subtitle = QLabel("Set daily active time allowance and expiration behavior.")
        subtitle.setObjectName("subLbl")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hdr_row.addLayout(title_box, 1)
        
        # Close button
        self.btn_close = QPushButton()
        self.btn_close.setObjectName("apple_close_btn")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setIcon(get_icon("close", color="#8E8E93", size=10))
        self.btn_close.clicked.connect(self.reject)
        hdr_row.addWidget(self.btn_close)
        
        container_layout.addLayout(hdr_row)
        
        # 2. Scrollable Content Area with strict NO horizontal scrolling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 2, 0, 2)
        scroll_layout.setSpacing(10)
        
        # Card 1: Time Allowance & Quick Presets
        card_dur = QFrame()
        card_dur.setObjectName("apple_inset_card")
        dur_layout = QVBoxLayout(card_dur)
        dur_layout.setContentsMargins(14, 12, 14, 12)
        dur_layout.setSpacing(8)
        
        lbl_dur = QLabel("DAILY TIME ALLOWANCE")
        lbl_dur.setObjectName("section_eyebrow")
        dur_layout.addWidget(lbl_dur)
        
        picker_layout = QHBoxLayout()
        picker_layout.setSpacing(10)
        picker_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Hours stepper: [ - ] [ 01 ] [ + ] hr
        hr_box = QHBoxLayout()
        hr_box.setSpacing(4)
        btn_hr_dec = QPushButton("−")
        btn_hr_dec.setObjectName("stepper_btn")
        btn_hr_dec.setFixedSize(28, 34)
        btn_hr_dec.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hr_picker = TwoDigitSpinBox(23)
        btn_hr_inc = QPushButton("+")
        btn_hr_inc.setObjectName("stepper_btn")
        btn_hr_inc.setFixedSize(28, 34)
        btn_hr_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hr_dec.clicked.connect(lambda: self.hr_picker.setValue(self.hr_picker.value() - 1))
        btn_hr_inc.clicked.connect(lambda: self.hr_picker.setValue(self.hr_picker.value() + 1))
        hr_lbl = QLabel("hr")
        hr_lbl.setObjectName("duration_unit_lbl")
        hr_box.addWidget(btn_hr_dec)
        hr_box.addWidget(self.hr_picker)
        hr_box.addWidget(btn_hr_inc)
        hr_box.addWidget(hr_lbl)
        picker_layout.addLayout(hr_box)
        
        picker_layout.addSpacing(6)
        
        # Minutes stepper: [ - ] [ 00 ] [ + ] min
        min_box = QHBoxLayout()
        min_box.setSpacing(4)
        btn_min_dec = QPushButton("−")
        btn_min_dec.setObjectName("stepper_btn")
        btn_min_dec.setFixedSize(28, 34)
        btn_min_dec.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_picker = TwoDigitSpinBox(59)
        btn_min_inc = QPushButton("+")
        btn_min_inc.setObjectName("stepper_btn")
        btn_min_inc.setFixedSize(28, 34)
        btn_min_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_min_dec.clicked.connect(lambda: self.min_picker.setValue(self.min_picker.value() - 1))
        btn_min_inc.clicked.connect(lambda: self.min_picker.setValue(self.min_picker.value() + 1))
        min_lbl = QLabel("min")
        min_lbl.setObjectName("duration_unit_lbl")
        min_box.addWidget(btn_min_dec)
        min_box.addWidget(self.min_picker)
        min_box.addWidget(btn_min_inc)
        min_box.addWidget(min_lbl)
        picker_layout.addLayout(min_box)
        picker_layout.addStretch()
        
        dur_layout.addLayout(picker_layout)
        
        # Presets row
        self.preset_row = PresetChipRow()
        self.preset_row.preset_selected.connect(self._on_preset)
        dur_layout.addWidget(self.preset_row)
        
        # Compact Timer Name input (optional)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        lbl_name = QLabel("Label:")
        lbl_name.setObjectName("duration_sub_lbl")
        name_row.addWidget(lbl_name)
        self.name_input = QLineEdit()
        self.name_input.setObjectName("timer_name_input")
        self.name_input.setPlaceholderText("Optional (e.g. Work App, Social Limit)")
        self.name_input.setFixedHeight(30)
        name_row.addWidget(self.name_input, 1)
        dur_layout.addLayout(name_row)
        
        scroll_layout.addWidget(card_dur)
        
        self.hr_picker.valueChanged.connect(self._on_spin_changed)
        self.min_picker.valueChanged.connect(self._on_spin_changed)
        
        # Card 2: Schedule & Enforcement
        card_rules = QFrame()
        card_rules.setObjectName("apple_inset_card")
        rules_layout = QVBoxLayout(card_rules)
        rules_layout.setContentsMargins(14, 12, 14, 12)
        rules_layout.setSpacing(10)
        
        # Repeat Schedule Row
        days_header = QHBoxLayout()
        days_header.setSpacing(8)
        lbl_sched = QLabel("REPEAT SCHEDULE")
        lbl_sched.setObjectName("section_eyebrow")
        days_header.addWidget(lbl_sched)
        days_header.addStretch()
        lbl_everyday = QLabel("Every Day")
        lbl_everyday.setObjectName("duration_sub_lbl")
        days_header.addWidget(lbl_everyday)
        self.every_day_toggle = ToggleSwitch()
        self.every_day_toggle.toggled.connect(self._on_every_day_toggled)
        days_header.addWidget(self.every_day_toggle)
        rules_layout.addLayout(days_header)
        
        self.days_picker = RepeatDaysPicker()
        rules_layout.addWidget(self.days_picker)
        
        # Expiry Action Segment Control
        lbl_action = QLabel("WHEN TIMER EXPIRES")
        lbl_action.setObjectName("section_eyebrow")
        rules_layout.addWidget(lbl_action)
        
        self.action_group = SegmentedActionChoice()
        rules_layout.addWidget(self.action_group)
        
        # Alerts Row
        alerts_header = QHBoxLayout()
        lbl_alerts = QLabel("NOTIFICATION ALERTS")
        lbl_alerts.setObjectName("section_eyebrow")
        alerts_header.addWidget(lbl_alerts)
        alerts_header.addStretch()
        rules_layout.addLayout(alerts_header)
        
        self.alerts_row = MultiSelectChipRow([("15m before", 15), ("10m before", 10), ("5m before", 5), ("1m before", 1)])
        rules_layout.addWidget(self.alerts_row)
        
        scroll_layout.addWidget(card_rules)
        
        scroll.setWidget(scroll_content)
        container_layout.addWidget(scroll, 1)
        
        # 3. Apple Action Footer
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("apple_btn_cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save Timer")
        save_btn.setObjectName("apple_btn_save")
        save_btn.setFixedHeight(34)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        container_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool):
        tm = ThemeManager.instance()
        dialog_bg = "#1C1C1E" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"
        card_bg = "#2C2C2E" if is_dark else "#F2F2F7"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        input_bg = "#1C1C1E" if is_dark else "#FFFFFF"
        input_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        text_main = "#F5F5F7" if is_dark else "#1D1D1F"
        text_sub = "#8E8E93" if is_dark else "#6E6E73"
        stepper_bg = "#3A3A3C" if is_dark else "#E5E5EA"
        stepper_border = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"
        stepper_text = "#FFFFFF" if is_dark else "#1D1D1F"
        close_bg = "#2C2C2E" if is_dark else "#E5E5EA"
        close_hover = "#3A3A3C" if is_dark else "#D1D1D6"
        cancel_bg = "#2C2C2E" if is_dark else "#E5E5EA"
        cancel_hover = "#3A3A3C" if is_dark else "#D1D1D6"
        cancel_text = "#F5F5F7" if is_dark else "#1D1D1F"
        accent = tm.color("accent", "#0A84FF")
        accent_hover = "#0071E3"
        scrollbar_handle = "rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.18)"

        self.setStyleSheet(f"""
            QFrame#dialogContainer {{
                background-color: {dialog_bg};
                border: 1px solid {border_col};
                border-radius: 20px;
            }}
            QFrame#hdr_icon_frame {{
                background-color: rgba(255, 159, 10, 0.15);
                border-radius: 10px;
            }}
            QLabel#titleLbl {{
                font-size: 17px;
                font-weight: 700;
                color: {text_main};
                font-family: -apple-system, "SF Pro Display", "Inter", sans-serif;
            }}
            QLabel#subLbl {{
                font-size: 12px;
                color: {text_sub};
            }}
            QPushButton#apple_close_btn {{
                background-color: {close_bg};
                border: none;
                border-radius: 14px;
            }}
            QPushButton#apple_close_btn:hover {{
                background-color: {close_hover};
            }}
            QFrame#apple_inset_card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 14px;
            }}
            QLabel#section_eyebrow {{
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.6px;
                color: {text_sub};
            }}
            QLineEdit#timer_name_input {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 10px;
                padding: 0 12px;
                color: {text_main};
                font-size: 14px;
            }}
            QLineEdit#timer_name_input:focus {{
                border: 1.5px solid {accent};
            }}
            QLabel#duration_sub_lbl {{
                font-size: 12px;
                color: {text_sub};
            }}
            QLabel#duration_unit_lbl {{
                font-size: 13px;
                font-weight: 600;
                color: {text_sub};
            }}
            QPushButton#action_segment_btn {{
                background-color: {stepper_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 0 10px;
                color: {text_sub};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#action_segment_btn:hover {{
                background-color: {cancel_hover};
                color: {text_main};
            }}
            QPushButton#action_segment_btn[active="true"], QPushButton#action_segment_btn:checked {{
                background-color: {accent};
                border: 1px solid {accent};
                color: #FFFFFF;
                font-weight: 700;
            }}
            QPushButton#stepper_btn {{
                background-color: {stepper_bg};
                border: 1px solid {stepper_border};
                border-radius: 8px;
                color: {stepper_text};
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton#stepper_btn:hover {{
                background-color: rgba(10, 132, 255, 0.20);
                border-color: {accent};
                color: {accent};
            }}
            QPushButton#stepper_btn:pressed {{
                background-color: rgba(10, 132, 255, 0.35);
            }}
            QPushButton#apple_btn_cancel {{
                background-color: {cancel_bg};
                border: 1px solid {stepper_border};
                border-radius: 10px;
                padding: 0 18px;
                color: {cancel_text};
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#apple_btn_cancel:hover {{
                background-color: {cancel_hover};
            }}
            QPushButton#apple_btn_save {{
                background-color: {accent};
                border: none;
                border-radius: 10px;
                padding: 0 22px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#apple_btn_save:hover {{
                background-color: {accent_hover};
            }}
            QPushButton#apple_btn_save:pressed {{
                background-color: #005BB5;
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
                background: {accent};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

    def _on_every_day_toggled(self, checked: bool):
        if checked:
            self.days_picker.set_selected_days([0,1,2,3,4,5,6])

    def _on_spin_changed(self):
        total_mins = (self.hr_picker.value() * 60) + self.min_picker.value()
        self.preset_row.set_active_value(total_mins)

    def _on_preset(self, mins: int):
        if mins < 0:
            return  # Custom duration
        self.hr_picker.blockSignals(True)
        self.min_picker.blockSignals(True)
        self.hr_picker.setValue(mins // 60)
        self.min_picker.setValue(mins % 60)
        self.hr_picker.blockSignals(False)
        self.min_picker.blockSignals(False)
        self.preset_row.set_active_value(mins)

    def _populate_data(self):
        secs = self.current_rule.get("limit_seconds", 0)
        mins = secs // 60
        self.hr_picker.setValue(mins // 60)
        self.min_picker.setValue(mins % 60)
        self.preset_row.set_active_value(mins)
        
        self.name_input.setText(self.current_rule.get("name", ""))
        
        days = self.current_rule.get("repeat_days", [0,1,2,3,4,5,6])
        self.days_picker.set_selected_days(days)
        self.every_day_toggle.setChecked(len(days) == 7)
        
        notifs = self.current_rule.get("notifications", [15, 5, 1])
        self.alerts_row.set_selected(notifs)
        
        action = self.current_rule.get("on_expire", "lock")
        self.action_group.set_selected(action)

    def get_rule(self) -> dict:
        total_secs = (self.hr_picker.value() * 3600) + (self.min_picker.value() * 60)
        if total_secs == 0:
            return None # Unlimited
            
        return {
            "name": self.name_input.text().strip(),
            "limit_seconds": total_secs,
            "repeat_days": self.days_picker.get_selected_days(),
            "notifications": sorted(self.alerts_row.get_selected(), reverse=True),
            "on_expire": self.action_group.get_selected()
        }


class TimerDisplayCard(QFrame):
    """The summary card shown on App Details page displaying current timer (Samsung style)."""
    change_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timer_summary_card")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header area
        header_frame = QFrame()
        header_frame.setObjectName("timer_header")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        self.title_lbl = FluentLabel("App Timer", FluentLabel.Style.HEADING)
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        
        from ui.theme import ThemeManager
        self.status_lbl = FluentLabel("Disabled", FluentLabel.Style.MUTED)
        self.status_lbl.setStyleSheet(f"font-weight: 700; color: {ThemeManager.instance().color('text_sub')};")
        header_layout.addWidget(self.status_lbl)
        
        # Body area
        body_frame = QFrame()
        body_layout = QVBoxLayout(body_frame)
        body_layout.setContentsMargins(24, 20, 24, 24)
        body_layout.setSpacing(12)
        
        # Grid for stats
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(16)
        
        def add_stat(row, title, val_widget):
            lbl = FluentLabel(title, FluentLabel.Style.SUBHEADING)
            lbl.setFixedWidth(120)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val_widget, row, 1)
            
        self.val_limit = FluentLabel("Unlimited", FluentLabel.Style.BODY)
        self.val_repeats = FluentLabel("-", FluentLabel.Style.BODY)
        self.val_alerts = FluentLabel("-", FluentLabel.Style.BODY)
        self.val_action = FluentLabel("-", FluentLabel.Style.BODY)
        
        # Style values slightly bolder
        for w in [self.val_limit, self.val_repeats, self.val_alerts, self.val_action]:
            w.setStyleSheet("font-weight: 500;")
            
        add_stat(0, "Daily Limit", self.val_limit)
        add_stat(1, "Repeats", self.val_repeats)
        add_stat(2, "Alerts", self.val_alerts)
        add_stat(3, "Action", self.val_action)
        
        body_layout.addLayout(grid)
        
        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setObjectName("divider")
        body_layout.addSpacing(12)
        body_layout.addWidget(div)
        body_layout.addSpacing(12)
        
        # Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.change_btn = FluentButton("Edit Timer")
        self.change_btn.clicked.connect(self.change_requested.emit)
        btn_layout.addWidget(self.change_btn)
        body_layout.addLayout(btn_layout)
        
        main_layout.addWidget(header_frame)
        main_layout.addWidget(body_frame)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#timer_summary_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#timer_header {{
                background-color: {tm.color('card_hover')};
                border-bottom: 1px solid {tm.color('border')};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            QFrame#divider {{
                background-color: {tm.color('border')};
            }}
        """)

    def set_limit(self, rule: dict):
        if not rule or not rule.get("limit_seconds"):
            self.title_lbl.setText("App Timer")
            self.status_lbl.setText("Disabled")
            self.status_lbl.setStyleSheet(f"font-weight: 700; color: {ThemeManager.instance().color('text_muted')};")
            self.val_limit.setText("Unlimited")
            self.val_repeats.setText("-")
            self.val_alerts.setText("-")
            self.val_action.setText("-")
            self.change_btn.setText("Configure App Timer")
            return
            
        name = rule.get("name", "").strip()
        self.title_lbl.setText(name if name else "App Timer")
            
        self.status_lbl.setText("Enabled")
        self.status_lbl.setStyleSheet(f"font-weight: 700; color: {ThemeManager.instance().color('accent')};")
        
        secs = rule.get("limit_seconds", 0)
        hrs = secs // 3600
        mns = (secs % 3600) // 60
        if hrs > 0 and mns > 0:
            self.val_limit.setText(f"{hrs}h {mns}m")
        elif hrs > 0:
            self.val_limit.setText(f"{hrs}h")
        else:
            self.val_limit.setText(f"{mns}m")
            
        days = rule.get("repeat_days", [0,1,2,3,4,5,6])
        days_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        days_str = " ".join(days_map[d] for d in sorted(days)) if len(days) < 7 else "Every day"
        self.val_repeats.setText(days_str)
        
        action = rule.get("on_expire", "lock")
        action_str = "Close App" if action == "close" else "Ask for PIN" if action == "pin" else "Lock Screen"
        self.val_action.setText(action_str)
        
        notifs = rule.get("notifications", [])
        notifs_str = " • ".join(str(n)+'m' for n in sorted(notifs, reverse=True)) if notifs else "None"
        self.val_alerts.setText(notifs_str)
        
        self.change_btn.setText("Edit Timer")


class AnimatedProgressBar(QWidget):
    """Smooth animated progress bar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self._progress = 0.0
        
        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)

    @Property(float)
    def progress(self):
        return self._progress
        
    @progress.setter
    def progress(self, val):
        self._progress = val
        self.update()

    def set_value(self, val: float):
        # val should be 0.0 to 1.0
        val = max(0.0, min(1.0, val))
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(val)
        self._anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tm = ThemeManager.instance()
        
        bg_color = QColor(tm.color('border'))
        fill_color = QColor(tm.color('accent'))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height()/2, self.height()/2)
        
        if self._progress > 0:
            fill_w = self.width() * self._progress
            painter.setBrush(QBrush(fill_color))
            painter.drawRoundedRect(0, 0, fill_w, self.height(), self.height()/2, self.height()/2)

