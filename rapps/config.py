"""
Configuration constants for RAPPS.
"""

import os

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

# Categories
CATEGORIES = {
    1:  ("Audio",            "Category Audio"),
    2:  ("Video",            "Category Video"),
    3:  ("Graphics",         "Category Graphics"),
    4:  ("Games",            "Category Games"),
    5:  ("Internet",         "Category Internet"),
    6:  ("Office",           "Category Office"),
    7:  ("Development",      "Category Development"),
    8:  ("Edutainment",      "Category Edutainment"),
    9:  ("Engineering",      "Category Engineering"),
    10: ("Finance",          "Category Finance"),
    11: ("Science",          "Category Science"),
    12: ("Tools",            "Category Tools"),
    13: ("Drivers",          "Category Drivers"),
    14: ("Libraries",        "Category Libraries"),
    15: ("Themes",           "Category Themes"),
    16: ("Other",            "Category Other"),
}

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
