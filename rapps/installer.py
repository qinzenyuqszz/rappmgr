"""
Application installer and uninstaller.
Equivalent to geninst.cpp and parts of loaddlg.cpp in the original C++ code.
"""

import os
import shutil
import subprocess
import threading
from typing import Optional, Callable

from .app_info import AvailableAppInfo, InstalledAppInfo, AppCategory
from .database import AppDatabase
from .downloader import download_file, DownloadProgress
from .config import INSTALLER_GENERATE


class InstallResult:
    """Result of an install operation."""

    def __init__(self, success: bool, message: str = "", error: str = ""):
        self.success = success
        self.message = message
        self.error = error


class Installer:
    """Handles downloading and installing applications."""

    def __init__(self, database: AppDatabase):
        self.db = database
        self._downloads_dir = self._get_default_download_dir()

    @staticmethod
    def _get_default_download_dir() -> str:
        """Get default download directory."""
        documents = os.path.expanduser("~/Documents")
        if not os.path.exists(documents):
            documents = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        return os.path.join(documents, "RAPPS Downloads")

    def set_download_dir(self, path: str):
        self._downloads_dir = path

    def install_app(
        self,
        app: AvailableAppInfo,
        on_progress: Optional[Callable] = None,
        on_complete: Optional[Callable[[InstallResult], None]] = None,
    ) -> threading.Thread:
        """
        Download and install an application (runs in background thread).
        """
        thread = threading.Thread(
            target=self._install_app_thread,
            args=(app, on_progress, on_complete),
            daemon=True,
        )
        thread.start()
        return thread

    def _install_app_thread(self, app, on_progress, on_complete):
        """Background thread for installing an app."""
        try:
            url, sha1, size = app.get_download_info()
            if not url:
                result = InstallResult(False, error="No download URL")
                if on_complete:
                    on_complete(result)
                return

            # Determine filename
            filename = app.parser.get_string("SaveAs", "") if app.parser else ""
            if not filename:
                filename = url.split("/")[-1]
            # Sanitize filename
            filename = "".join(c for c in filename if c not in '<>:"/\\|?*')

            dest_path = os.path.join(self._downloads_dir, filename)

            # Check if already downloaded and valid
            if os.path.exists(dest_path) and sha1:
                if self.db.verify_integrity(dest_path, sha1):
                    # File already exists and is valid, skip download
                    pass
                else:
                    dest_path = None  # Will re-download

            if dest_path and not os.path.exists(dest_path):
                dest_path = None

            if dest_path is None:
                dest_path = os.path.join(self._downloads_dir, filename)
                os.makedirs(self._downloads_dir, exist_ok=True)

                def progress_cb(progress: DownloadProgress):
                    if on_progress:
                        on_progress("downloading", progress)

                success = download_file(url, dest_path, on_progress=progress_cb)
                if not success:
                    result = InstallResult(False, error="Download failed")
                    if on_complete:
                        on_complete(result)
                    return

                # Verify integrity
                if sha1 and not self.db.verify_integrity(dest_path, sha1):
                    result = InstallResult(False, error="Integrity check failed")
                    if on_complete:
                        on_complete(result)
                    return

            # Run installer
            if on_progress:
                on_progress("installing", None)

            installer_type = app.get_installer_type()
            if installer_type == INSTALLER_GENERATE:
                success = self._run_generated_installer(app, dest_path)
            else:
                success = self._run_standard_installer(dest_path)

            if success:
                result = InstallResult(True, message=f"{app.display_name} installed successfully")
            else:
                result = InstallResult(False, error="Installer failed")

            if on_complete:
                on_complete(result)

        except Exception as e:
            result = InstallResult(False, error=str(e))
            if on_complete:
                on_complete(result)

    def _run_standard_installer(self, installer_path: str) -> bool:
        """Run a standard installer executable."""
        try:
            process = subprocess.Popen(
                [installer_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.wait()
            return process.returncode == 0
        except Exception as e:
            print(f"Installer error: {e}")
            return False

    def _run_generated_installer(self, app: AvailableAppInfo, archive_path: str) -> bool:
        """
        Run a generated installer (extracts archive and installs files).
        This is a simplified version of the original geninst.cpp.
        """
        import zipfile

        try:
            # Create temp extraction directory
            temp_dir = os.path.join(
                self._downloads_dir,
                f"~temp_{app.identifier}",
            )
            os.makedirs(temp_dir, exist_ok=True)

            # Extract archive
            if archive_path.lower().endswith((".zip", ".cab")):
                if archive_path.lower().endswith(".zip"):
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        zf.extractall(temp_dir)
                # CAB extraction would need additional handling
            else:
                # Assume it's an executable installer
                return self._run_standard_installer(archive_path)

            # Find files to install
            files_spec = app.parser.get_string("Files", "*.exe|*.*") if app.parser else "*.exe|*.*"
            install_dir = self._get_install_dir(app)

            os.makedirs(install_dir, exist_ok=True)

            # Move files from temp to install directory
            for spec in files_spec.split("|"):
                spec = spec.strip()
                import glob as glob_mod
                for src_file in glob_mod.glob(os.path.join(temp_dir, spec)):
                    if os.path.isfile(src_file):
                        dest_file = os.path.join(install_dir, os.path.basename(src_file))
                        shutil.move(src_file, dest_file)

            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Create uninstall registry entry
            self._create_uninstall_entry(app, install_dir)

            return True

        except Exception as e:
            print(f"Generated installer error: {e}")
            return False

    def _get_install_dir(self, app: AvailableAppInfo) -> str:
        """Get installation directory for an app."""
        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        dir_name = app.parser.get_string("Dir", app.display_name) if app.parser else app.display_name
        return os.path.join(program_files, dir_name)

    def _create_uninstall_entry(self, app: AvailableAppInfo, install_dir: str):
        """Create uninstall registry entry."""
        import winreg

        try:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{app.identifier}"
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_WRITE,
            )
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, app.display_name)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, app.display_version or "1.0")

            import datetime
            today = datetime.datetime.now().strftime("%Y%m%d")
            winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, today)

            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to create uninstall entry: {e}")

    def uninstall_app(
        self,
        app: InstalledAppInfo,
        silent: bool = False,
        modify: bool = False,
    ) -> bool:
        """
        Uninstall or modify an installed application.
        """
        cmd = app.modify_string if modify else app.uninstall_string
        if not cmd:
            return False

        try:
            if silent:
                # Add silent flags for MSI
                if "msiexec" in cmd.lower():
                    cmd += " /qn"
                elif app.registry_key_path:
                    quiet_cmd = ""
                    try:
                        import winreg
                        key_path = app.registry_key_path
                        with winreg.OpenKey(
                            winreg.HKEY_CURRENT_USER if "CurrentUser" in key_path else winreg.HKEY_LOCAL_MACHINE,
                            key_path,
                            0,
                            winreg.KEY_READ,
                        ) as key:
                            quiet_cmd = winreg.QueryValueEx(key, "QuietUninstallString")[0]
                    except (FileNotFoundError, OSError):
                        pass
                    if quiet_cmd:
                        cmd = quiet_cmd

            process = subprocess.Popen(cmd, shell=True)
            process.wait()
            return process.returncode == 0

        except Exception as e:
            print(f"Uninstall error: {e}")
            return False
