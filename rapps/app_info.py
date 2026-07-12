"""
Application information classes.
Equivalent to appinfo.cpp in the original C++ code.
"""

import os
import re
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Optional

from .config import (
    CATEGORIES, LICENSE_NAMES, INSTALLER_GENERATE, INSTALLER_UNKNOWN,
    get_storage_directory,
)
from .config_parser import MultiLanguageConfigParser


class AppCategory(IntEnum):
    """Application categories."""
    AUDIO = 1
    VIDEO = 2
    GRAPHICS = 3
    GAMES = 4
    INTERNET = 5
    OFFICE = 6
    DEVELOPMENT = 7
    EDUTAINMENT = 8
    ENGINEERING = 9
    FINANCE = 10
    SCIENCE = 11
    TOOLS = 12
    DRIVERS = 13
    LIBRARIES = 14
    THEMES = 15
    OTHER = 16
    INSTALLED_APPLICATIONS = 100
    UPDATES = 101


class AppType(IntEnum):
    """Type of application (available vs installed)."""
    AVAILABLE = auto()
    INSTALLED = auto()


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    def parse_parts(v):
        return [int(p) if p.isdigit() else 0 for p in v.split(".")]

    parts1 = parse_parts(v1)
    parts2 = parse_parts(v2)

    # Pad shorter list with zeros
    max_len = max(len(parts1), len(parts2))
    parts1.extend([0] * (max_len - len(parts1)))
    parts2.extend([0] * (max_len - len(parts2)))

    for a, b in zip(parts1, parts2):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes == 0:
        return ""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


@dataclass
class AppInfo:
    """Base class for application information."""
    identifier: str  # Package name / registry key name
    category: AppCategory
    display_name: str = ""
    display_version: str = ""
    comments: str = ""
    display_icon: str = ""
    app_type: AppType = AppType.AVAILABLE

    def is_valid(self) -> bool:
        raise NotImplementedError

    def get_download_info(self) -> tuple:
        """Return (url, sha1, size_bytes)."""
        return ("", "", 0)

    def get_display_info(self) -> dict:
        """Return display information dict."""
        return {}

    def get_installer_type(self) -> str:
        return INSTALLER_UNKNOWN


@dataclass
class AvailableAppInfo(AppInfo):
    """Information about an available (downloadable) application."""
    parser: Optional[MultiLanguageConfigParser] = None
    base_path: str = ""
    _languages_loaded: bool = field(default=False, repr=False)
    _language_lcids: list = field(default_factory=list, repr=False)

    def __post_init__(self):
        if not self.display_name and self.parser:
            self.display_name = self.parser.get_string("Name")
        if not self.display_version and self.parser:
            self.display_version = self.parser.get_string("Version")
        if not self.comments and self.parser:
            self.comments = self.parser.get_string("Description")

        # Resolve icon path
        if self.parser and not self.display_icon:
            icon_name = self.parser.get_string("Icon", "")
            if not icon_name:
                icon_name = f"{self.identifier}.ico"
            icon_path = os.path.join(self.base_path, "icons", icon_name)
            if os.path.exists(icon_path):
                self.display_icon = icon_path

        self.app_type = AppType.AVAILABLE

    def is_valid(self) -> bool:
        return bool(self.display_name and self._get_url_download())

    def _get_url_download(self) -> str:
        if self.parser:
            return self.parser.get_string("URLDownload", "")
        return ""

    def _get_url_site(self) -> str:
        if self.parser:
            return self.parser.get_string("URLSite", "")
        return ""

    def get_license_string(self) -> str:
        """Get formatted license string."""
        if not self.parser:
            return ""

        license_type = self.parser.get_int("LicenseType", 0)
        license_str = self.parser.get_string("License", "")

        if license_type not in (0, 1, 2, 3):
            license_type = 0

        if license_type == 0 and license_str.lower() == "freeware":
            license_type = 2
            license_str = ""

        result = LICENSE_NAMES.get(license_type, "")
        if license_str and result:
            result = f"{result} ({license_str})"
        elif license_str:
            result = license_str

        return result

    def get_size_string(self) -> str:
        """Get formatted size string."""
        if not self.parser:
            return ""
        size_bytes = self.parser.get_int("SizeBytes", 0)
        return format_size(size_bytes) if size_bytes else ""

    def get_download_info(self) -> tuple:
        """Return (url, sha1, size_bytes)."""
        if not self.parser:
            return ("", "", 0)
        url = self.parser.get_string("URLDownload", "")
        sha1 = self.parser.get_string("SHA1", "")
        size = self.parser.get_int("SizeBytes", 0)
        return (url, sha1, size)

    def get_display_info(self) -> dict:
        return {
            "license": self.get_license_string(),
            "size": self.get_size_string(),
            "url_site": self._get_url_site(),
            "url_download": self._get_url_download(),
        }

    def get_installer_type(self) -> str:
        if self.parser:
            installer = self.parser.get_string("Installer", "")
            if installer.lower() == "generate":
                return INSTALLER_GENERATE
        return INSTALLER_UNKNOWN

    def get_screenshots(self) -> list:
        """Get list of screenshot URLs."""
        if not self.parser:
            return []
        screenshots = []
        for i in range(1, 17):
            url = self.parser.get_string(f"Screenshot{i}", "")
            if url:
                screenshots.append(url)
            else:
                break
        return screenshots

    def retrieve_languages(self) -> list:
        """Parse and return supported language LCIDs."""
        if self._languages_loaded:
            return self._language_lcids

        self._languages_loaded = True
        if not self.parser:
            return []

        lang_str = self.parser.get_string("Languages", "")
        if not lang_str:
            return []

        for token in lang_str.split("|"):
            token = token.strip()
            if token:
                try:
                    lcid = int(token, 16) if token.startswith("0x") else int(token)
                    self._language_lcids.append(lcid)
                except ValueError:
                    pass

        return self._language_lcids


@dataclass
class InstalledAppInfo(AppInfo):
    """Information about an installed application (from Windows registry)."""
    registry_key_path: str = ""
    uninstall_string: str = ""
    modify_string: str = ""
    install_date: str = ""
    publisher: str = ""
    install_location: str = ""
    help_link: str = ""
    contact: str = ""
    reg_owner: str = ""
    product_id: str = ""
    read_me: str = ""
    install_source: str = ""

    def __post_init__(self):
        self.app_type = AppType.INSTALLED

    def is_valid(self) -> bool:
        return bool(self.display_name)

    def get_installer_type(self) -> str:
        # Check for Generate ARP subkey
        # Simplified: check if uninstall string contains rapps path
        if self.uninstall_string and "/geninst" in self.uninstall_string.lower():
            return INSTALLER_GENERATE
        return INSTALLER_UNKNOWN

    def get_display_info(self) -> dict:
        return {}

    def get_download_info(self) -> tuple:
        return ("", "", 0)
