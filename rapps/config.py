"""
Configuration constants for RAPPS.
"""

import os
from typing import Optional

APP_NAME = "RAPPS"
APP_TITLE = "ReactOS Application Manager"
APPWIZ_TITLE = "Add or Remove Programs"

# Database
APPLICATION_DATABASE_URL = "https://rapps.reactos.org/rapps/rappmgr.cab"
APPLICATION_DATABASE_NAME = "rappmgr.cab"
DATABASE_SUBDIR = "appdb"

# Registry
SETTINGS_REG_KEY = r"Software\ReactOS\RAPPS"
UNINSTALL_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"

# Category definitions (source strings for translation)
CATEGORIES = {
    1:  "Audio",
    2:  "Video",
    3:  "Graphics",
    4:  "Games",
    5:  "Internet",
    6:  "Office",
    7:  "Development",
    8:  "Edutainment",
    9:  "Engineering",
    10: "Finance",
    11: "Science",
    12: "Tools",
    13: "Drivers",
    14: "Libraries",
    15: "Themes",
    16: "Other",
}

# Category display names (can be overridden by locale)
CATEGORY_NAMES = {
    "installed": "Installed",
    "updates": "Updates",
    "selected": "Selected",
    "all_available": "All Available",
    "all_installed": "All Installed",
}


def get_category_display_name(cat_id: int, translator=None) -> str:
    """Get the display name for a category, optionally translated."""
    name = CATEGORIES.get(cat_id, f"Category {cat_id}")
    if translator:
        return translator("CategoryTree", name)
    return name


def get_category_root_names(translator=None) -> dict:
    """Get translated category root names."""
    names = {
        "installed_root": "Installed Applications",
        "installed": "Applications",
        "updates": "Updates",
        "selected": "Selected for Installation",
        "available_root": "Available for Installation",
    }
    if translator:
        return {k: translator("CategoryTree", v) for k, v in names.items()}
    return names

CATEGORY_INSTALLED = "installed"
CATEGORY_UPDATES   = "updates"
CATEGORY_SELECTED  = "selected"
CATEGORY_ALL_AVAIL = "all_available"
CATEGORY_ALL_INST  = "all_installed"

# Installer types
INSTALLER_GENERATE = "generate"
INSTALLER_UNKNOWN  = "unknown"

# License types
LICENSE_NONE      = 0
LICENSE_OPENSOURCE = 1
LICENSE_FREEWARE  = 2
LICENSE_TRIAL     = 3

LICENSE_NAMES = {
    LICENSE_NONE:      "",
    LICENSE_OPENSOURCE: "Open Source",
    LICENSE_FREEWARE:  "Freeware",
    LICENSE_TRIAL:     "Trial",
}

# Storage directory
def get_storage_directory():
    """Get the local storage directory for RAPPS data."""
    appdata = os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
    return os.path.join(appdata, APP_NAME)

def get_download_directory():
    """Get the default download directory."""
    documents = os.path.expanduser("~/Documents")
    if not os.path.exists(documents):
        documents = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    return os.path.join(documents, "RAPPS Downloads")

# Command line keys
CMD_INSTALL  = "install"
CMD_UNINSTALL = "uninstall"
CMD_FIND     = "find"
CMD_INFO     = "info"
CMD_HELP     = "help"
CMD_GENINST  = "geninst"
CMD_SETUP    = "setup"
CMD_APPWIZ   = "appwiz"
