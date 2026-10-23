"""
fluent.py — "Aurora" Apple Design System UI kit for Digital Wellbeing v4.0.

Reusable macOS-style controls: AppleButton (primary / tinted / plain / danger),
AppleCard, FluentLabel (SF-metric type scale), iOS ToggleSwitch, SegmentedControl
and IconButton with spring press feedback.

Fluent* class names are kept as aliases for backwards compatibility.
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PySide6.QtWidgets import (
    QFrame, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QGraphicsOpacityEffect, QAbstractButton, QButtonGroup, QSizePolicy,
)

from ui import design_system as ds
from ui.icons import get_pixmap


# ─────────────────────────────────────────────────────────────────────────────
# Card
# ─────────────────────────────────────────────────────────────────────────────
class FluentCard(QFrame):
    """Apple-style card: opaque surface, hairline border, continuous radius."""

    def __init__(self, parent=None, radius: int = None):
        super().__init__(parent)
        self.setObjectName("fluent_card")
        self._radius = radius if radius is not None else ds.RADIUS["lg"]

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_base_theme)
        self._apply_base_theme(ThemeManager.instance().is_dark)

    def _apply_base_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        self.setStyleSheet(f"""
            QFrame#fluent_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: {self._radius}px;
            }}
            QFrame#fluent_card:hover {{
                background-color: {tm.color('card_hover')};
                border: 1px solid {tm.color('border_hover')};
            }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Buttons
