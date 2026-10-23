"""
animated_stacked_widget.py — Aurora page transitions (Apple macOS style).

Incoming page fades in while sliding up a few pixels (macOS sheet-like motion),
with a longer, silkier easing curve than the v3 cross-fade.

Interruption-safe: a navigation request during an in-flight transition finishes
the previous transition instantly, so rapid sidebar clicks are never dropped.
"""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget

from ui import design_system as ds


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget that animates page switches with a soft rise + fade."""

    SLIDE_DISTANCE = 14

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_animating: bool = False
        self._duration: int = ds.DURATION_PAGE
        self._fade_anim: QPropertyAnimation | None = None
        self._move_anim: QPropertyAnimation | None = None
        self._anim_widget: QWidget | None = None

    def _finish_animation(self) -> None:
        """Instantly complete any in-flight transition (cleanup effects)."""
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        if self._move_anim is not None:
            self._move_anim.stop()
            self._move_anim = None
        if self._anim_widget is not None:
            try:
                self._anim_widget.setGraphicsEffect(None)
            except RuntimeError:
                pass  # widget already deleted
            self._anim_widget = None
        self._is_animating = False

    def setCurrentIndexAnimated(self, index: int) -> None:
        if index == self.currentIndex() or index < 0 or index >= self.count():
            return

        # If a transition is mid-flight, finish it instantly first
        if self._is_animating:
            self._finish_animation()

        current_widget = self.currentWidget()
        next_widget = self.widget(index)

        if not current_widget or not next_widget:
            self.setCurrentIndex(index)
            return

        self._is_animating = True
        self._anim_widget = next_widget

        opacity_effect = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0.0)

        self.setCurrentIndex(index)

        geo = next_widget.geometry()

        self._fade_anim = QPropertyAnimation(opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(self._duration)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(ds.EASE_OUT_QUINT)
        self._fade_anim.finished.connect(self._on_finished)
        self._fade_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        self._move_anim = QPropertyAnimation(next_widget, b"pos", self)
        self._move_anim.setDuration(self._duration)
        self._move_anim.setStartValue(geo.translated(0, self.SLIDE_DISTANCE).topLeft())
        self._move_anim.setEndValue(geo.topLeft())
        self._move_anim.setEasingCurve(ds.EASE_OUT_QUINT)
        self._move_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_finished(self) -> None:
        self._finish_animation()
