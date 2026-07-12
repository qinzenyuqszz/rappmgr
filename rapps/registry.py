"""
Windows registry operations for enumerating installed applications.
Equivalent to the registry enumeration in appdb.cpp.
"""

import winreg
from typing import Optional

from .app_info import AppCategory, InstalledAppInfo


UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"

# Registry hive combinations to check
REG_HIVES = [
    (winreg.HKEY_CURRENT_USER, 0),
    (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
    (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
]


def _is_system_component(key: winreg.HKEYType) -> bool:
    """Check if a registry key represents a system component."""
    try:
        value, _ = winreg.QueryValueEx(key, "SystemComponent")
        return value == 1
    except (FileNotFoundError, OSError):
        return False


def _is_update(key: winreg.HKEYType) -> bool:
    """Check if this is an update entry."""
    try:
        winreg.QueryValueEx(key, "ParentKeyName")
        return True
    except (FileNotFoundError, OSError):
        return False


def _expand_env_strings(s: str) -> str:
    """Expand environment variables in a string."""
    import os
    try:
        return os.path.expandvars(s)
    except Exception:
        return s


def _read_reg_string(key: winreg.HKEYType, name: str) -> Optional[str]:
    """Read a string value from registry."""
    try:
        value, _ = winreg.QueryValueEx(key, name)
        if isinstance(value, str) and "%" in value:
            value = _expand_env_strings(value)
        return value
    except (FileNotFoundError, OSError):
        return None


def _read_reg_dword(key: winreg.HKEYType, name: str) -> Optional[int]:
    """Read a DWORD value from registry."""
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return value if isinstance(value, int) else None
    except (FileNotFoundError, OSError):
        return None


def _parse_install_date(date_str: str) -> str:
    """Parse install date from registry format."""
    import datetime
    date_str = date_str.strip()
    if len(date_str) == 8:
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            dt = datetime.datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            pass
    return date_str


def _parse_unix_date(unix_ts: int) -> str:
    """Convert Unix timestamp to date string."""
    import datetime
    try:
        dt = datetime.datetime.fromtimestamp(unix_ts)
        return dt.strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return ""


def enumerate_installed_applications(search_only: Optional[str] = None) -> list:
    """
    Enumerate all installed applications from the registry.
    
    Args:
        search_only: If provided, only search for this specific key name.
    
    Returns:
        List of InstalledAppInfo objects.
    """
    apps = []

    for hive, wow_flag in REG_HIVES:
        try:
            with winreg.OpenKey(hive, UNINSTALL_KEY, 0, winreg.KEY_READ | wow_flag) as key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                        index += 1
                    except OSError:
                        break

                    if search_only and subkey_name != search_only:
                        continue

                    try:
                        app = _create_app_from_registry_key(hive, subkey_name, wow_flag)
                        if app:
                            if search_only:
                                return [app]
                            apps.append(app)
                    except Exception:
                        continue
        except (FileNotFoundError, OSError):
            continue

    return apps


def _create_app_from_registry_key(hive, key_name: str, wow_flag: int) -> Optional[InstalledAppInfo]:
    """Create an InstalledAppInfo from a registry key."""
    try:
        with winreg.OpenKey(hive, f"{UNINSTALL_KEY}\\{key_name}", 0, winreg.KEY_READ | wow_flag) as key:
            if _is_system_component(key):
                return None

            display_name = _read_reg_string(key, "DisplayName")
            if not display_name:
                return None

            category = AppCategory.UPDATES if _is_update(key) else AppCategory.INSTALLED_APPLICATIONS

            app = InstalledAppInfo(
                identifier=key_name,
                category=category,
                display_name=display_name,
                display_version=_read_reg_string(key, "DisplayVersion") or "",
                comments=_read_reg_string(key, "Comments") or "",
                display_icon=_read_reg_string(key, "DisplayIcon") or "",
                registry_key_path=f"{UNINSTALL_KEY}\\{key_name}",
                publisher=_read_reg_string(key, "Publisher") or "",
                install_location=_read_reg_string(key, "InstallLocation") or "",
                help_link=_read_reg_string(key, "HelpLink") or "",
                contact=_read_reg_string(key, "Contact") or "",
                reg_owner=_read_reg_string(key, "RegOwner") or "",
                product_id=_read_reg_string(key, "ProductID") or "",
                read_me=_read_reg_string(key, "Readme") or "",
                install_source=_read_reg_string(key, "InstallSource") or "",
            )

            # Uninstall string
            windows_installer = _read_reg_dword(key, "WindowsInstaller")
            if windows_installer:
                app.uninstall_string = f"msiexec /x{key_name}"
            else:
                app.uninstall_string = _read_reg_string(key, "UninstallString") or ""

            # Modify string
            no_modify = _read_reg_dword(key, "NoModify")
            if not no_modify:
                no_modify_str = _read_reg_string(key, "NoModify")
                if no_modify_str and no_modify_str[0] == "1":
                    no_modify = 1

            if not no_modify:
                if windows_installer:
                    app.modify_string = f"msiexec /i{key_name}"
                else:
                    app.modify_string = _read_reg_string(key, "ModifyPath") or ""

            # Install date
            install_date_str = _read_reg_string(key, "InstallDate")
            if install_date_str:
                app.install_date = _parse_install_date(install_date_str)
            else:
                install_date_dword = _read_reg_dword(key, "InstallDate")
                if install_date_dword is not None:
                    app.install_date = _parse_unix_date(install_date_dword)

            return app

    except (FileNotFoundError, OSError, PermissionError):
        return None


def get_installed_version(reg_name: str) -> Optional[str]:
    """
    Get the installed version of an application by its registry name.
    
    Returns version string or None if not installed.
    """
    if not reg_name:
        return None

    for hive, wow_flag in REG_HIVES:
        try:
            path = f"{UNINSTALL_KEY}\\{reg_name}"
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ | wow_flag) as key:
                version = _read_reg_string(key, "DisplayVersion")
                if version:
                    return version
        except (FileNotFoundError, OSError):
            continue

    return None


def remove_installed_app_from_registry(app: InstalledAppInfo) -> bool:
    """Remove an installed app's registry key."""
    if app.category not in (AppCategory.INSTALLED_APPLICATIONS, AppCategory.UPDATES):
        return False

    try:
        # Determine the correct hive
        if "HKEY_CURRENT_USER" in app.registry_key_path or app.registry_key_path.startswith("User"):
            hive = winreg.HKEY_CURRENT_USER
        else:
            hive = winreg.HKEY_LOCAL_MACHINE

        winreg.DeleteKey(hive, app.registry_key_path)
        return True
    except (FileNotFoundError, OSError, PermissionError):
        return False
