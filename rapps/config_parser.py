"""
INI configuration parser with multi-language support.
Equivalent to configparser.cpp in the original C++ code.
"""

import configparser
import locale
from typing import Optional


class MultiLanguageConfigParser:
    """
    INI parser that supports language-specific sections.
    
    Section resolution order (e.g. for Spanish Spain 0c0a):
    1. Section.0c0a.x86 (locale-specific + architecture)
    2. Section.0a.x86     (neutral locale + architecture)
    3. Section.x86        (architecture only)
    4. Section.0c0a       (locale-specific)
    5. Section.0a         (neutral locale)
    6. Section            (default/fallback)
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._keys: dict = {}
        self._cache_ini()

    def _get_locale_sections(self) -> list:
        """Generate section name variants based on current locale."""
        try:
            lcid = locale.getlocale()[0]
            # Get language ID (simplified - use Windows API for real LCID)
            lang = ""
            try:
                import ctypes
                lang = f"{ctypes.windll.kernel32.GetUserDefaultLCID():04x}"
            except Exception:
                pass
        except Exception:
            lang = ""

        arch = "x86"
        try:
            import platform
            arch = platform.machine().lower()
            if arch in ("amd64", "x86_64"):
                arch = "x64"
        except Exception:
            pass

        neutral_lang = lang[-2:] if len(lang) >= 2 else ""

        sections = []
        # Architecture-specific
        if lang:
            sections.append(f"Section.{lang}.{arch}")
        if neutral_lang:
            sections.append(f"Section.{neutral_lang}.{arch}")
        sections.append(f"Section.{arch}")

        # Architecture-neutral
        if lang:
            sections.append(f"Section.{lang}")
        if neutral_lang:
            sections.append(f"Section.{neutral_lang}")
        sections.append("Section")

        return sections

    def _cache_ini(self):
        """Read all relevant sections and cache key-value pairs."""
        config = configparser.ConfigParser(interpolation=None)
        try:
            # Try UTF-16 LE first (common for RAPPS database)
            with open(self.filepath, "r", encoding="utf-16-le") as f:
                config.read_file(f)
        except UnicodeDecodeError:
            try:
                # Fall back to UTF-8
                with open(self.filepath, "r", encoding="utf-8") as f:
                    config.read_file(f)
            except Exception:
                try:
                    with open(self.filepath, "r", encoding="latin-1") as f:
                        config.read_file(f)
                except Exception:
                    return

        seen_keys = set()
        for section_name in self._get_locale_sections():
            if section_name not in config:
                continue
            for key, value in config.items(section_name):
                if key not in seen_keys:
                    self._keys[key] = value
                    seen_keys.add(key)

    def get_string(self, key: str, default: str = "") -> str:
        """Get a string value by key."""
        return self._keys.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer value by key."""
        value = self._keys.get(key, "")
        if not value:
            return default
        try:
            result = int(value)
            return result if result > 0 else default
        except (ValueError, TypeError):
            return default

    def get_all_keys(self) -> dict:
        """Return all cached key-value pairs."""
        return dict(self._keys)
