"""
Application list widget - right panel showing apps in a table.
Equivalent to CApplicationView in appview.cpp.
"""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from ..app_info import AppType, AppCategory, compare_versions


# Column indices
COL_CHECK = 0
COL_NAME = 1
COL_VERSION = 2
COL_SIZE = 3
COL_STATUS = 4


class ApplicationList(QWidget):
    """Table widget showing applications."""

    app_selected = Signal(object)  # Emits selected AppInfo
    app_activated = Signal(object)  # Emits activated (double-clicked) AppInfo
    app_checked = Signal(object, bool)  # Emits (AppInfo, checked)
    search_text_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apps = []
        self._filtered_apps = []
        self._display_type = AppType.AVAILABLE
        self._search_text = ""

        self._setup_ui()

    def _setup_ui(self):
        """Build the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Type to search...")
        self._search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self._search_edit)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["", "Name", "Version", "Size", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(COL_VERSION, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(COL_SIZE, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # Add search bar above table
        main_layout = QVBoxLayout()
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self._table)
        layout.addLayout(main_layout)

        # Search delay timer
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_search)

    def set_display_type(self, app_type: AppType):
        """Set whether to show available or installed apps."""
        self._display_type = app_type

    @property
    def display_type(self) -> AppType:
        return self._display_type

    def set_apps(self, apps: list):
        """Set the list of applications to display."""
        self._apps = apps
        self._apply_search()

    def get_selected_app(self):
        """Get the currently selected application."""
        rows = self._table.selectedItems()
        if rows:
            row = rows[0].row()
            if 0 <= row < len(self._filtered_apps):
                return self._filtered_apps[row]
        return None

    def get_checked_apps(self) -> list:
        """Get all checked applications."""
        checked = []
        for i, app in enumerate(self._filtered_apps):
            checkbox = self._table.cellWidget(i, COL_CHECK)
            if checkbox and checkbox.isChecked():
                checked.append(app)
        return checked

    def check_all(self, checked: bool = True):
        """Check or uncheck all items."""
        for i in range(self._table.rowCount()):
            checkbox = self._table.cellWidget(i, COL_CHECK)
            if checkbox:
                checkbox.blockSignals(True)
                checkbox.setChecked(checked)
                checkbox.blockSignals(False)

    def set_search_text(self, text: str):
        """Set the search text programmatically."""
        self._search_edit.setText(text)

    def focus_search(self):
        """Give focus to the search box."""
        self._search_edit.setFocus()

    def _on_search_changed(self, text: str):
        """Handle search text changes with debounce."""
        self._search_timer.stop()
        self._search_timer.start(300)  # 300ms debounce

    def _apply_search(self):
        """Apply search filter and update table."""
        self._search_text = self._search_edit.text().strip().lower()
        if self._search_text:
            self._filtered_apps = [
                app for app in self._apps
                if self._search_text in app.display_name.lower()
                or self._search_text in (app.comments or "").lower()
            ]
        else:
            self._filtered_apps = list(self._apps)

        self._populate_table()
        self.search_text_changed.emit(self._search_text)

    def _populate_table(self):
        """Populate the table with filtered apps."""
        self._table.blockSignals(True)
        self._table.setRowCount(0)

        self._table.setRowCount(len(self._filtered_apps))

        for row, app in enumerate(self._filtered_apps):
            # Check box (only for available apps)
            if self._display_type == AppType.AVAILABLE:
                checkbox = QCheckBox()
                checkbox.setChecked(False)
                checkbox.stateChanged.connect(lambda state, a=app: self._on_check_changed(a, state))
                self._table.setCellWidget(row, COL_CHECK, checkbox)
            else:
                self._table.setItem(row, COL_CHECK, QTableWidgetItem(""))

            # Name
            name_item = QTableWidgetItem(app.display_name or app.identifier)
            name_item.setData(Qt.ItemDataRole.UserRole, app)
            self._table.setItem(row, COL_NAME, name_item)

            # Version
            version_item = QTableWidgetItem(app.display_version or "")
            self._table.setItem(row, COL_VERSION, version_item)

            # Size
            if hasattr(app, 'get_size_string'):
                size_str = app.get_size_string()
            else:
                size_str = ""
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, COL_SIZE, size_item)

            # Status
            status_item = QTableWidgetItem(self._get_status_text(app))
            self._table.setItem(row, COL_STATUS, status_item)

        self._table.blockSignals(False)

    def _get_status_text(self, app) -> str:
        """Get status text for an application."""
        if self._display_type == AppType.INSTALLED:
            return "Installed"

        # For available apps, check if already installed
        from ..database import AppDatabase
        is_installed, installed_ver, has_update = False, "", False

        # Check against installed apps
        for installed in getattr(self.parent(), '_installed_apps', []):
            if installed.display_name.lower() == app.display_name.lower():
                is_installed = True
                installed_ver = installed.display_version
                if app.display_version:
                    has_update = compare_versions(installed_ver, app.display_version) < 0
                break

        if has_update:
            return f"Update available ({installed_ver})"
        elif is_installed:
            return "Installed"
        else:
            return "Not installed"

    def _on_selection_changed(self):
        """Handle row selection change."""
        app = self.get_selected_app()
        if app:
            self.app_selected.emit(app)

    def _on_cell_double_clicked(self, row, col):
        """Handle double-click on a row."""
        if 0 <= row < len(self._filtered_apps):
            self.app_activated.emit(self._filtered_apps[row])

    def _on_check_changed(self, app, state):
        """Handle checkbox state change."""
        self.app_checked.emit(app, state == Qt.CheckState.Checked.value)

    def refresh_status(self):
        """Refresh the status column for all items."""
        self._populate_table()