# ─────────────────────────────────────────────────────────────────────────────
class FluentButton(QPushButton):
    """
    Apple-style push button.

    variants:
      primary  — solid systemBlue, white label (default CTA)
      tinted   — blue tint fill, blue label (secondary CTA)
      plain    — transparent, blue label
      danger   — solid systemRed, white label
      (anything else / plain gray) — neutral gray fill, primary label
    """

    def __init__(self, text: str, primary: bool = False, parent=None, variant: str = None):
        super().__init__(text, parent)
        if variant:
            self._variant = variant
        elif primary:
            self._variant = "primary"
        else:
            self._variant = "tinted"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(32)
        self.setIconSize(self.iconSize())

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    # Public API: allow code to set an icon by name from the SVG set
    def set_icon_name(self, name: str, size: int = 16, color: str = None) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        if color is None:
            color = "#FFFFFF" if self._variant in ("primary", "danger") else tm.color("accent_tint_text")
        from ui.icons import get_icon
        self.setIcon(get_icon(name, color=color, size=size))

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        r = ds.RADIUS["md"]

        if self._variant == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tm.color('accent')};
                    color: #FFFFFF;
                    border: none;
                    border-radius: {r}px;
                    padding: 7px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {tm.color('accent_hover')}; }}
                QPushButton:pressed {{ background-color: {tm.color('accent_pressed')}; }}
                QPushButton:disabled {{ background-color: {tm.color('track')}; color: {tm.color('text_muted')}; }}
            """)
        elif self._variant == "tinted":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tm.color('accent_tint_bg')};
                    color: {tm.color('accent_tint_text')};
                    border: none;
                    border-radius: {r}px;
                    padding: 7px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {tm.color('accent_hover_bg')}; }}
                QPushButton:pressed {{ background-color: {tm.color('accent_tint_border')}; }}
                QPushButton:disabled {{ color: {tm.color('text_muted')}; }}
            """)
        elif self._variant == "plain":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {tm.color('accent_tint_text')};
                    border: none;
                    border-radius: {r}px;
                    padding: 7px 12px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {tm.color('surface_hover')}; }}
                QPushButton:pressed {{ background-color: {tm.color('surface_pressed')}; }}
            """)
        elif self._variant == "danger":
            red = tm.color("danger")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {red};
                    color: #FFFFFF;
                    border: none;
                    border-radius: {r}px;
                    padding: 7px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {tm.color('danger_text')}; }}
                QPushButton:pressed {{ background-color: {tm.color('danger_border')}; }}
            """)
        else:  # neutral gray (Apple "gray" button)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {tm.color('surface_secondary')};
                    color: {tm.color('text_main')};
                    border: 1px solid {tm.color('border')};
                    border-radius: {r}px;
                    padding: 7px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {tm.color('surface_hover')}; border-color: {tm.color('border_hover')}; }}
                QPushButton:pressed {{ background-color: {tm.color('surface_pressed')}; }}
            """)


# ─────────────────────────────────────────────────────────────────────────────
# Typography
# ─────────────────────────────────────────────────────────────────────────────
class FluentLabel(QLabel):
    """A semantic label for the Aurora type scale (SF Pro-metrics via Inter)."""

    class Style:
        TITLE = "title"          # 26 / 700 — page titles
        HEADING = "heading"      # 19 / 700 — section titles
        SUBHEADING = "subheading"  # 15 / 600 — card headers
        BODY = "body"            # 13 / 400
        MUTED = "muted"          # 12 / 400 secondary color
        DISPLAY = "display"      # 40 / 800 — hero numerals
        MICRO = "micro"          # 10 / 700 uppercase eyebrow

    def __init__(self, text: str, style: str = Style.BODY, parent=None):
        super().__init__(text, parent)
        self._style = style
        self.setObjectName(f"fluent_label_{style}")

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        if self._style == self.Style.TITLE:
            self.setStyleSheet(f"QLabel {{ {ds.type_css('title1', tm.color('text_main'))} }}")
        elif self._style == self.Style.HEADING:
            self.setStyleSheet(f"QLabel {{ {ds.type_css('title2', tm.color('text_main'))} }}")
        elif self._style == self.Style.SUBHEADING:
            self.setStyleSheet(f"QLabel {{ {ds.type_css('title3', tm.color('text_sub'))} }}")
        elif self._style == self.Style.MUTED:
            self.setStyleSheet(f"QLabel {{ {ds.type_css('callout', tm.color('text_muted'), 'font-weight: 400;')} }}")
        elif self._style == self.Style.DISPLAY:
            self.setStyleSheet(
                f"QLabel {{ {ds.type_css('display', tm.color('text_main'), family=ds.FONT_STACK_DISPLAY)} }}")
        elif self._style == self.Style.MICRO:
            self.setStyleSheet(f"QLabel {{ {ds.type_css('micro', tm.color('text_muted'))} text-transform: uppercase; }}")
        else:  # Body
            self.setStyleSheet(f"QLabel {{ {ds.type_css('body', tm.color('text_main'))} }}")


# ─────────────────────────────────────────────────────────────────────────────
# Toggle (iOS style)
# ─────────────────────────────────────────────────────────────────────────────
class ToggleSwitch(QAbstractButton):
    """iOS-style switch: 51×31, 27px thumb, spring pop on toggle."""

    THUMB_ON = 22.0
    THUMB_OFF = 2.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(51, 31)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._thumb_position = self.THUMB_OFF
        self._thumb_scale = 1.0
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.setDuration(ds.DURATION_BASE)

        self._scale_anim = QPropertyAnimation(self, b"thumb_scale", self)
        self._scale_anim.setDuration(110)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._on_toggled)

    @Property(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    @Property(float)
    def thumb_scale(self):
        return self._thumb_scale

    @thumb_scale.setter
    def thumb_scale(self, val):
        self._thumb_scale = val
        self.update()

    def _on_toggled(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(self.THUMB_ON if checked else self.THUMB_OFF)
        self._anim.start()

        # Subtle squish while sliding (Apple switch behaviour)
        self._scale_anim.stop()
        self._scale_anim.setStartValue(0.88)
        self._scale_anim.setEndValue(1.0)
        self._scale_anim.start()

        from ui import feedback
        feedback.play(feedback.Sound.TAP)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        is_dark = tm.is_dark

        if self.isChecked():
            track_color = QColor(tm.color('accent'))
            if not self.isEnabled():
                track_color = QColor(tm.color('track'))
        else:
            track_color = QColor("#48484A") if is_dark else QColor("#E9E9EA")

        # hover brightening on un-checked track
        if self.underMouse() and not self.isChecked() and self.isEnabled():
            track_color = track_color.lighter(112) if is_dark else track_color.darker(104)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), self.height() / 2.0, self.height() / 2.0)

        thumb_color = QColor("#FFFFFF")
        if not self.isEnabled():
            thumb_color = QColor(255, 255, 255, 140)

        # thumb with scale (squish)
        tw = 27.0 * self._thumb_scale
        th = 27.0 * self._thumb_scale
        cy = self.height() / 2.0
        x = self._thumb_position + (27.0 - tw) / 2.0
        painter.setBrush(QBrush(thumb_color))
        # soft shadow line under thumb (macOS switch)
        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
        painter.drawEllipse(QRectF(x, cy - th / 2.0, tw, th))
        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
# Segmented control (Apple style)
# ─────────────────────────────────────────────────────────────────────────────
class SegmentedControl(QWidget):
    """macOS/iOS segmented control with sliding selection pill."""

    selection_changed = Signal(int)

    def __init__(self, items: list, parent=None):
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._current = 0

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        self.setObjectName("seg_control")
        self.setStyleSheet(f"""
            QWidget#seg_control {{
                background-color: {tm.color('surface_secondary')};
                border-radius: {ds.RADIUS['md']}px;
                border: 1px solid {tm.color('border')};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, label in enumerate(items):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _=False, idx=i: self._on_click(idx))
            self._group.addButton(btn, i)
            layout.addWidget(btn)
            self._buttons.append(btn)

        ThemeManager.instance().theme_changed.connect(self._restyle_buttons)
        if self._buttons:
            self._buttons[0].setChecked(True)
        self._restyle_buttons(tm.is_dark)

    def _on_click(self, idx: int) -> None:
        if idx == self._current:
            return
        self._current = idx
        self._restyle_buttons()
        from ui import feedback
        feedback.play(feedback.Sound.TAP)
        self.selection_changed.emit(idx)

    def set_current(self, idx: int) -> None:
        if 0 <= idx < len(self._buttons):
            self._buttons[idx].setChecked(True)
            self._current = idx
            self._restyle_buttons()

    def current(self) -> int:
        return self._current

    def _restyle_buttons(self, *_args) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        r = ds.RADIUS["md"] - 3
        for i, btn in enumerate(self._buttons):
            selected = (i == self._current)
            if selected:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {tm.color('card_solid')};
                        color: {tm.color('text_main')};
                        border: 1px solid {tm.color('border')};
                        border-radius: {r}px;
                        font-size: 12px;
                        font-weight: 600;
                        padding: 0 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {tm.color('text_sub')};
                        border: none;
                        border-radius: {r}px;
                        font-size: 12px;
                        font-weight: 500;
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{ color: {tm.color('text_main')}; }}
                """)


# ─────────────────────────────────────────────────────────────────────────────
# Icon button
# ─────────────────────────────────────────────────────────────────────────────
class IconButton(QAbstractButton):
    """
    Circular icon-only button with animated hover/press states and optional
    spin. Accepts an icon name from the SVG set (preferred) or a glyph string.
    """

    def __init__(self, icon_ref: str, parent=None, size: int = 36, icon_size: int = 18):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._icon_ref = icon_ref
        self._icon_size = icon_size

        self._hover_progress = 0.0
        self._scale = 1.0
        self._rotation = 0.0
        self._is_spinning = False

        self._hover_anim = QPropertyAnimation(self, b"hover_progress", self)
        self._hover_anim.setDuration(ds.DURATION_FAST)
        self._hover_anim.setEasingCurve(ds.EASE_OUT)
        self._hover_anim.setStartValue(0.0)
        self._hover_anim.setEndValue(1.0)

        self._scale_anim = QPropertyAnimation(self, b"scale", self)
        self._scale_anim.setDuration(ds.DURATION_FAST)
        self._scale_anim.setEasingCurve(ds.EASE_OUT)

        self._spin_anim = QPropertyAnimation(self, b"rotation", self)
        self._spin_anim.setDuration(700)
        self._spin_anim.setStartValue(0.0)
        self._spin_anim.setEndValue(360.0)
        self._spin_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._spin_anim.finished.connect(self._on_spin_finished)

    @Property(float)
    def hover_progress(self):
        return self._hover_progress

    @hover_progress.setter
    def hover_progress(self, val):
        self._hover_progress = val
        self.update()

    @Property(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val
        self.update()

    @Property(float)
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, val):
        self._rotation = val
        self.update()

    def set_spinning(self, spinning: bool):
        self._is_spinning = spinning
        if spinning:
            self.setCursor(Qt.CursorShape.BusyCursor)
            if self._spin_anim.state() != QPropertyAnimation.State.Running:
                self._spin_anim.setStartValue(self._rotation)
                self._spin_anim.setEndValue(self._rotation + 360.0)
                self._spin_anim.start()
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_spin_finished(self):
        if self._is_spinning:
            self._spin_anim.setStartValue(0.0)
            self._spin_anim.setEndValue(360.0)
            self._spin_anim.start()
        else:
            self._rotation = 0.0
            self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hover_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        if not self.isDown():
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(1.06)
            self._scale_anim.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover_anim.setDirection(QPropertyAnimation.Direction.Backward)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        if not self.isDown():
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(1.0)
            self._scale_anim.start()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(0.94)
            self._scale_anim.start()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._scale_anim.setDirection(QPropertyAnimation.Direction.Forward)
            self._scale_anim.setStartValue(self._scale)
            self._scale_anim.setEndValue(1.06 if self.underMouse() else 1.0)
            self._scale_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        is_dark = tm.is_dark

        w = self.width()
        h = self.height()
        rect_w = w - 6
        rect_h = h - 6

        center = QRectF(0, 0, w, h).center()
        painter.translate(center)
        painter.scale(self._scale, self._scale)

        base_color = QColor(255, 255, 255) if is_dark else QColor(0, 0, 0)
        normal_alpha = 22 if is_dark else 14
        hover_alpha = 38 if is_dark else 24
        press_alpha = 52 if is_dark else 36

        current_alpha = normal_alpha + (hover_alpha - normal_alpha) * self._hover_progress
        if self.isDown():
            current_alpha = press_alpha
        base_color.setAlpha(int(current_alpha))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(base_color))
        painter.drawEllipse(QRectF(-rect_w / 2, -rect_h / 2, rect_w, rect_h))

        painter.save()
        painter.rotate(self._rotation)

        icon_color = QColor(tm.color('text_main'))
        icon_size = self._icon_size

        # SVG icon if the ref matches the icon set; otherwise fall back to glyph text
        from ui.icons import ICONS
        if self._icon_ref in ICONS:
            pm = get_pixmap(self._icon_ref, color=icon_color.name(), size=icon_size)
            painter.drawPixmap(
                QRectF(-icon_size / 2, -icon_size / 2, icon_size, icon_size).toRect(),
                pm,
            )
        else:
            painter.setPen(icon_color)
            font = self.font()
            font.setPixelSize(int(icon_size * 1.05))
            font.setWeight(QFont.Weight.Light)
            painter.setFont(font)
            painter.drawText(QRectF(-rect_w / 2, -rect_h / 2, rect_w, rect_h),
                             Qt.AlignmentFlag.AlignCenter, self._icon_ref)
        painter.restore()
        painter.end()
