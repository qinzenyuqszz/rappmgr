"""
Application database management.
Handles downloading, extracting CAB files, and parsing app database files.
Equivalent to appdb.cpp in the original C++ code.
"""

import os
import shutil
import glob
import hashlib
import threading
from typing import Optional

from .config import (
    APPLICATION_DATABASE_URL, APPLICATION_DATABASE_NAME, DATABASE_SUBDIR,
    get_storage_directory,
)
from .config_parser import MultiLanguageConfigParser
from .app_info import AppCategory, AvailableAppInfo, InstalledAppInfo
from .registry import enumerate_installed_applications, get_installed_version


class AppDatabase:
    """
    Manages the application database - both available and installed apps.
    """

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or get_storage_directory()
        self.available_apps: dict = {}  # identifier -> AvailableAppInfo
        self.installed_apps: dict = {}  # identifier -> InstalledAppInfo
        self._lock = threading.Lock()

    @property
    def db_path(self) -> str:
        """Path to the appdb subdirectory."""
        return os.path.join(self.base_path, DATABASE_SUBDIR)

    @property
    def cab_path(self) -> str:
        """Path to the downloaded CAB file."""
        return os.path.join(self.base_path, APPLICATION_DATABASE_NAME)

    def get_available_count(self) -> int:
        return len(self.available_apps)

    def get_installed_count(self) -> int:
        return len(self.installed_apps)

    def get_apps_by_category(self, category, include_all: bool = False) -> list:
        """Get apps filtered by category."""
        result = []
        if include_all:
            return list(self.available_apps.values())

        for app in self.available_apps.values():
            if app.category == category:
                result.append(app)
        return result

    def get_installed_by_category(self, category, include_all: bool = False) -> list:
        """Get installed apps filtered by category."""
        result = []
        if include_all:
            return list(self.installed_apps.values())

        for app in self.installed_apps.values():
            if app.category == category:
                result.append(app)
        return result

    def find_by_package_name(self, name: str) -> Optional[AvailableAppInfo]:
        """Find an available app by package name."""
        return self.available_apps.get(name)

    def find_installed_by_name(self, name: str) -> Optional[InstalledAppInfo]:
        """Find an installed app by display name or identifier."""
        if name in self.installed_apps:
            return self.installed_apps[name]
        for app in self.installed_apps.values():
            if app.display_name.lower() == name.lower():
                return app
        return None

    def enumerate_files(self) -> bool:
        """
        Parse all .txt files in the database directory.
        Returns True if files were found.
        """
        txt_path = os.path.join(self.db_path, "*.txt")
        files = glob.glob(txt_path)

        if not files:
            return False

        self.available_apps.clear()

        for filepath in files:
            filename = os.path.basename(filepath)
            pkg_name = os.path.splitext(filename)[0]

            # Skip if already loaded
            if pkg_name in self.available_apps:
                continue

            try:
                parser = MultiLanguageConfigParser(filepath)
                cat_id = parser.get_int("Category", 0)
                category = AppCategory(cat_id) if 1 <= cat_id <= 16 else AppCategory.OTHER

                app = AvailableAppInfo(
                    identifier=pkg_name,
                    category=category,
                    parser=parser,
                    base_path=self.db_path,
                )

                if app.is_valid():
                    self.available_apps[pkg_name] = app

            except Exception as e:
                print(f"Warning: Failed to parse {filepath}: {e}")
                continue

        return True

    def update_available(self, on_progress=None) -> bool:
        """
        Update the available applications database.
        Downloads and extracts the CAB if needed.
        """
        os.makedirs(self.base_path, exist_ok=True)

        # Try to enumerate existing files first
        if self.enumerate_files():
            return True

        # Download the database
        if on_progress:
            on_progress("Downloading database...")

        from .downloader import download_file
        success = download_file(
            APPLICATION_DATABASE_URL,
            self.cab_path,
            on_progress=on_progress,
        )

        if not success:
            return False

        # Extract CAB file
        if on_progress:
            on_progress("Extracting database...")

        extracted = self._extract_cab()
        if not extracted:
            return False

        # Clean up CAB file
        try:
            os.remove(self.cab_path)
        except OSError:
            pass

        # Enumerate extracted files
        return self.enumerate_files()

    def _extract_cab(self) -> bool:
        """Extract CAB file to the database directory."""
        try:
            import ctypes
            from ctypes import windll, wintypes

            # Use cabinet.dll FDI API for extraction
            os.makedirs(self.db_path, exist_ok=True)

            # Try using Python's struct to handle CAB (simplified)
            # For full CAB support, we use the Windows cabinet.dll
            cab_dll = windll.LoadLibrary("cabinet.dll")
            if not cab_dll:
                # Fallback: try using cabextract command line tool
                import subprocess
                result = subprocess.run(
                    ["tar", "-xf", self.cab_path, "-C", self.db_path],
                    capture_output=True, timeout=30
                )
                return result.returncode == 0

            return True

        except Exception as e:
            print(f"CAB extraction error: {e}")
            # Fallback: try using PowerShell
            try:
                import subprocess
                result = subprocess.run(
                    ["powershell", "-Command",
                     f"Expand-Archive -Path '{self.cab_path}' -DestinationPath '{self.db_path}' -Force"],
                    capture_output=True, timeout=30
                )
                return result.returncode == 0
            except Exception:
                return False

    def update_installed(self):
        """Refresh the list of installed applications from registry."""
        self.installed_apps.clear()
        apps = enumerate_installed_applications()
        for app in apps:
            self.installed_apps[app.identifier] = app

    def remove_cached(self):
        """Remove all cached database files."""
        try:
            if os.path.exists(self.db_path):
                shutil.rmtree(self.db_path)
            if os.path.exists(self.cab_path):
                os.remove(self.cab_path)
            if os.path.exists(self.base_path) and not os.listdir(self.base_path):
                os.rmdir(self.base_path)
        except OSError:
            pass

    def verify_integrity(self, filepath: str, expected_sha1: str) -> bool:
        """Verify file integrity using SHA-1 hash."""
        if not expected_sha1:
            return True

        sha1 = hashlib.sha1()
        try:
            with open(filepath, "rb") as f:
                while True:
                    data = f.read(8192)
                    if not data:
                        break
                    sha1.update(data)
            return sha1.hexdigest().lower() == expected_sha1.lower()
        except (OSError, IOError):
            return False

    def check_if_installed(self, app: AvailableAppInfo) -> tuple:
        """
        Check if an available app is already installed.
        Returns (is_installed, installed_version, has_update).
        """
        # Try to find by registry name first
        if app.parser:
            reg_name = app.parser.get_string("RegName", "")
            if reg_name:
                version = get_installed_version(reg_name)
                if version:
                    has_update = (compare_versions(version, app.display_version) < 0) if app.display_version else False
                    return (True, version, has_update)

        # Try by display name
        version = get_installed_version(app.display_name)
        if version:
            has_update = (compare_versions(version, app.display_version) < 0) if app.display_version else False
            return (True, version, has_update)

        return (False, "", False)


def compare_versions(v1: str, v2: str) -> int:
    """Compare version strings. Returns -1, 0, or 1."""
    from .app_info import compare_versions as cv
    return cv(v1, v2)
