"""
Main application window.
Equivalent to CMainWindow in gui.cpp.
"""

import os
import sys
import threading
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QMenuBar, QMenu,
    QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence

from ..config import (
    APP_TITLE, APPWIZ_TITLE,
    CATEGORY_INSTALLED, CATEGORY_UPDATES, CATEGORY_SELECTED,
    CATEGORY_ALL_AVAIL, CATEGORY_ALL_INST,
)
from ..app_info import AppType, AppCategory, AvailableAppInfo, InstalledAppInfo
from ..database import AppDatabase
from ..installer import Installer
from ..settings import Settings, SettingsManager
from ..locale import locale_manager

from .category_tree import CategoryTree
from .app_list import ApplicationList
from .info_panel import InfoPanel
from .download_dialog import DownloadDialog
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, db: AppDatabase, settings: Settings,
                 settings_mgr: SettingsManager, appwiz_mode: bool = False, parent=None):
        super().__init__(parent)
        self._db = db
        self._settings = settings
        self._settings_mgr = settings_mgr
        self._appwiz_mode = appwiz_mode
        self._installer = Installer(db)
        self._selected_apps = []  # Apps selected for batch install
        self._current_category = CATEGORY_ALL_AVAIL

        self._setup_ui()
        self._setup_menu()
        self._setup_connections()

        # Title
        self.setWindowTitle(APPWIZ_TITLE if appwiz_mode else APP_TITLE)

        # Load installed apps immediately
        self._load_installed_apps()

        # Update available apps in background
        if not appwiz_mode:
            self._update_available_apps()

    def _setup_ui(self):
        """Build the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter: tree on left, app list + info on right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Category tree
        self._category_tree = CategoryTree(self)
        splitter.addWidget(self._category_tree)

        # Right: App list + info panel
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # App list
        self._app_list = ApplicationList(self)
        right_splitter.addWidget(self._app_list)

        # Info panel
        self._info_panel = InfoPanel(self)
        right_splitter.addWidget(self._info_panel)

        # Set right splitter proportions (60% list, 40% info)
        right_splitter.setStretchFactor(0, 6)
        right_splitter.setStretchFactor(1, 4)

        splitter.addWidget(right_splitter)

        # Set splitter proportions (25% tree, 75% right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 8)

        main_layout.addWidget(splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("")
        self._status_bar.addWidget(self._status_label)

        # Selected count label
        self._selected_label = QLabel("")
        self._status_bar.addPermanentWidget(self._selected_label)

        # Set initial status text
        self._update_status_text()

    def _setup_menu(self):
        """Build the menu bar."""
        self._setup_menu_actions()

    def _setup_menu_actions(self):
        """Build menu bar actions with translated strings."""
        menubar = self.menuBar()
        # Clear existing menus if re-translating
        menubar.clear()

        tr = locale_manager.tr

        # File menu
        file_menu = menubar.addMenu(tr("MainWindow", "&File"))

        settings_action = QAction(tr("MainWindow", "Settings..."), self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction(tr("MainWindow", "E&xit"), self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Actions menu
        actions_menu = menubar.addMenu(tr("MainWindow", "&Actions"))

        refresh_action = QAction(tr("MainWindow", "&Refresh"), self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._refresh)
        actions_menu.addAction(refresh_action)

        reset_db_action = QAction(tr("MainWindow", "&Reset Database"), self)
        reset_db_action.triggered.connect(self._reset_database)
        actions_menu.addAction(reset_db_action)

        actions_menu.addSeparator()

        install_action = QAction(tr("MainWindow", "&Install"), self)
        install_action.setShortcut(QKeySequence("Ctrl+I"))
        install_action.triggered.connect(self._install_selected)
        actions_menu.addAction(install_action)

        uninstall_action = QAction(tr("MainWindow", "&Uninstall"), self)
        uninstall_action.setShortcut(QKeySequence("Ctrl+U"))
        uninstall_action.triggered.connect(self._uninstall_selected)
        actions_menu.addAction(uninstall_action)

        modify_action = QAction(tr("MainWindow", "&Modify"), self)
        modify_action.triggered.connect(self._modify_selected)
        actions_menu.addAction(modify_action)

        actions_menu.addSeparator()

        check_all_action = QAction(tr("MainWindow", "Check &All"), self)
        check_all_action.setShortcut(QKeySequence("Ctrl+A"))
        check_all_action.triggered.connect(lambda: self._app_list.check_all(True))
        actions_menu.addAction(check_all_action)

        uncheck_all_action = QAction(tr("MainWindow", "&Uncheck All"), self)
        uncheck_all_action.triggered.connect(lambda: self._app_list.check_all(False))
        actions_menu.addAction(uncheck_all_action)

        # Search
        search_action = QAction(tr("MainWindow", "&Search"), self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self._app_list.focus_search)
        actions_menu.addAction(search_action)

        # Help menu
        help_menu = menubar.addMenu(tr("MainWindow", "&Help"))

        about_action = QAction(tr("MainWindow", "&About"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_connections(self):
        """Connect signals and slots."""
        self._category_tree.category_selected.connect(self._on_category_selected)
        self._app_list.app_selected.connect(self._on_app_selected)
        self._app_list.app_activated.connect(self._on_app_activated)
        self._app_list.app_checked.connect(self._on_app_checked)
        self._info_panel.install_requested.connect(self._on_install_requested)
        self._info_panel.uninstall_requested.connect(self._on_uninstall_requested)
        self._info_panel.modify_requested.connect(self._on_modify_requested)

    def _update_available_apps(self):
        """Update available apps database in background."""
        def update_thread():
            def on_progress(msg):
                QTimer.singleShot(0, lambda: self._status_label.setText(msg))

            success = self._db.update_available(on_progress=on_progress)
            QTimer.singleShot(0, lambda: self._on_available_updated(success))

        thread = threading.Thread(target=update_thread, daemon=True)
        thread.start()

    def _on_available_updated(self, success: bool):
        """Called when available apps database is updated."""
        tr = locale_manager.tr
        if success:
            count = self._db.get_available_count()
            self._status_label.setText(tr("MainWindow", f"Database updated: {count} applications available").replace(str(count), "{}", 1).format(count))
            # Refresh current view
            self._refresh_current_view()
        else:
            self._status_label.setText(tr("MainWindow", "Failed to update database (using cached data)"))

    def _load_installed_apps(self):
        """Load installed applications from registry."""
        self._db.update_installed()
        self._app_list.set_apps(list(self._db.installed_apps.values()))
        self._app_list.set_display_type(AppType.INSTALLED)
        count = self._db.get_installed_count()
        self._status_label.setText(f"{count} {locale_manager.tr('MainWindow', 'applications installed')}")

    def _refresh(self):
        """Refresh the current view."""
        self._refresh_current_view()

    def _refresh_current_view(self):
        """Refresh the currently displayed category."""
        if self._current_category in (CATEGORY_ALL_INST, CATEGORY_INSTALLED, CATEGORY_UPDATES):
            self._load_installed_apps()
        else:
            self._update_available_apps()

    def _reset_database(self):
        """Reset the database - delete cache and re-download."""
        tr = locale_manager.tr
        reply = QMessageBox.question(
            self, tr("MainWindow", "Reset Database"),
            tr("MainWindow", "This will delete the local database cache and re-download it. Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.remove_cached()
            self._update_available_apps()

    def _on_category_selected(self, category):
        """Handle category selection from tree."""
        self._current_category = category

        if category == CATEGORY_ALL_INST:
            self._app_list.set_display_type(AppType.INSTALLED)
            self._app_list.set_apps(list(self._db.installed_apps.values()))
        elif category == CATEGORY_INSTALLED:
            self._app_list.set_display_type(AppType.INSTALLED)
            self._app_list.set_apps([
                app for app in self._db.installed_apps.values()
                if app.category == AppCategory.INSTALLED_APPLICATIONS
            ])
        elif category == CATEGORY_UPDATES:
            self._app_list.set_display_type(AppType.INSTALLED)
            self._app_list.set_apps([
                app for app in self._db.installed_apps.values()
                if app.category == AppCategory.UPDATES
            ])
        elif category == CATEGORY_ALL_AVAIL:
            self._app_list.set_display_type(AppType.AVAILABLE)
            self._app_list.set_apps(list(self._db.available_apps.values()))
        elif category == CATEGORY_SELECTED:
            self._app_list.set_display_type(AppType.AVAILABLE)
            self._app_list.set_apps(self._selected_apps)
        elif isinstance(category, int) and 1 <= category <= 16:
            self._app_list.set_display_type(AppType.AVAILABLE)
            self._app_list.set_apps(
                self._db.get_apps_by_category(AppCategory(category))
            )

        self._update_status()

    def _on_app_selected(self, app):
        """Handle application selection."""
        self._info_panel.show_app_info(app)

    def _on_app_activated(self, app):
        """Handle application double-click."""
        if app.app_type == AppType.AVAILABLE:
            self._install_app(app)
        else:
            # For installed apps, show info (already shown by selection)
            pass

    def _on_app_checked(self, app, checked: bool):
        """Handle checkbox state change."""
        if checked:
            if app not in self._selected_apps:
                self._selected_apps.append(app)
        else:
            if app in self._selected_apps:
                self._selected_apps.remove(app)
        self._update_status()

    def _on_install_requested(self, app):
        """Handle install link click in info panel."""
        self._install_app(app)

    def _on_uninstall_requested(self, app):
        """Handle uninstall link click in info panel."""
        self._uninstall_app(app)

    def _on_modify_requested(self, app):
        """Handle modify link click in info panel."""
        self._modify_app(app)

    def _install_app(self, app: AvailableAppInfo):
        """Install a single application."""
        self._install_apps([app])

    def _install_apps(self, apps: list):
        """Install multiple applications."""
        dialog = DownloadDialog(self)
        dialog.start_downloads(apps, self._installer)
        dialog.download_complete.connect(lambda _: self._refresh_current_view())
        dialog.exec()

    def _install_selected(self):
        """Install selected (checked) applications."""
        checked = self._app_list.get_checked_apps()
        if checked:
            self._install_apps(checked)
        else:
            app = self._app_list.get_selected_app()
            if app and app.app_type == AppType.AVAILABLE:
                self._install_app(app)

    def _uninstall_app(self, app: InstalledAppInfo):
        """Uninstall an application."""
        tr = locale_manager.tr
        reply = QMessageBox.question(
            self, tr("MainWindow", "Uninstall"),
            tr("MainWindow", "Are you sure you want to uninstall %s?") % app.display_name,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self._installer.uninstall_app(app)
            if success:
                QMessageBox.information(
                    self, tr("MainWindow", "Success"),
                    f"{app.display_name} {tr('MainWindow', 'has been uninstalled.')}")
                self._refresh_current_view()
            else:
                QMessageBox.warning(
                    self, tr("MainWindow", "Error"),
                    f"{tr('MainWindow', 'Failed to uninstall')} {app.display_name}.")

    def _uninstall_selected(self):
        """Uninstall the selected installed application."""
        app = self._app_list.get_selected_app()
        if app and app.app_type == AppType.INSTALLED:
            self._uninstall_app(app)

    def _modify_app(self, app: InstalledAppInfo):
        """Modify an installed application."""
        success = self._installer.uninstall_app(app, modify=True)
        if success:
            self._refresh_current_view()

    def _modify_selected(self):
        """Modify the selected installed application."""
        app = self._app_list.get_selected_app()
        if app and app.app_type == AppType.INSTALLED:
            self._modify_app(app)

    def _show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec():
            self._settings_mgr.save(dialog.settings)
            self._installer.set_download_dir(self._settings.download_dir)

    def _show_about(self):
        """Show the about dialog."""
        tr = locale_manager.tr
        QMessageBox.about(
            self, tr("MainWindow", "About"),
            f"<h2>{APP_TITLE}</h2>"
            f"<p>{tr('MainWindow', 'Version 1.0.0 (Python/PySide6)')}</p>"
            f"<p>{tr('MainWindow', 'A rewrite of the ReactOS Application Manager.')}</p>"
            f"<p>{tr('MainWindow', 'Original C++ code copyright ReactOS contributors.')}</p>"
            f"<p>{tr('MainWindow', 'Python rewrite licensed under GPL-2.0-or-later.')}</p>",
        )

    def _update_status(self):
        """Update the status bar text."""
        total = self._app_list._table.rowCount()
        selected = len(self._selected_apps)
        tr = locale_manager.tr
        if self._app_list.display_type == AppType.AVAILABLE and selected > 0:
            self._selected_label.setText(f"  |  {selected} {tr('MainWindow', 'selected for installation')}")
        else:
            self._selected_label.setText("")

    def _update_status_text(self):
        """Set the initial status text."""
        self._status_label.setText(locale_manager.tr("MainWindow", "Ready"))

    def handle_command(self, command: str, args: list):
        """Handle command-line arguments."""
        if command == "find" and args:
            self._handle_find(args)
        elif command == "info" and args:
            self._handle_info(args)
        elif command == "install" and args:
            self._handle_install(args)
        elif command == "uninstall" and args:
            self._handle_uninstall(args)
        elif command == "help":
            self._print_help()

    def _handle_find(self, search_terms: list):
        """Handle 'find' command - search for apps."""
        self._app_list.set_display_type(AppType.AVAILABLE)
        self._app_list.set_apps(list(self._db.available_apps.values()))
        if search_terms:
            self._app_list.set_search_text(" ".join(search_terms))

    def _handle_info(self, package_names: list):
        """Handle 'info' command - show app info."""
        for name in package_names:
            app = self._db.find_by_package_name(name)
            if app:
                print(f"\n{name}:")
                print(f"  Name: {app.display_name}")
                print(f"  Version: {app.display_version}")
                print(f"  License: {app.get_license_string()}")
                print(f"  Size: {app.get_size_string()}")
                print(f"  Description: {app.comments}")
            else:
                print(f"Package not found: {name}")

    def _handle_install(self, package_names: list):
        """Handle 'install' command."""
        apps = []
        for name in package_names:
            app = self._db.find_by_package_name(name)
            if app:
                apps.append(app)
            else:
                print(f"Package not found: {name}")
        if apps:
            self._install_apps(apps)

    def _handle_uninstall(self, args: list):
        """Handle 'uninstall' command."""
        silent = "/S" in args
        name = None
        for arg in args:
            if arg not in ("/S", "/K"):
                name = arg
                break
        if name:
            app = self._db.find_installed_by_name(name)
            if app:
                success = self._installer.uninstall_app(app, silent=silent)
                if success:
                    print(f"Successfully uninstalled {app.display_name}")
                else:
                    print(f"Failed to uninstall {app.display_name}")
            else:
                print(f"Application not found: {name}")

    def _print_help(self):
        """Print help text."""
        help_text = """
ReactOS Application Manager (Python/PySide6)

Usage:
  main.py [options]

Options:
  /install <package>   Install a package
  /uninstall <name>    Uninstall an application
  /find <search>       Search for applications
  /info <package>      Show package information
  /help                Show this help
  /appwiz              Open in Add/Remove Programs mode
"""
        print(help_text)

    def closeEvent(self, event):
        """Handle window close."""
        # Save settings
        if self._settings.save_window_pos:
            self._settings.window_left = self.x()
            self._settings.window_top = self.y()
            self._settings.window_width = self.width()
            self._settings.window_height = self.height()
            self._settings.window_maximized = self.isMaximized()

        self._settings_mgr.save(self._settings)
        event.accept()
