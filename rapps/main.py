#!/usr/bin/env python3
"""
ReactOS Application Manager - Python/PySide6 Rewrite
Main entry point.
"""

import sys
import os

# Ensure the python/ directory is on sys.path (not the parent rapps/ directory)
_script_dir = os.path.dirname(os.path.abspath(__file__))  # rapps/ package dir
_python_dir = os.path.dirname(_script_dir)               # python/ dir
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
# Also add current working directory
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from rapps.config import APP_TITLE, CMD_INSTALL, CMD_UNINSTALL, CMD_FIND, CMD_INFO, CMD_HELP, CMD_APPWIZ
from rapps.database import AppDatabase
from rapps.settings import SettingsManager
from rapps.ui.main_window import MainWindow


def parse_command_line(args: list) -> dict:
    """Parse command line arguments."""
    result = {
        "command": None,
        "args": [],
        "appwiz_mode": False,
    }

    i = 1  # Skip program name
    while i < len(args):
        arg = args[i].lstrip("-/")

        if arg.lower() == CMD_APPWIZ:
            result["appwiz_mode"] = True
        elif arg.lower() in (CMD_INSTALL, CMD_UNINSTALL, CMD_FIND, CMD_INFO, CMD_HELP):
            result["command"] = arg.lower()
        else:
            result["args"].append(args[i])

        i += 1

    return result


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("ReactOS")

    # Parse command line
    cmd = parse_command_line(sys.argv)

    # Load settings
    settings_mgr = SettingsManager()
    settings = settings_mgr.load()

    # Initialize database
    db = AppDatabase()

    # Create main window
    window = MainWindow(db, settings, settings_mgr, appwiz_mode=cmd["appwiz_mode"])

    # Restore window position
    if settings.save_window_pos:
        window.resize(settings.window_width, settings.window_height)
        window.move(settings.window_left, settings.window_top)
        if settings.window_maximized:
            window.showMaximized()
        else:
            window.show()
    else:
        window.show()

    # Handle command line
    if cmd["command"]:
        window.handle_command(cmd["command"], cmd["args"])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
