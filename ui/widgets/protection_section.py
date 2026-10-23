from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QMessageBox
)
from protection.core import ProtectionManager
from ui.widgets.fluent import FluentButton

class ProtectionSection(QWidget):
    def __init__(self, protection: ProtectionManager, parent=None) -> None:
        super().__init__(parent)
        self._protection = protection
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        status_col = QVBoxLayout()
        status_col.setSpacing(2)
        status_title = QLabel("Protection Status")
        status_title.setObjectName("setting_label")
        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("setting_desc")
        status_col.addWidget(status_title)
        status_col.addWidget(self.status_lbl)
        layout.addLayout(status_col)
        
        pin_col = QVBoxLayout()
        pin_col.setSpacing(8)
        pin_title = QLabel("PIN")
        pin_title.setObjectName("setting_label")
        pin_col.addWidget(pin_title)
        
        row = QHBoxLayout()
        row.setSpacing(12)
        
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("••••")
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setFixedWidth(200)
        
        # Style QLineEdit to look like other modern controls
        from ui.theme import ThemeManager
        from ui import design_system as ds
        tm = ThemeManager.instance()
        self.pin_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: {ds.RADIUS['md']}px;
                padding: 6px 12px;
                color: {tm.color('text_main')};
                font-size: 13px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: 1px solid {tm.color('accent')};
            }}
        """)
        
        row.addWidget(self.pin_input)
        
        self.btn_action = FluentButton("Set PIN", primary=False)
        self.btn_action.setFixedWidth(120)
        self.btn_action.clicked.connect(self._on_action)
        row.addWidget(self.btn_action)
        
        self.btn_disable = FluentButton("Disable PIN", primary=False)
        self.btn_disable.setFixedWidth(120)
        self.btn_disable.clicked.connect(self._on_disable)
        row.addWidget(self.btn_disable)
        
        row.addStretch()
        pin_col.addLayout(row)
        layout.addLayout(pin_col)
        
        self._refresh()
        
    def _refresh(self) -> None:
        if self._protection.pin.is_enabled():
            self.status_lbl.setText("Protected by PIN")
            self.pin_input.setVisible(False)
            self.btn_action.setText("Change PIN")
            self.btn_disable.setVisible(True)
        else:
            self.status_lbl.setText("Not Protected")
            self.pin_input.setVisible(True)
            self.btn_action.setText("Set PIN")
            self.btn_disable.setVisible(False)
            
    def _on_action(self) -> None:
        if self._protection.pin.is_enabled():
            from ui.widgets.auth_dialog import AppLockerAuthDialog
            from PySide6.QtWidgets import QDialog, QInputDialog
            dialog = AppLockerAuthDialog(
                process_name="settings",
                display_name="Change App PIN",
                pin_manager=self._protection.pin,
                auth_method="pin",
                parent=self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_pin, ok = QInputDialog.getText(
                    self, "New PIN", "Enter your new PIN (4 to 8 digits):", 
                    QLineEdit.EchoMode.Password
                )
                if ok and new_pin:
                    new_pin = new_pin.strip()
                    if self._protection.pin.set_pin(new_pin):
                        QMessageBox.information(self, "PIN Changed", "Your PIN has been successfully changed.")
                        self._refresh()
                    else:
                        QMessageBox.warning(self, "Error", "PIN must be 4 to 8 digits.")
            return

        pin = self.pin_input.text().strip()
        if not pin:
            QMessageBox.warning(self, "Error", "Please enter a PIN.")
            return
            
        if self._protection.pin.set_pin(pin):
            QMessageBox.information(self, "PIN Set", "PIN has been successfully saved.")
            self.pin_input.clear()
            self._refresh()
        else:
            QMessageBox.warning(self, "Error", "PIN must be 4 to 8 digits.")
            
    def _on_disable(self) -> None:
        if self._protection.pin.is_enabled():
            from ui.widgets.auth_dialog import AppLockerAuthDialog
            from PySide6.QtWidgets import QDialog
            dialog = AppLockerAuthDialog(
                process_name="settings",
                display_name="Disable App PIN",
                pin_manager=self._protection.pin,
                auth_method="pin",
                parent=self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._protection.pin.disable_pin()
                QMessageBox.information(self, "PIN Disabled", "PIN protection has been disabled.")
                self.pin_input.clear()
                self._refresh()
