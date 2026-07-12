"""
Category tree widget - left panel showing app categories.
Equivalent to CSideTreeView in gui.cpp.
"""

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from ..config import CATEGORIES, CATEGORY_INSTALLED, CATEGORY_UPDATES, CATEGORY_SELECTED, CATEGORY_ALL_AVAIL, CATEGORY_ALL_INST


class CategoryTree(QTreeWidget):
    """Tree widget showing application categories."""

    category_selected = Signal(object)  # Emits category identifier

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setRootIsDecorated(True)

        self._category_icons = {}
        self._build_tree()

        self.currentItemChanged.connect(self._on_item_changed)

    def _build_tree(self):
        """Build the category tree."""
        self.clear()

        # --- Installed Applications ---
        installed_root = QTreeWidgetItem(self)
        installed_root.setText(0, "Installed Applications")
        installed_root.setData(0, Qt.ItemDataRole.UserRole, CATEGORY_ALL_INST)
        installed_root.setExpanded(True)

        apps_item = QTreeWidgetItem(installed_root)
        apps_item.setText(0, "Applications")
        apps_item.setData(0, Qt.ItemDataRole.UserRole, CATEGORY_INSTALLED)

        updates_item = QTreeWidgetItem(installed_root)
        updates_item.setText(0, "Updates")
        updates_item.setData(0, Qt.ItemDataRole.UserRole, CATEGORY_UPDATES)

        # --- Available for Installation ---
        if not self.parent().property("appwiz_mode"):
            selected_item = QTreeWidgetItem(self)
            selected_item.setText(0, "Selected for Installation")
            selected_item.setData(0, Qt.ItemDataRole.UserRole, CATEGORY_SELECTED)

            avail_root = QTreeWidgetItem(self)
            avail_root.setText(0, "Available for Installation")
            avail_root.setData(0, Qt.ItemDataRole.UserRole, CATEGORY_ALL_AVAIL)
            avail_root.setExpanded(True)

            for cat_id, (name, _) in CATEGORIES.items():
                cat_item = QTreeWidgetItem(avail_root)
                cat_item.setText(0, name)
                cat_item.setData(0, Qt.ItemDataRole.UserRole, cat_id)

    def set_appwiz_mode(self, enabled: bool):
        """Switch to Add/Remove Programs mode (only show installed)."""
        self._build_tree()
        if enabled:
            # Find and select the installed root
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                role = item.data(0, Qt.ItemDataRole.UserRole)
                if role == CATEGORY_ALL_INST:
                    self.setCurrentItem(item)
                    break

    def _on_item_changed(self, current, previous):
        """Handle category selection change."""
        if current:
            category = current.data(0, Qt.ItemDataRole.UserRole)
            self.category_selected.emit(category)

    def select_category(self, category):
        """Programmatically select a category."""
        for i in range(self.topLevelItemCount()):
            item = self._find_category_item(self.topLevelItem(i), category)
            if item:
                self.setCurrentItem(item)
                return

    def _find_category_item(self, item, category):
        """Recursively find an item with the given category data."""
        if item.data(0, Qt.ItemDataRole.UserRole) == category:
            return item
        for i in range(item.childCount()):
            result = self._find_category_item(item.child(i), category)
            if result:
                return result
        return None
