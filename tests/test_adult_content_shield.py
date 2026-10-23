"""
Unit tests for the Adult Content Classifier & Shield Engine.
Validates search query parsing, open-source keyword classification, false-positive exclusion,
and browser tab intervention.
"""
import pytest
from unittest.mock import MagicMock, patch

from protection.adult_content_shield import AdultContentClassifier, AdultContentShield


class TestAdultContentClassifier:
    def test_extract_search_query_google(self):
        title = "quantum computing algorithms - Google Search"
        q = AdultContentClassifier.extract_search_query(title)
        assert q == "quantum computing algorithms"

    def test_extract_search_query_bing(self):
        title = "python tutorial - Bing"
        q = AdultContentClassifier.extract_search_query(title)
        assert q == "python tutorial"

    def test_extract_search_query_duckduckgo(self):
        title = "rust programming at DuckDuckGo"
        q = AdultContentClassifier.extract_search_query(title)
        assert q == "rust programming"

    def test_extract_search_query_brave(self):
        title = "deep learning research - Brave Search"
        q = AdultContentClassifier.extract_search_query(title)
        assert q == "deep learning research"

    def test_explicit_search_query_detection(self):
        is_adult, reason = AdultContentClassifier.is_adult_title(
            "free porn videos - Google Search"
        )
        assert is_adult is True
        assert "porn" in reason.lower()

    def test_explicit_domain_detection(self):
        is_adult, reason = AdultContentClassifier.is_adult_title(
            "Pornhub: Free HD Porn Videos - Google Chrome",
            domain="pornhub.com"
        )
        assert is_adult is True
        assert "pornhub" in reason.lower()

    def test_leetspeak_normalization(self):
        norm = AdultContentClassifier.normalize_text("watch p0rn hd")
        assert "porn" in norm

        is_adult, reason = AdultContentClassifier.is_adult_query("watch p0rn hd")
        assert is_adult is True
        assert "porn" in reason.lower() or "p0rn" in reason.lower()

    def test_safe_word_false_positive_prevention(self):
        safe_titles = [
            "Essex County Council - Google Search",
            "University of Sussex - Bing",
            "Middlesex Community College - Brave Search",
            "Licensed psychotherapist appointments - DuckDuckGo",
            "Classic literature study guide - Google Search",
            "Documentary on wildlife habitats - YouTube",
        ]
        for title in safe_titles:
            is_adult, reason = AdultContentClassifier.is_adult_title(title)
            assert is_adult is False, f"False positive detected for '{title}' (reason: {reason})"

    def test_clean_search_query(self):
        is_adult, reason = AdultContentClassifier.is_adult_title(
            "how to build an iOS app with SwiftUI - Google Search"
        )
        assert is_adult is False
        assert reason == ""


class TestAdultContentShield:
    @pytest.fixture(autouse=True)
    def setup_shield(self):
        shield = AdultContentShield.instance()
        shield._last_intervention_ts = 0.0
        shield._motivation_callbacks = []
        self.shield = shield

    def test_shield_disabled_ignores_explicit_content(self):
        callback = MagicMock()
        self.shield.register_motivation_callback(callback)

        with patch("settings.manager.SettingsManager.get_bool", return_value=False):
            with patch.object(self.shield, "close_active_browser_tab") as mock_close:
                intervened = self.shield.inspect(
                    process_name="chrome.exe",
                    window_title="pornhub.com - Google Chrome",
                    domain="pornhub.com"
                )
                assert intervened is False
                mock_close.assert_not_called()
                callback.assert_not_called()

    def test_shield_triggers_tab_close_and_callback(self):
        callback = MagicMock()
        self.shield.register_motivation_callback(callback)

        with patch("settings.manager.SettingsManager.get_bool", return_value=True):
            with patch.object(self.shield, "close_active_browser_tab") as mock_close:
                intervened = self.shield.inspect(
                    process_name="brave.exe",
                    window_title="watch xxx porn clips - Brave Search"
                )
                assert intervened is True
                mock_close.assert_called_once()
                callback.assert_called_once()
                args, _ = callback.call_args
                assert "porn" in args[0].lower() or "xxx" in args[0].lower()

    def test_shield_ignores_non_browsers(self):
        with patch.object(self.shield, "close_active_browser_tab") as mock_close:
            intervened = self.shield.inspect(
                process_name="notepad.exe",
                window_title="watch porn videos"
            )
            assert intervened is False
            mock_close.assert_not_called()
