"""
url_rules_dialog.py — Editor for granular Focus web rules + extension setup.

Rules are persisted immediately through FocusManager; the dialog is a thin,
Apple-style surface over protection.url_rules.UrlRuleEngine.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from ui.icons import get_icon, get_pixmap
from ui.theme import ThemeManager


class _RuleRow(QFrame):
    def __init__(self, rule, on_delete, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("rule_row")
        self.rule = rule

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(10)

        action = QLabel("ALLOW" if rule.action == "allow" else "BLOCK")
        action.setObjectName("rule_action_allow" if rule.action == "allow" else "rule_action_block")
        action.setFixedWidth(58)
        action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(action)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        pattern = QLabel(rule.pattern)
        pattern.setObjectName("rule_pattern")
        text_col.addWidget(pattern)
        if rule.label:
            label = QLabel(rule.label)
            label.setObjectName("rule_label")
            text_col.addWidget(label)
        layout.addLayout(text_col, 1)

        delete_btn = QPushButton()
        delete_btn.setObjectName("rule_delete_btn")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setIcon(get_icon("trash", color=ThemeManager.instance().color("text_muted"), size=14))
        delete_btn.setFixedSize(28, 28)
        delete_btn.setToolTip("Delete rule")
        delete_btn.clicked.connect(lambda: on_delete(rule))
        layout.addWidget(delete_btn)


class UrlRulesDialog(QDialog):
    """Manage sub-path allow/block rules and read extension bridge credentials."""

    def __init__(self, focus_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._fm = focus_manager
        if self._fm is None:
            from protection.focus_manager import FocusManager

            self._fm = FocusManager.instance()
        self.setWindowTitle("Web rules & browser bridge")
        self.setMinimumSize(640, 640)
        self.setModal(True)
        self._setup_ui()
        self._refresh_rules()
        self._refresh_bridge()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(16)

        title = QLabel("Web rules")
        title.setObjectName("dialog_title")
        subtitle = QLabel(
            "Allow productive sub-paths while blocking distracting ones. "
            "The most specific rule wins; unmatched pages use the Focus mode's domain list."
        )
        subtitle.setObjectName("dialog_subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        # Add rule row
        add_card = QFrame()
        add_card.setObjectName("v2_card")
        add_layout = QHBoxLayout(add_card)
        add_layout.setContentsMargins(12, 10, 12, 10)
        add_layout.setSpacing(8)

        self._pattern_input = QLineEdit()
        self._pattern_input.setPlaceholderText("reddit.com/r/all")
        self._pattern_input.setClearButtonEnabled(True)
        self._pattern_input.returnPressed.connect(self._add_rule)
        add_layout.addWidget(self._pattern_input, 1)

        self._action_combo = QComboBox()
        self._action_combo.addItem("Block", "block")
        self._action_combo.addItem("Allow", "allow")
        self._action_combo.setFixedWidth(100)
        add_layout.addWidget(self._action_combo)

        add_btn = QPushButton("Add rule")
        add_btn.setObjectName("primary_pill_btn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setIcon(get_icon("plus", "#FFFFFF", 13))
        add_btn.clicked.connect(self._add_rule)
        add_layout.addWidget(add_btn)
        root.addWidget(add_card)

        # Presets
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_row.addWidget(QLabel("Suggestions:"))
        for label, pattern, action in (
            ("YouTube Shorts", "youtube.com/shorts", "block"),
            ("Reddit r/all", "reddit.com/r/all", "block"),
            ("Reddit programming", "reddit.com/r/programming", "allow"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("preset_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, p=pattern, a=action: self._quick_add(p, a))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        root.addLayout(preset_row)

        # Rule packs / portability
        pack_row = QHBoxLayout()
        pack_row.setSpacing(8)
        pack_row.addWidget(QLabel("Rule pack:"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItem("Study", "study")
        self._preset_combo.addItem("Deep Work", "deep_work")
        self._preset_combo.addItem("Evening", "evening")
        self._preset_combo.setFixedWidth(130)
        pack_row.addWidget(self._preset_combo)
        apply_btn = QPushButton("Apply pack")
        apply_btn.setObjectName("preset_btn")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_pack)
        pack_row.addWidget(apply_btn)
        pack_row.addStretch()
        import_btn = QPushButton("Import…")
        import_btn.setObjectName("preset_btn")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self._import_rules)
        pack_row.addWidget(import_btn)
        export_btn = QPushButton("Export…")
        export_btn.setObjectName("preset_btn")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._export_rules)
        pack_row.addWidget(export_btn)
        root.addLayout(pack_row)

        # Rules list
        self._rules_scroll = QScrollArea()
        self._rules_scroll.setWidgetResizable(True)
        self._rules_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._rules_container = QWidget()
        self._rules_layout = QVBoxLayout(self._rules_container)
        self._rules_layout.setContentsMargins(0, 0, 0, 0)
        self._rules_layout.setSpacing(6)
        self._rules_layout.addStretch()
        self._rules_scroll.setWidget(self._rules_container)
        root.addWidget(self._rules_scroll, 1)

        # Bridge credentials
        bridge_card = QFrame()
        bridge_card.setObjectName("v2_card")
        bridge_layout = QVBoxLayout(bridge_card)
        bridge_layout.setContentsMargins(14, 12, 14, 12)
        bridge_layout.setSpacing(6)

        bridge_hdr = QHBoxLayout()
        bridge_hdr.setSpacing(8)
        bridge_icon = QLabel()
        bridge_icon.setPixmap(get_pixmap("globe", color="#0A84FF", size=16))
        bridge_hdr.addWidget(bridge_icon)
        bridge_title = QLabel("Local browser bridge")
        bridge_title.setObjectName("bridge_title")
        bridge_hdr.addWidget(bridge_title)
        bridge_hdr.addStretch()
        self._bridge_status = QLabel("Starting…")
        self._bridge_status.setObjectName("bridge_status")
        bridge_hdr.addWidget(self._bridge_status)
        bridge_layout.addLayout(bridge_hdr)

        self._bridge_detail = QLabel("")
        self._bridge_detail.setObjectName("bridge_detail")
        self._bridge_detail.setWordWrap(True)
        self._bridge_detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bridge_layout.addWidget(self._bridge_detail)

        bridge_actions = QHBoxLayout()
        bridge_actions.setSpacing(8)
        copy_btn = QPushButton("Copy connection details")
        copy_btn.setObjectName("preset_btn")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_bridge_info)
        bridge_actions.addWidget(copy_btn)
        bridge_actions.addStretch()
        bridge_layout.addLayout(bridge_actions)
        root.addWidget(bridge_card)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Done")
        close_btn.setObjectName("primary_pill_btn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    # ── data operations ─────────────────────────────────────────────────────

    def _refresh_rules(self) -> None:
        while self._rules_layout.count() > 1:
            item = self._rules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rules = self._fm.url_rules()
        if not rules:
            empty = QLabel("No URL rules yet. Add one above, or use a suggestion.")
            empty.setObjectName("rules_empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._rules_layout.insertWidget(0, empty)
            return
        for index, rule in enumerate(rules):
            row = _RuleRow(rule, self._delete_rule)
            self._rules_layout.insertWidget(index, row)

    def _add_rule(self) -> None:
        pattern = self._pattern_input.text().strip()
        action = self._action_combo.currentData() or "block"
        rule = self._fm.add_url_rule(pattern, action)
        if rule is None:
            self._pattern_input.setStyleSheet("border: 1px solid #FF453A;")
            return
        self._pattern_input.clear()
        self._pattern_input.setStyleSheet("")
        self._refresh_rules()

    def _quick_add(self, pattern: str, action: str) -> None:
        if self._fm.add_url_rule(pattern, action):
            self._refresh_rules()

    def _apply_pack(self) -> None:
        preset = self._preset_combo.currentData()
        if preset and self._fm.apply_url_preset(preset):
            self._refresh_rules()

    def _import_rules(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import web rules",
            "",
            "JSON files (*.json)",
        )
        if not path:
            return
        added, error = self._fm.import_url_rules(path)
        if error:
            logger.warning("URL rules import failed: %s", error)
        if added:
            self._refresh_rules()

    def _export_rules(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export web rules",
            "digital-wellbeing-web-rules.json",
            "JSON files (*.json)",
        )
        if path:
            self._fm.export_url_rules(path)

    def _delete_rule(self, rule) -> None:
        try:
            self._fm.remove_url_rule(rule.id)
        except Exception as exc:
            logger.warning("Failed to delete URL rule %s: %s", rule.id, exc)
        self._refresh_rules()

    def _refresh_bridge(self) -> None:
        info = self._fm.extension_bridge_info()
        if info.get("running"):
            self._bridge_status.setText("● Listening on loopback")
            self._bridge_status.setProperty("state", "on")
            self._bridge_detail.setText(
                f"Port: {info.get('port', 0)}    Token: {info.get('token', '')}\n"
                "Install the bundled extension (assets/browser_extension) and paste these "
                "credentials into its Options page. Traffic never leaves this computer."
            )
        else:
            self._bridge_status.setText("○ Bridge offline")
            self._bridge_status.setProperty("state", "off")
            self._bridge_detail.setText(
                info.get("last_error") or "The local bridge is not running."
            )
        self._bridge_status.style().unpolish(self._bridge_status)
        self._bridge_status.style().polish(self._bridge_status)

    def _copy_bridge_info(self) -> None:
        info = self._fm.extension_bridge_info()
        text = f"port={info.get('port', 0)}\ntoken={info.get('token', '')}"
        QApplication.clipboard().setText(text)

    # ── theme ───────────────────────────────────────────────────────────────

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; }}
            QLabel#dialog_title {{ font-size: 24px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#dialog_subtitle {{ font-size: 12px; font-weight: 500; color: {tm.color('text_sub')}; }}
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#rule_pattern {{ color: {tm.color('text_main')}; font-size: 13px; font-weight: 600; }}
            QLabel#rule_label {{ color: {tm.color('text_muted')}; font-size: 11px; }}
            QLabel#rules_empty {{ color: {tm.color('text_muted')}; font-size: 12px; padding: 28px; }}
            QFrame#rule_row {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 10px; }}
            QFrame#v2_card {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 12px; }}
            QLabel#rule_action_allow {{ color: #30D158; font-size: 10px; font-weight: 800; letter-spacing: 0.8px; }}
            QLabel#rule_action_block {{ color: #FF453A; font-size: 10px; font-weight: 800; letter-spacing: 0.8px; }}
            QPushButton#rule_delete_btn {{ background: transparent; border: none; border-radius: 7px; }}
            QPushButton#rule_delete_btn:hover {{ background: {tm.color('surface_hover')}; }}
            QPushButton#primary_pill_btn {{ background: {tm.color('accent')}; color: white; border: none; border-radius: 16px; padding: 8px 18px; font-size: 12px; font-weight: 700; }}
            QPushButton#primary_pill_btn:hover {{ background: {tm.color('accent_hover')}; }}
            QPushButton#preset_btn {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 9px; color: {tm.color('text_sub')}; padding: 5px 11px; font-size: 11px; font-weight: 600; }}
            QPushButton#preset_btn:hover {{ color: {tm.color('text_main')}; border-color: {tm.color('accent')}; }}
            QLineEdit {{ background: {tm.color('input_bg')}; border: 1px solid {tm.color('input_border')}; border-radius: 9px; color: {tm.color('text_main')}; padding: 7px 10px; font-size: 12px; }}
            QComboBox {{ background: {tm.color('input_bg')}; border: 1px solid {tm.color('input_border')}; border-radius: 9px; color: {tm.color('text_main')}; padding: 6px 9px; font-size: 12px; }}
            QLabel#bridge_title {{ color: {tm.color('text_main')}; font-size: 13px; font-weight: 700; }}
            QLabel#bridge_status {{ color: {tm.color('text_muted')}; font-size: 11px; font-weight: 600; }}
            QLabel#bridge_status[state="on"] {{ color: #30D158; }}
            QLabel#bridge_detail {{ color: {tm.color('text_sub')}; font-size: 11px; }}
        """)
