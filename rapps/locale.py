"""
Internationalization (i18n) support for RAPPS.
Uses Qt's QTranslator for .qm files, with JSON fallback.
"""

import os
import json
from typing import Optional, Dict

from PySide6.QtCore import QLocale, QTranslator, QCoreApplication, QObject
from PySide6.QtWidgets import QApplication


# Language display names
LANGUAGE_NAMES = {
    "en": "English",
    "zh_CN": "简体中文",
    "zh_TW": "繁體中文",
    "ja": "日本語",
}

# Default language
DEFAULT_LANGUAGE = "en"


class LocaleManager:
    """Manages application translations."""

    def __init__(self):
        self._current_lang = DEFAULT_LANGUAGE
        self._qt_translator: Optional[QTranslator] = None
        self._app_translator: Optional[QTranslator] = None
        self._json_translations: Dict[str, str] = {}
        self._translations_dir = self._get_translations_dir()

    @staticmethod
    def _get_translations_dir() -> str:
        """Get the path to the translations directory."""
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "translations")

    def detect_system_language(self) -> str:
        """Detect the system language and return the best matching language code."""
        locale = QLocale.system()
        lang_code = locale.name()  # e.g. "zh_CN", "en_US"

        # Try exact match first
        if lang_code in LANGUAGE_NAMES:
            return lang_code

        # Try language-only match
        lang_part = lang_code.split("_")[0]
        for code in LANGUAGE_NAMES:
            if code.split("_")[0] == lang_part:
                return code

        return DEFAULT_LANGUAGE

    def set_language(self, lang: str, app: Optional[QApplication] = None) -> bool:
        """
        Set the application language.
        Returns True if the language was set successfully.
        """
        if lang not in LANGUAGE_NAMES:
            lang = DEFAULT_LANGUAGE

        self._current_lang = lang
        self._json_translations = {}

        # Remove old translators
        if app is None:
            app = QApplication.instance()
        if app is None:
            return False

        if self._qt_translator:
            app.removeTranslator(self._qt_translator)
            self._qt_translator = None
        if self._app_translator:
            app.removeTranslator(self._app_translator)
            self._app_translator = None

        # Try loading .qm files first
        app_trans = QTranslator()
        app_path = os.path.join(self._translations_dir, f"rapps_{lang}")
        if app_trans.load(app_path):
            app.installTranslator(app_trans)
            self._app_translator = app_trans
        else:
            # Fallback: try JSON-based translation
            json_path = os.path.join(self._translations_dir, f"rapps_{lang}.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    self._json_translations = json.load(f)

        return True

    def tr(self, context: str, text: str, disambiguation: str = None) -> str:
        """
        Translate a string.
        First tries Qt's translation system, then falls back to JSON translations.
        """
        # Try Qt translator first
        translated = QCoreApplication.translate(context, text, disambiguation)
        if translated and translated != text:
            return translated

        # Fallback to JSON translations
        if text in self._json_translations:
            return self._json_translations[text]

        return text

    def retranslate_ui(self, widget: QObject) -> None:
        """
        Re-translate a widget and its children.
        Call this after changing language to update all UI strings.
        """
        if hasattr(widget, 'retranslateUi'):
            widget.retranslateUi(widget)

    @property
    def current_language(self) -> str:
        return self._current_lang

    @property
    def available_languages(self) -> dict:
        return dict(LANGUAGE_NAMES)


# Singleton instance
locale_manager = LocaleManager()
