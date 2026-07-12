"""
Settings management - load/save user preferences.
Equivalent to settings.cpp in the original C++ code.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

from .config import get_storage_directory, get_download_directory


@dataclass
class Settings:
    """User settings for RAPPS."""

    # Window
    save_window_pos: bool = True
    window_maximized: bool = False
    window_left: int = 100
    window_top: int = 100
    window_width: int = 800
    window_height: int = 550

    # Database
    update_at_start: bool = False
    use_custom_source: bool = False
    custom_source_url: str = ""

    # Download
    download_dir: str = ""
    delete_installer: bool = False

    # Proxy
    proxy_mode: int = 0  # 0=preconfig, 1=direct, 2=proxy
    proxy_server: str = ""
    no_proxy_for: str = ""

    # Logging
    log_enabled: bool = True

    def __post_init__(self):
        if not self.download_dir:
            self.download_dir = get_download_directory()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        settings = cls()
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        return settings


class SettingsManager:
    """Manages loading and saving of settings."""

    def __init__(self):
        self._settings = Settings()
        self._config_path = self._get_config_path()

    @staticmethod
    def _get_config_path() -> str:
        """Get path to settings file."""
        storage = get_storage_directory()
        return os.path.join(storage, "settings.json")

    def load(self) -> Settings:
        """Load settings from file."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._settings = Settings.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            print(f"Warning: Failed to load settings: {e}")
            self._settings = Settings()

        return self._settings

    def save(self, settings: Optional[Settings] = None):
        """Save settings to file."""
        if settings is None:
            settings = self._settings

        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=2)
        except OSError as e:
            print(f"Error: Failed to save settings: {e}")

    @property
    def settings(self) -> Settings:
        return self._settings

    @settings.setter
    def settings(self, value: Settings):
        self._settings = value
