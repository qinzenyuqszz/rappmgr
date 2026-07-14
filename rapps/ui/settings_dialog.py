"""
Settings dialog.
Equivalent to settingsdlg.cpp in the original C++ code.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QCheckBox, QComboBox,
    QPushButton, QFileDialog, QGroupBox,
)
from PySide6.QtCore import Qt

from ..settings import Settings
from ..locale import locale_manager, LANGUAGE_NAMES


class SettingsDialog(QDialog):
    """Dialog for editing application settings."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(450)

        self._settings = settings
        self._temp_settings = Settings.from_dict(settings.to_dict())

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)

        # --- General Settings ---
        general_group = QGroupBox("General")
        general_layout = QFormLayout(general_group)

        # Language selector
        self._language_combo = QComboBox()
        self._language_combo.addItems(
            [f"{name} ({code})" if code != "en" else name for code, name in LANGUAGE_NAMES.items()]
        )
        current_idx = 0
        for i, code in enumerate(LANGUAGE_NAMES.keys()):
            if code == self._temp_settings.language:
                current_idx = i
                break
        self._language_combo.setCurrentIndex(current_idx)
        general_layout.addRow("Language:", self._language_combo)

        self._language_note = QLabel("Restart the application for language changes to take effect.")
        self._language_note.setStyleSheet("color: gray; font-style: italic;")
        general_layout.addRow(self._language_note)

        self._update_at_start = QCheckBox("Update database at startup")
        self._update_at_start.setChecked(self._temp_settings.update_at_start)
        general_layout.addRow(self._update_at_start)

        self._save_window_pos = QCheckBox("Save window position")
        self._save_window_pos.setChecked(self._temp_settings.save_window_pos)
        general_layout.addRow(self._save_window_pos)

        self._log_enabled = QCheckBox("Enable logging")
        self._log_enabled.setChecked(self._temp_settings.log_enabled)
        general_layout.addRow(self._log_enabled)

        layout.addWidget(general_group)

        # --- Database Source ---
        db_group = QGroupBox("Database Source")
        db_layout = QFormLayout(db_group)

        self._use_custom_source = QCheckBox("Use custom database source")
        self._use_custom_source.setChecked(self._temp_settings.use_custom_source)
        db_layout.addRow(self._use_custom_source)

        self._custom_source_url = QLineEdit()
        self._custom_source_url.setText(self._temp_settings.custom_source_url)
        self._custom_source_url.setPlaceholderText("https://example.com/rappmgr.cab")
        db_layout.addRow("Custom URL:", self._custom_source_url)

        layout.addWidget(db_group)

        # --- Download Settings ---
        download_group = QGroupBox("Downloads")
        download_layout = QFormLayout(download_group)

        download_path_layout = QHBoxLayout()
        self._download_dir = QLineEdit()
        self._download_dir.setText(self._temp_settings.download_dir)
        download_path_layout.addWidget(self._download_dir)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_download_dir)
        download_path_layout.addWidget(browse_btn)

        download_layout.addRow("Download directory:", download_path_layout)

        self._delete_installer = QCheckBox("Delete installer after installation")
        self._delete_installer.setChecked(self._temp_settings.delete_installer)
        download_layout.addRow(self._delete_installer)

        layout.addWidget(download_group)

        # --- Proxy Settings ---
        proxy_group = QGroupBox("Proxy")
        proxy_layout = QFormLayout(proxy_group)

        self._proxy_mode = QComboBox()
        self._proxy_mode.addItems(["Use system proxy settings", "Direct connection (no proxy)", "Use proxy server"])
        self._proxy_mode.setCurrentIndex(self._temp_settings.proxy_mode)
        proxy_layout.addRow("Proxy mode:", self._proxy_mode)

        self._proxy_server = QLineEdit()
        self._proxy_server.setText(self._temp_settings.proxy_server)
        self._proxy_server.setPlaceholderText("proxy.example.com:8080")
        proxy_layout.addRow("Proxy server:", self._proxy_server)

        self._no_proxy_for = QLineEdit()
        self._no_proxy_for.setText(self._temp_settings.no_proxy_for)
        self._no_proxy_for.setPlaceholderText("localhost;127.0.0.1")
        proxy_layout.addRow("No proxy for:", self._no_proxy_for)

        layout.addWidget(proxy_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _browse_download_dir(self):
        """Open directory browser for download path."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Download Directory",
            self._download_dir.text(),
        )
        if directory:
            self._download_dir.setText(directory)

    def _accept(self):
        """Apply settings and close."""
        # Save language setting
        selected_lang = list(LANGUAGE_NAMES.keys())[self._language_combo.currentIndex()]
        self._temp_settings.language = selected_lang

        self._temp_settings.update_at_start = self._update_at_start.isChecked()
        self._temp_settings.save_window_pos = self._save_window_pos.isChecked()
        self._temp_settings.log_enabled = self._log_enabled.isChecked()
        self._temp_settings.use_custom_source = self._use_custom_source.isChecked()
        self._temp_settings.custom_source_url = self._custom_source_url.text()
        self._temp_settings.download_dir = self._download_dir.text()
        self._temp_settings.delete_installer = self._delete_installer.isChecked()
        self._temp_settings.proxy_mode = self._proxy_mode.currentIndex()
        self._temp_settings.proxy_server = self._proxy_server.text()
        self._temp_settings.no_proxy_for = self._no_proxy_for.text()

        # Update the original settings
        self._settings.__dict__.update(self._temp_settings.__dict__)

        self.accept()

    @property
    def settings(self) -> Settings:
        return self._settings
