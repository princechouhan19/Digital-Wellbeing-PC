"""
focus_active_view.py — Active Focus cockpit (dial, status pills, exit controls).

Extracted from FocusTimerWidget so the real-time surface is reviewed and
changed independently from the setup surface.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui import design_system as ds
from ui.icons import get_icon, get_pixmap


class FocusActiveViewMixin:
    """Builds the active Focus cockpit on the host widget."""

    def _build_active_view(self) -> None:
        from ui.widgets.focus_timer import AppleFocusRing, StatPill

        layout = QVBoxLayout(self._active_view)
        layout.setContentsMargins(
            ds.SPACING["xl"], ds.SPACING["lg"], ds.SPACING["xl"], ds.SPACING["lg"]
        )
        layout.setSpacing(ds.SPACING["lg"])
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Top Badge: FOCUS ACTIVE (Vector Badge)
        top_badge_row = QHBoxLayout()
        top_badge_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._active_status_pill = QFrame()
        self._active_status_pill.setObjectName("active_focus_pill")
        asp_layout = QHBoxLayout(self._active_status_pill)
        asp_layout.setContentsMargins(14, 5, 14, 5)
        asp_layout.setSpacing(8)
        asp_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._active_pill_icon = QLabel()
        self._active_pill_icon.setFixedSize(14, 14)
        asp_layout.addWidget(self._active_pill_icon)

        self._active_pill_text = QLabel("FOCUS ACTIVE")
        self._active_pill_text.setObjectName("active_pill_text")
        asp_layout.addWidget(self._active_pill_text)

        top_badge_row.addWidget(self._active_status_pill)
        layout.addLayout(top_badge_row)

        # Active Mode Title
        self._active_mode_lbl = QLabel("DEEP FOCUS MODE")
        self._active_mode_lbl.setObjectName("active_mode_title")
        self._active_mode_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._active_mode_lbl)

        # Apple Circular Countdown Dial (Active Cockpit)
        self._active_focus_ring = AppleFocusRing()
        layout.addWidget(self._active_focus_ring, 0, Qt.AlignmentFlag.AlignCenter)

        # Elapsed and Remaining Statistic Pills with Vector SVG Icons
        prog_labels = QHBoxLayout()
        prog_labels.setSpacing(12)
        prog_labels.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._active_elapsed_pill = StatPill("clock", "#0A84FF", "0m elapsed")
        self._active_remaining_pill = StatPill("hourglass", "#FF9F0A", "25m remaining")

        prog_labels.addWidget(self._active_elapsed_pill)
        prog_labels.addWidget(self._active_remaining_pill)
        layout.addLayout(prog_labels)

        # Active Restrictions Inset Panel
        apps_panel = QFrame()
        apps_panel.setObjectName("apple_inset_card")
        apps_panel.setMaximumWidth(560)
        apps_panel_layout = QVBoxLayout(apps_panel)
        apps_panel_layout.setContentsMargins(20, 16, 20, 16)
        apps_panel_layout.setSpacing(10)

        # App Policy line
        app_line = QHBoxLayout()
        app_line.setSpacing(10)
        app_ic = QLabel()
        app_ic.setPixmap(get_pixmap("apps", color="#0A84FF", size=18))
        app_line.addWidget(app_ic)

        self._active_apps_summary = QLabel("All protected processes + 3 permitted applications")
        self._active_apps_summary.setObjectName("active_apps_text")
        app_line.addWidget(self._active_apps_summary, 1)
        apps_panel_layout.addLayout(app_line)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        apps_panel_layout.addWidget(div)

        # Web Policy line
        web_line = QHBoxLayout()
        web_line.setSpacing(10)
        web_ic = QLabel()
        web_ic.setPixmap(get_pixmap("globe", color="#30D158", size=18))
        web_line.addWidget(web_ic)

        self._active_websites_summary = QLabel("3 distracting websites blocked across all browsers")
        self._active_websites_summary.setObjectName("active_apps_text")
        web_line.addWidget(self._active_websites_summary, 1)
        apps_panel_layout.addLayout(web_line)

        layout.addWidget(apps_panel, 0, Qt.AlignmentFlag.AlignCenter)

        # End Session Control Button
        btn_box = QHBoxLayout()
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._active_stop_btn = QPushButton("End Focus Session")
        self._active_stop_btn.setObjectName("active_stop_btn")
        self._active_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active_stop_btn.setMinimumHeight(46)
        self._active_stop_btn.setMinimumWidth(230)
        self._active_stop_btn.setIcon(get_icon("stop", "#FF453A", 16))
        self._active_stop_btn.clicked.connect(self._stop_timer)
        btn_box.addWidget(self._active_stop_btn)
        layout.addLayout(btn_box)

        self._emergency_btn = QPushButton("Need to exit? Emergency unlock")
        self._emergency_btn.setObjectName("text_link_btn")
        self._emergency_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._emergency_btn.setVisible(False)
        self._emergency_btn.clicked.connect(self._open_emergency_exit)
        layout.addWidget(self._emergency_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def _open_emergency_exit(self) -> None:
        from ui.widgets.emergency_exit_dialog import EmergencyExitDialog

        dialog = EmergencyExitDialog(self._fm, parent=self.window())
        dialog.exec()
        self._sync_ui_state()


