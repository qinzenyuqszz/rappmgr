"""
Application info panel - shows detailed info about a selected app.
"""

from PySide6.QtWidgets import (
    QTextBrowser, QVBoxLayout, QWidget, QLabel,
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices

from ..app_info import AppType, compare_versions
from ..locale import locale_manager


class InfoPanel(QWidget):
    """Panel showing detailed application information."""

    link_clicked = Signal(str)  # Emits URL when a link is clicked
    install_requested = Signal(object)  # Emits AppInfo
    uninstall_requested = Signal(object)  # Emits InstalledAppInfo
    modify_requested = Signal(object)  # Emits InstalledAppInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_app = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_browser = QTextBrowser()
        self._text_browser.setOpenExternalLinks(False)
        self._text_browser.setReadOnly(True)
        self._text_browser.anchorClicked.connect(self._on_link_clicked)
        layout.addWidget(self._text_browser)

    def show_app_info(self, app):
        """Display detailed information about an application."""
        self._current_app = app

        if app.app_type == AppType.AVAILABLE:
            self._show_available_info(app)
        else:
            self._show_installed_info(app)

    def _show_available_info(self, app):
        """Show info for an available (downloadable) application."""
        tr = locale_manager.tr
        html = []
        html.append(f"<h2>{app.display_name or app.identifier}</h2>")

        # Status
        is_installed, installed_ver, has_update = self._check_install_status(app)
        if has_update:
            html.append(f"<p><i>{tr('InfoPanel', 'Update available')} ({installed_ver})</i></p>")
        elif is_installed:
            html.append(f"<p><i>{tr('InfoPanel', 'Installed')}</i></p>")
        else:
            html.append(f"<p><i>{tr('InfoPanel', 'Not installed')}</i></p>")

        html.append(f"<p><b>{tr('InfoPanel', 'Available version:')}</b> {app.display_version or 'N/A'}</p>")

        # License
        license_str = app.get_license_string()
        if license_str:
            html.append(f"<p><b>{tr('InfoPanel', 'License:')}</b> {license_str}</p>")

        # Size
        size_str = app.get_size_string()
        if size_str:
            html.append(f"<p><b>{tr('InfoPanel', 'Size:')}</b> {size_str}</p>")

        # URL
        url_site = app._get_url_site() if hasattr(app, '_get_url_site') else ""
        if url_site:
            html.append(f'<p><b>{tr("InfoPanel", "Website:")}</b> <a href="{url_site}">{url_site}</a></p>')

        # Description
        if app.comments:
            html.append(f"<p><b>{tr('InfoPanel', 'Description:')}</b> {app.comments}</p>")

        # Download URL
        url_download = app._get_url_download() if hasattr(app, '_get_url_download') else ""
        if url_download:
            html.append(f'<p><b>{tr("InfoPanel", "Download URL:")}</b> <a href="{url_download}">{url_download}</a></p>')

        # Package name
        html.append(f"<p><b>{tr('InfoPanel', 'Package:')}</b> {app.identifier}</p>")

        # Languages
        languages = app.retrieve_languages() if hasattr(app, 'retrieve_languages') else []
        if languages:
            html.append(f"<p><b>{tr('InfoPanel', 'Languages:')}</b> {', '.join(hex(l) for l in languages)}</p>")

        # Action buttons info
        html.append("<hr>")
        if is_installed and not has_update:
            html.append(f"<p><i>{tr('InfoPanel', 'This application is already installed.')}</i></p>")
        else:
            html.append(f'<p><a href="install" style="color:blue;text-decoration:underline;">{tr("InfoPanel", "Click here to Install")}</a></p>')

        self._text_browser.setHtml("\n".join(html))

    def _show_installed_info(self, app):
        """Show info for an installed application."""
        tr = locale_manager.tr
        html = []
        html.append(f"<h2>{app.display_name}</h2>")
        html.append(f"<p><b>{tr('InfoPanel', 'Version:')}</b> {app.display_version or 'N/A'}</p>")

        if app.publisher:
            html.append(f"<p><b>{tr('InfoPanel', 'Publisher:')}</b> {app.publisher}</p>")

        if app.reg_owner:
            html.append(f"<p><b>{tr('InfoPanel', 'Registered owner:')}</b> {app.reg_owner}</p>")

        if app.product_id:
            html.append(f"<p><b>{tr('InfoPanel', 'Product ID:')}</b> {app.product_id}</p>")

        if app.help_link:
            html.append(f'<p><b>{tr("InfoPanel", "Help:")}</b> <a href="{app.help_link}">{app.help_link}</a></p>')

        if app.read_me:
            html.append(f"<p><b>{tr('InfoPanel', 'Readme:')}</b> {app.read_me}</p>")

        if app.contact:
            html.append(f"<p><b>{tr('InfoPanel', 'Contact:')}</b> {app.contact}</p>")

        if app.install_date:
            html.append(f"<p><b>{tr('InfoPanel', 'Install date:')}</b> {app.install_date}</p>")

        if app.install_location:
            html.append(f"<p><b>{tr('InfoPanel', 'Install location:')}</b> {app.install_location}</p>")

        if app.install_source:
            html.append(f"<p><b>{tr('InfoPanel', 'Install source:')}</b> {app.install_source}</p>")

        if app.comments:
            html.append(f"<p><b>{tr('InfoPanel', 'Comments:')}</b> {app.comments}</p>")

        if app.uninstall_string:
            html.append(f"<p><b>{tr('InfoPanel', 'Uninstall string:')}</b> {app.uninstall_string}</p>")

        if app.modify_string:
            html.append(f"<p><b>{tr('InfoPanel', 'Modify string:')}</b> {app.modify_string}</p>")

        # Action buttons
        html.append("<hr>")
        html.append(f'<p><a href="uninstall" style="color:red;text-decoration:underline;">{tr("InfoPanel", "Uninstall")}</a></p>')
        if app.modify_string:
            html.append(f'<p><a href="modify" style="color:blue;text-decoration:underline;">{tr("InfoPanel", "Modify")}</a></p>')

        self._text_browser.setHtml("\n".join(html))

    def _check_install_status(self, app):
        """Check if an available app is already installed."""
        from ..registry import get_installed_version

        # Try by registry name
        if hasattr(app, 'parser') and app.parser:
            reg_name = app.parser.get_string("RegName", "")
            if reg_name:
                version = get_installed_version(reg_name)
                if version:
                    has_update = compare_versions(version, app.display_version) < 0 if app.display_version else False
                    return (True, version, has_update)

        # Try by display name
        version = get_installed_version(app.display_name)
        if version:
            has_update = compare_versions(version, app.display_version) < 0 if app.display_version else False
            return (True, version, has_update)

        return (False, "", False)

    def _on_link_clicked(self, url: QUrl):
        """Handle link clicks in the info panel."""
        href = url.toString()

        if href == "install" and self._current_app:
            self.install_requested.emit(self._current_app)
        elif href == "uninstall" and self._current_app:
            self.uninstall_requested.emit(self._current_app)
        elif href == "modify" and self._current_app:
            self.modify_requested.emit(self._current_app)
        else:
            # Open external URL
            QDesktopServices.openUrl(url)
