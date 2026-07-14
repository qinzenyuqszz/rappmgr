"""
Download progress dialog.
Equivalent to CDownloadManager in loaddlg.cpp.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from ..downloader import download_file, DownloadProgress, DownloadWorker
from ..app_info import AvailableAppInfo
from ..installer import Installer, InstallResult
from ..config import INSTALLER_GENERATE
from ..locale import locale_manager


class DownloadDialog(QDialog):
    """Dialog showing download and installation progress."""

    download_complete = Signal(object)  # Emits InstalledAppInfo when done
    download_error = Signal(str)  # Emits error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(locale_manager.tr("DownloadDialog", "Downloading..."))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self._apps = []
        self._current_index = 0
        self._cancelled = False
        self._worker = None

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)

        # Status label
        self._status_label = QLabel(locale_manager.tr("DownloadDialog", "Preparing downloads..."))
        layout.addWidget(self._status_label)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        # File list
        self._file_list = QListWidget()
        layout.addWidget(self._file_list)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._cancel_button = QPushButton(locale_manager.tr("DownloadDialog", "Cancel"))
        self._cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self._cancel_button)

        layout.addLayout(button_layout)

    def start_downloads(self, apps: list, installer: Installer):
        """Start downloading and installing a list of applications."""
        self._apps = apps
        self._current_index = 0
        self._cancelled = False
        self._installer = installer

        # Populate list
        self._file_list.clear()
        for app in apps:
            item = QListWidgetItem(f"{app.display_name} - Waiting...")
            self._file_list.addItem(item)

        self.show()
        self._process_next()

    def _process_next(self):
        """Process the next download in the queue."""
        if self._cancelled or self._current_index >= len(self._apps):
            self._finish()
            return

        app = self._apps[self._current_index]
        self._current_app = app

        # Update list item
        item = self._file_list.item(self._current_index)
        if item:
            item.setText(f"{app.display_name} - Downloading...")

        # Get download info
        url, sha1, size = app.get_download_info()
        if not url:
            if item:
                item.setText(f"{app.display_name} - Error: No URL")
            self._current_index += 1
            self._process_next()
            return

        # Determine filename
        filename = app.parser.get_string("SaveAs", "") if app.parser else ""
        if not filename:
            filename = url.split("/")[-1]
        filename = "".join(c for c in filename if c not in '<>:"/\\|?*')

        dest_path = self._installer._downloads_dir + "/" + filename
        import os
        dest_path = os.path.join(self._installer._downloads_dir, filename)

        # Update status
        self._status_label.setText(f"Downloading: {app.display_name}")

        # Start download
        import threading
        self._download_thread = threading.Thread(
            target=self._download_thread_func,
            args=(url, dest_path, sha1, app),
            daemon=True,
        )
        self._download_thread.start()

    def _download_thread_func(self, url: str, dest_path: str, sha1: str, app):
        """Download thread function."""
        def on_progress(progress: DownloadProgress):
            # Update UI from main thread
            QTimer.singleShot(0, lambda: self._update_download_progress(progress))

        success = download_file(url, dest_path, on_progress=on_progress)

        if success and sha1:
            # Verify integrity
            QTimer.singleShot(0, lambda: self._status_label.setText("Verifying integrity..."))
            from ..database import AppDatabase
            db = AppDatabase()
            if not db.verify_integrity(dest_path, sha1):
                QTimer.singleShot(0, lambda: self._download_failed("Integrity check failed"))
                return

        if success:
            QTimer.singleShot(0, lambda: self._download_succeeded(dest_path, app))
        else:
            QTimer.singleShot(0, lambda: self._download_failed("Download failed"))

    def _update_download_progress(self, progress: DownloadProgress):
        """Update progress bar from download thread."""
        if progress.total_bytes > 0:
            self._progress_bar.setValue(int(progress.percentage))
            self._status_label.setText(
                f"Downloading: {self._current_app.display_name} "
                f"({progress.downloaded_bytes / 1024 / 1024:.1f} MB / "
                f"{progress.total_bytes / 1024 / 1024:.1f} MB)"
            )
        else:
            self._progress_bar.setValue(0)  # Marquee mode

    def _download_succeeded(self, dest_path: str, app):
        """Handle successful download."""
        item = self._file_list.item(self._current_index)
        if item:
            item.setText(f"{app.display_name} - Installing...")

        self._status_label.setText(f"Installing: {app.display_name}")
        self._progress_bar.setValue(0)

        # Run installer
        def on_install_complete(result: InstallResult):
            if result.success:
                if item:
                    item.setText(f"{app.display_name} - Installed")
            else:
                if item:
                    item.setText(f"{app.display_name} - Install failed: {result.error}")
            self._current_index += 1
            QTimer.singleShot(0, self._process_next)

        self._installer.install_app(app, on_complete=on_install_complete)

    def _download_failed(self, error: str):
        """Handle download failure."""
        item = self._file_list.item(self._current_index)
        if item:
            item.setText(f"{self._current_app.display_name} - Failed: {error}")

        self.download_error.emit(error)
        self._current_index += 1
        self._process_next()

    def _on_cancel(self):
        """Handle cancel button click."""
        self._cancelled = True
        self._finish()

    def _finish(self):
        """Finish the dialog."""
        self.download_complete.emit(self._current_index)
        self.accept()
