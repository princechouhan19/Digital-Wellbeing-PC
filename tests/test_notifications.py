"""
test_notifications.py
Unit and regression tests for the Windows Toast Notification system.
"""
import time
from unittest.mock import MagicMock, patch

import sys

import pytest

from notifications.notifier import Notifier
from protection.notifications import NotificationManager
from settings.manager import SettingsManager


@pytest.fixture
def notifier():
    """Returns a fresh Notifier instance with reset debounce history."""
    n = Notifier()
    with Notifier._lock:
        Notifier._recent_toasts.clear()
    return n


def test_notifier_initialization(notifier):
    assert notifier._enabled is True
    assert notifier._aumid is not None
    assert "DigitalWellbeing" in notifier._aumid


@pytest.mark.skipif(sys.platform != "win32", reason="Toast delivery is Windows-only (WinRT)")
def test_notifier_debounce_prevents_duplicate_storms(notifier):
    title = "Test Warning"
    msg = "5 minutes left"

    with patch.object(notifier, "_send_winrt_toast", return_value=True) as mock_send:
        # First send succeeds
        r1 = notifier.notify(title, msg, debounce=True, cooldown=5.0)
        assert r1 is True
        assert mock_send.call_count == 1

        # Second send immediately after should be suppressed
        r2 = notifier.notify(title, msg, debounce=True, cooldown=5.0)
        assert r2 is False
        assert mock_send.call_count == 1  # Not incremented

        # Different message should be delivered
        r3 = notifier.notify(title, "Different message", debounce=True, cooldown=5.0)
        assert r3 is True
        assert mock_send.call_count == 2


def test_notifier_disabled_in_settings(notifier):
    sm = SettingsManager()
    orig = sm.get_bool("notifications_enabled", True)
    try:
        sm.set("notifications_enabled", False)
        with patch.object(notifier, "_send_winrt_toast", return_value=True) as mock_send:
            res = notifier.notify("Test", "Should not show")
            assert res is False
            mock_send.assert_not_called()
    finally:
        sm.set("notifications_enabled", orig)


def test_notifier_disabled_instance(notifier):
    notifier.set_enabled(False)
    with patch.object(notifier, "_send_winrt_toast", return_value=True) as mock_send:
        res = notifier.notify("Test", "Should not show")
        assert res is False
        mock_send.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="Toast delivery is Windows-only (WinRT)")
def test_notifier_fallback_when_winrt_fails(notifier):
    title = "Fallback Test"
    msg = "Testing fallback execution"

    with patch.object(notifier, "_send_winrt_toast", side_effect=Exception("WinRT unavailable")), \
         patch.object(notifier, "_send_powershell_toast", return_value=True) as mock_ps:
        res = notifier.notify(title, msg, debounce=False)
        assert res is True
        mock_ps.assert_called_once_with(title, msg)


def test_notification_manager_send_warning():
    nm = NotificationManager()
    with patch.object(nm._notifier, "notify", return_value=True) as mock_notify:
        nm.send_warning("Discord.exe", 5)
        mock_notify.assert_called_once_with(
            "App Limit Warning",
            "You have 5 minutes left for Discord.",
            duration=5
        )


def test_notification_manager_send_warning_limit_reached():
    nm = NotificationManager()
    with patch.object(nm._notifier, "notify", return_value=True) as mock_notify:
        nm.send_warning("Discord.exe", 0)
        mock_notify.assert_called_once_with(
            "Limit Reached",
            "Discord has reached its screen time limit.",
            duration=5
        )


def test_notification_manager_send_website_warning():
    nm = NotificationManager()
    with patch.object(nm._notifier, "notify", return_value=True) as mock_notify:
        nm.send_website_warning("youtube.com", 5)
        mock_notify.assert_called_once_with(
            "Website Limit Warning",
            "You have 5 minutes left for youtube.com.",
            duration=5
        )


def test_notification_manager_send_website_warning_limit_reached():
    nm = NotificationManager()
    with patch.object(nm._notifier, "notify", return_value=True) as mock_notify:
        nm.send_website_warning("youtube.com", 0)
        mock_notify.assert_called_once_with(
            "Website Limit Reached",
            "youtube.com has reached its screen time limit.",
            duration=5
        )
