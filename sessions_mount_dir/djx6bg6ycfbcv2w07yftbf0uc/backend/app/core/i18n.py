import os
import json
from typing import Dict, Optional
from fastapi import Request, Header
from pathlib import Path


class I18n:
    """Internationalization support class for language detection and message translation."""

    def __init__(self, default_lang: str = "en", translations_dir: str = "translations"):
        self.default_lang = default_lang
        self.translations_dir = Path(translations_dir)
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """Load translation files from the translations directory."""
        if not self.translations_dir.exists():
            self.translations_dir.mkdir(parents=True, exist_ok=True)
            # Create default translation files
            self._create_default_translations()

        for lang_file in self.translations_dir.glob("*.json"):
            lang_code = lang_file.stem
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self._translations[lang_code] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Failed to load translations for {lang_code}: {e}")

    def _create_default_translations(self) -> None:
        """Create default translation files for English and Chinese."""
        default_translations = {
            "en": {
                "welcome": "Welcome",
                "login_success": "Login successful",
                "login_failed": "Login failed",
                "invalid_credentials": "Invalid credentials",
                "token_expired": "Token has expired",
                "access_denied": "Access denied",
                "user_not_found": "User not found",
                "invalid_request": "Invalid request",
                "server_error": "Internal server error"
            },
            "zh": {
                "welcome": "欢迎",
                "login_success": "登录成功",
                "login_failed": "登录失败",
                "invalid_credentials": "无效的凭据",
                "token_expired": "令牌已过期",
                "access_denied": "访问被拒绝",
                "user_not_found": "未找到用户",
                "invalid_request": "无效的请求",
                "server_error": "服务器内部错误"
            }
        }

        for lang_code, translations in default_translations.items():
            lang_file = self.translations_dir / f"{lang_code}.json"
            with open(lang_file, "w", encoding="utf-8") as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)

    def detect_language(self, request: Request, accept_language: Optional[str] = Header(None)) -> str:
        """Detect the preferred language from the request."""
        # Check if language is explicitly set in query parameters
        query_lang = request.query_params.get("lang")
        if query_lang and query_lang in self._translations:
            return query_lang

        # Check Accept-Language header
        if accept_language:
            # Parse Accept-Language header (e.g., "en-US,en;q=0.9,zh;q=0.8")
            languages = [lang.split(";")[0].split("-")[0] for lang in accept_language.split(",")]
            for lang in languages:
                if lang in self._translations:
                    return lang

        # Return default language
        return self.default_lang

    def translate(self, key: str, lang: Optional[str] = None) -> str:
        """Translate a message key to the specified language."""
        if lang is None:
            lang = self.default_lang

        if lang not in self._translations:
            lang = self.default_lang

        return self._translations.get(lang, {}).get(key, key)

    def get_translations(self, lang: Optional[str] = None) -> Dict[str, str]:
        """Get all translations for a specific language."""
        if lang is None:
            lang = self.default_lang

        return self._translations.get(lang, {})


# Global i18n instance
i18n = I18n()


def get_translator(request: Request, accept_language: Optional[str] = Header(None)) -> callable:
    """Get a translator function for the current request."""
    lang = i18n.detect_language(request, accept_language)

    def translate(key: str) -> str:
        return i18n.translate(key, lang)

    return translate


def _(key: str, lang: Optional[str] = None) -> str:
    """Shorthand function for translation."""
    return i18n.translate(key, lang)
