"""
primitives.py — Shared page/card/button primitives.

These are the adoption point for the design tokens. New pages should compose
`PageScaffold`, `Card`, and `Button` instead of hardcoding margins and one-off
button styles. Existing pages can migrate incrementally without changing their
behaviour.

Density:
    comfortable -> PAGE_MARGINS / PAGE_SECTION_SPACING
    compact     -> tighter margins and 18 px section gaps
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui import design_system as ds
from ui.icons import get_icon
from ui.theme import ThemeManager


def density_enabled() -> bool:
    try:
        from settings.manager import SettingsManager

        return SettingsManager().get("ui_density", "comfortable") == "compact"
    except Exception:
        return False


def page_margins(compact: Optional[bool] = None) -> tuple[int, int, int, int]:
    if compact is None:
        compact = density_enabled()
    return (24, 20, 24, 20) if compact else ds.PAGE_MARGINS


def section_spacing(compact: Optional[bool] = None) -> int:
    if compact is None:
        compact = density_enabled()
    return 18 if compact else ds.PAGE_SECTION_SPACING


class Card(QFrame):
    """Standard surface card with token-based padding and a body layout."""

    def __init__(
        self,
        object_name: str = "v2_card",
        padding: Optional[tuple[int, int, int, int]] = None,
        spacing: int = 8,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(*(padding or ds.CARD_MARGINS))
        self.body.setSpacing(spacing)


class Button(QPushButton):
    """Button with a semantic variant mapped to the app's object-name styles."""

    _OBJECT_NAMES = {
        "primary": "primary_pill_btn",
        "secondary": "secondary_pill_btn",
        "ghost": "preset_btn",
        "danger": "active_stop_btn",
    }

    def __init__(
        self,
        text: str,
        variant: str = "secondary",
        icon_name: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(self._OBJECT_NAMES.get(variant, "secondary_pill_btn"))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            self.setIcon(get_icon(icon_name, ThemeManager.instance().color("text_sub"), 13))


class PageScaffold(QWidget):
    """Page shell: content margins, scroll area, title/subtitle, section layout."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        scroll: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._compact = density_enabled()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QHBoxLayout()
        self.header.setSpacing(12)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("page_title")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("page_subtitle")
        title_box.addWidget(self.title_label)
        if subtitle:
            title_box.addWidget(self.subtitle_label)
        self.header.addLayout(title_box, 1)

        self._scroll = None
        self._host: QWidget
        if scroll:
            self._scroll = QScrollArea()
            self._scroll.setWidgetResizable(True)
            self._scroll.setFrameShape(QFrame.Shape.NoFrame)
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._host = QWidget()
            self.content_layout = QVBoxLayout(self._host)
            self._scroll.setWidget(self._host)
            root.addWidget(self._scroll, 1)
        else:
            self._host = QWidget()
            self.content_layout = QVBoxLayout(self._host)
            root.addWidget(self._host, 1)
        self.content_layout.setContentsMargins(*page_margins(self._compact))
        self.content_layout.setSpacing(section_spacing(self._compact))
        self.content_layout.addLayout(self.header)

    def add_section(self, widget: QWidget, stretch: int = 0) -> None:
        self.content_layout.addWidget(widget, stretch)

    def add_stretch(self) -> None:
        self.content_layout.addStretch()

    def set_density(self, compact: bool) -> None:
        self._compact = compact
        self.content_layout.setContentsMargins(*page_margins(compact))
        self.content_layout.setSpacing(section_spacing(compact))
