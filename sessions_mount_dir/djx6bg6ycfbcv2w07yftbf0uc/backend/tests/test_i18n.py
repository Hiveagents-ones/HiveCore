import pytest
import json
from pathlib import Path
from fastapi import Request
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.core.i18n import I18n
from app.main import app


@pytest.fixture
def i18n_instance(tmp_path):
    """Create a temporary I18n instance for testing."""
    translations_dir = tmp_path / "translations"
    translations_dir.mkdir()
    
    # Create test translation files
    en_translations = {
        "test_key": "Test message",
        "welcome": "Welcome"
    }
    zh_translations = {
        "test_key": "测试消息",
        "welcome": "欢迎"
    }
    
    with open(translations_dir / "en.json", "w", encoding="utf-8") as f:
        json.dump(en_translations, f)
    
    with open(translations_dir / "zh.json", "w", encoding="utf-8") as f:
        json.dump(zh_translations, f)
    
    return I18n(default_lang="en", translations_dir=str(translations_dir))


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestI18n:
    """Test cases for I18n functionality."""

    def test_init_default_translations(self, tmp_path):
        """Test I18n initialization with default translations."""
        translations_dir = tmp_path / "translations"
        i18n = I18n(default_lang="en", translations_dir=str(translations_dir))
        
        assert translations_dir.exists()
        assert (translations_dir / "en.json").exists()
        assert (translations_dir / "zh.json").exists()
        assert i18n.default_lang == "en"

    def test_load_translations(self, i18n_instance):
        """Test loading translations from files."""
        assert "en" in i18n_instance._translations
        assert "zh" in i18n_instance._translations
        assert i18n_instance._translations["en"]["test_key"] == "Test message"
        assert i18n_instance._translations["zh"]["test_key"] == "测试消息"

    def test_detect_language_from_query(self, i18n_instance):
        """Test language detection from query parameters."""
        # Mock request with query parameter
        request = Request({
            "type": "http",
            "query_params": {"lang": "zh"},
            "headers": {}
        })
        
        lang = i18n_instance.detect_language(request)
        assert lang == "zh"

    def test_detect_language_from_header(self, i18n_instance):
        """Test language detection from Accept-Language header."""
        # Mock request with Accept-Language header
        request = Request({
            "type": "http",
            "query_params": {},
            "headers": {"accept-language": "zh-CN,zh;q=0.9,en;q=0.8"}
        })
        
        lang = i18n_instance.detect_language(request, accept_language="zh-CN,zh;q=0.9,en;q=0.8")
        assert lang == "zh"

    def test_detect_language_default(self, i18n_instance):
        """Test default language when no language is specified."""
        # Mock request without language specification
        request = Request({
            "type": "http",
            "query_params": {},
            "headers": {}
        })
        
        lang = i18n_instance.detect_language(request)
        assert lang == "en"

    def test_detect_language_invalid(self, i18n_instance):
        """Test handling of invalid language codes."""
        # Mock request with invalid language in query
        request = Request({
            "type": "http",
            "query_params": {"lang": "invalid"},
            "headers": {}
        })
        
        lang = i18n_instance.detect_language(request)
        assert lang == "en"  # Should fall back to default

    def test_get_translation(self, i18n_instance):
        """Test getting translations."""
        # Test existing key
        assert i18n_instance.get_translation("en", "test_key") == "Test message"
        assert i18n_instance.get_translation("zh", "test_key") == "测试消息"
        
        # Test non-existing key
        assert i18n_instance.get_translation("en", "non_existing") == "non_existing"
        
        # Test non-existing language
        assert i18n_instance.get_translation("fr", "test_key") == "test_key"

    def test_api_with_language_header(self, client):
        """Test API endpoint with Accept-Language header."""
        response = client.get("/", headers={"Accept-Language": "zh-CN"})
        assert response.status_code == 200
        # The actual response would depend on the endpoint implementation

    def test_api_with_language_query(self, client):
        """Test API endpoint with lang query parameter."""
        response = client.get("/?lang=zh")
        assert response.status_code == 200
        # The actual response would depend on the endpoint implementation

    def test_translation_file_error_handling(self, tmp_path):
        """Test handling of corrupted translation files."""
        translations_dir = tmp_path / "translations"
        translations_dir.mkdir()
        
        # Create a corrupted JSON file
        with open(translations_dir / "corrupted.json", "w") as f:
            f.write("{ invalid json }")
        
        # Should not raise exception, just skip the corrupted file
        i18n = I18n(default_lang="en", translations_dir=str(translations_dir))
        assert "corrupted" not in i18n._translations

    def test_missing_translations_directory(self, tmp_path):
        """Test initialization when translations directory doesn't exist."""
        non_existent_dir = tmp_path / "non_existent"
        i18n = I18n(default_lang="en", translations_dir=str(non_existent_dir))
        
        # Should create the directory and default files
        assert non_existent_dir.exists()
        assert (non_existent_dir / "en.json").exists()
        assert (non_existent_dir / "zh.json").exists()

    def test_language_priority(self, i18n_instance):
        """Test language detection priority (query > header > default)."""
        # Mock request with both query and header
        request = Request({
            "type": "http",
            "query_params": {"lang": "zh"},
            "headers": {"accept-language": "en"}
        })
        
        lang = i18n_instance.detect_language(request, accept_language="en")
        assert lang == "zh"  # Query parameter should take priority

    def test_case_insensitive_language_code(self, i18n_instance):
        """Test handling of case-insensitive language codes."""
        # Mock request with uppercase language code
        request = Request({
            "type": "http",
            "query_params": {"lang": "EN"},
            "headers": {}
        })
        
        lang = i18n_instance.detect_language(request)
        assert lang == "en"

    def test_complex_accept_language(self, i18n_instance):
        """Test parsing complex Accept-Language header."""
        request = Request({
            "type": "http",
            "query_params": {},
            "headers": {}
        })
        
        # Test with quality values
        lang = i18n_instance.detect_language(
            request,
            accept_language="fr-CH, fr;q=0.9, en;q=0.8, zh;q=0.7"
        )
        assert lang == "en"  # Should fall back to default as fr is not supported

    def test_translation_with_placeholders(self, i18n_instance):
        """Test translations with placeholder support."""
        # Add a translation with placeholders
        i18n_instance._translations["en"]["greeting"] = "Hello, {name}!"
        
        # Test simple replacement (would need to implement this in I18n class)
        translation = i18n_instance.get_translation("en", "greeting")
        assert translation == "Hello, {name}!"

    def test_reload_translations(self, i18n_instance, tmp_path):
        """Test reloading translations."""
        # Add a new language file
        new_lang_file = Path(i18n_instance.translations_dir) / "fr.json"
        with open(new_lang_file, "w", encoding="utf-8") as f:
            json.dump({"test_key": "Message de test"}, f)
        
        # Reload translations
        i18n_instance._load_translations()
        
        assert "fr" in i18n_instance._translations
        assert i18n_instance._translations["fr"]["test_key"] == "Message de test"
