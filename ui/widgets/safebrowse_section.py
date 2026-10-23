"""
safebrowse_section.py — Settings card for the SafeBrowse adult content filter.

Apple-style settings section: a single switch, a live status line, source
picker, and manual sync. All heavy work (list download, hosts write, UAC
elevation) happens off the UI thread.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSizePolicy,
)

from protection.content_blocker import ContentBlocker, SOURCES, DEFAULT_SOURCE
from ui.theme import ThemeManager
from ui import design_system as ds
from ui.widgets.fluent import ToggleSwitch, FluentButton


def _humanize_ts(ts: float) -> str:
    if not ts:
        return "never"
    delta = max(0.0, __import__("time").time() - ts)
    if delta < 90:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)} min ago"
    if delta < 86400:
        h = int(delta // 3600)
        return "1 hour ago" if h == 1 else f"{h} hours ago"
    d = int(delta // 86400)
    return "yesterday" if d == 1 else f"{d} days ago"


class SafeBrowseSection(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cb = ContentBlocker.instance()
        self._busy = False
        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        self._refresh_status()
        self._poll = QTimer(self)
        self._poll.setInterval(4000)
        self._poll.timeout.connect(self._refresh_status)
        self._poll.start()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header
        head_col = QVBoxLayout()
        head_col.setSpacing(3)
        title = QLabel("SafeBrowse")
        title.setObjectName("setting_label")
        desc = QLabel(
            "Filter adult websites system-wide with open-source blocklists. "
            "Works in every browser, fully offline after setup."
        )
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        head_col.addWidget(title)
        head_col.addWidget(desc)
        layout.addLayout(head_col)

        # Main toggle row
        from PySide6.QtWidgets import QFrame
        row = QFrame()
        row.setObjectName("settings_card")
        row_l = QHBoxLayout(row)
        row_l.setContentsMargins(18, 14, 18, 14)
        row_l.setSpacing(12)

        col = QVBoxLayout()
        col.setSpacing(3)
        lbl = QLabel("Block adult content")
        lbl.setObjectName("setting_label")
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("setting_desc")
        self._status_lbl.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(self._status_lbl)
        row_l.addLayout(col, 1)

        self._toggle = ToggleSwitch()
        self._toggle.toggled.connect(self._on_toggle)
        row_l.addWidget(self._toggle)
        layout.addWidget(row)

        # Source picker
        src_row = QFrame()
        src_row.setObjectName("settings_card")
        src_l = QHBoxLayout(src_row)
        src_l.setContentsMargins(18, 14, 18, 14)
        src_l.setSpacing(12)

        src_col = QVBoxLayout()
        src_col.setSpacing(3)
        src_lbl = QLabel("Blocklist source")
        src_lbl.setObjectName("setting_label")
        self._src_desc = QLabel("Curated open-source lists, refreshed weekly")
        self._src_desc.setObjectName("setting_desc")
        self._src_desc.setWordWrap(True)
        src_col.addWidget(src_lbl)
        src_col.addWidget(self._src_desc)
        src_l.addLayout(src_col, 1)

        self._source_combo = QComboBox()
        for key, meta in SOURCES.items():
            self._source_combo.addItem(meta["label"], key)
        self._source_combo.setMinimumWidth(220)
        self._source_combo.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._source_combo.currentIndexChanged.connect(self._on_source_changed)
        src_l.addWidget(self._source_combo)
        layout.addWidget(src_row)

        # Custom URL input (visible only for the custom source)
        self._url_row = QWidget()
        url_l = QHBoxLayout(self._url_row)
        url_l.setContentsMargins(4, 0, 4, 0)
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://example.com/hosts — any hosts-format list")
        self._url_edit.setMinimumWidth(260)
        self._url_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        url_l.addWidget(self._url_edit, 1)
        self._url_apply_btn = FluentButton("Use This List")
        self._url_apply_btn.clicked.connect(self._on_custom_url)
        url_l.addWidget(self._url_apply_btn)
        layout.addWidget(self._url_row)

        # Sync row
        sync_row = QHBoxLayout()
        sync_row.setContentsMargins(4, 0, 0, 0)
        sync_row.setSpacing(12)
        self._sync_btn = FluentButton("Update Blocklist Now")
        self._sync_btn.clicked.connect(self._on_sync)
        sync_row.addWidget(self._sync_btn)
        sync_row.addStretch()
        layout.addLayout(sync_row)

        layout.addStretch()

        idx = list(SOURCES.keys()).index(self._cb.source_key) if self._cb.source_key in SOURCES else 0
        self._source_combo.blockSignals(True)
        self._source_combo.setCurrentIndex(idx)
        self._source_combo.blockSignals(False)
        self._url_row.setVisible(self._cb.source_key == "custom")
        self._url_edit.setText(self._cb._sm().get("content_filter_custom_url", ""))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_toggle(self, checked: bool) -> None:
        if self._busy:
            self._refresh_status()
            return
        self._busy = True
        self._status_lbl.setText("Working…")
        self._sync_btn.setEnabled(False)
        QTimer.singleShot(30, lambda: self._do_toggle(checked))

    def _do_toggle(self, checked: bool) -> None:
        
        try:
            if checked:
                ok, msg = self._cb.enable()
            else:
                ok, msg = self._cb.disable()
            if ok:
                feedback.success(self._toggle)
            else:
                feedback.warning(self._toggle)
                # Revert the switch to reflect the real state
                self._toggle.blockSignals(True)
                self._toggle.setChecked(self._cb.is_enabled)
                self._toggle.blockSignals(False)
        except Exception as exc:
            ok, msg = False, f"Unexpected error: {exc}"
        finally:
            self._busy = False
            self._sync_btn.setEnabled(True)
        self._set_status(ok, msg)
        self._refresh_status()

    def _on_sync(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._sync_btn.setEnabled(False)
        self._status_lbl.setText("Updating blocklist…")
        self._cb.sync_now(callback=self._on_sync_done)

    def _on_sync_done(self, ok: bool, msg: str) -> None:
        self._busy = False
        self._sync_btn.setEnabled(True)
        self._set_status(ok, msg)
        self._refresh_status()

    def _on_source_changed(self, index: int) -> None:
        key = self._source_combo.currentData() or DEFAULT_SOURCE
        self._url_row.setVisible(key == "custom")
        if key != "custom":
            self._cb._sm().set("content_filter_source", key)
            self._src_desc.setText(SOURCES[key]["note"])

    def _on_custom_url(self) -> None:
        url = self._url_edit.text().strip()
        if not url.lower().startswith(("https://", "http://")):
            self._set_status(False, "Enter a valid https:// list URL first")
            return
        self._cb._sm().set("content_filter_source", "custom")
        self._cb._sm().set("content_filter_custom_url", url)
        self._src_desc.setText("Using your custom list")
        self._on_sync()

    # ------------------------------------------------------------------
    # Status rendering
    # ------------------------------------------------------------------

    def _set_status(self, ok: bool, msg: str) -> None:
        tm = ThemeManager.instance()
        color = tm.color("success") if ok else tm.color("danger")
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {color};")

    def _refresh_status(self) -> None:
        if self._busy:
            return
        st = self._cb.status()
        self._toggle.blockSignals(True)
        self._toggle.setChecked(st["enabled"])
        self._toggle.blockSignals(False)

        if st["enabled"] and st["section_active"]:
            text = f"Active — {st['domain_count']:,} domains blocked · list updated {_humanize_ts(st['last_sync'])}"
        elif st["enabled"]:
            text = "On — awaiting administrator approval to update the hosts file"
        elif st["section_active"]:
            text = "Off — a leftover filter section is still on this PC; toggle on or restart to clean it"
        else:
            text = "Off — the web is unfiltered on this device"
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet("")

    def _apply_theme(self, is_dark: bool) -> None:
        # Widget inherits app stylesheet; nothing custom required today.
        pass
