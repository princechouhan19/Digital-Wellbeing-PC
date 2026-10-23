from __future__ import annotations

from database.repository import Repository


class SettingsManager:
    _BOOL_KEYS = {"autostart", "dark_mode", "minimize_to_tray", "notifications_enabled", "debug_tracking", "auto_update_enabled", "notify_updates", "name_prompt_completed"}
    _INT_KEYS = {"idle_threshold_s", "daily_limit_minutes"}

    def __init__(self) -> None:
        self._repo = Repository()

    def get(self, key: str, default: str = "") -> str:
        return self._repo.get_setting(key) or default

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self._repo.get_setting(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes")

    def get_int(self, key: str, default: int = 0) -> int:
        val = self._repo.get_setting(key)
        try:
            return int(val) if val is not None else default
        except ValueError:
            return default

    def set(self, key: str, value: str) -> None:
        self._repo.set_setting(key, value)

    def set_bool(self, key: str, value: bool) -> None:
        self._repo.set_setting(key, "true" if value else "false")

    def set_int(self, key: str, value: int) -> None:
        self._repo.set_setting(key, str(value))

    def all(self) -> dict[str, str]:
        return self._repo.get_all_settings()

    # Personalization Extensions
    @property
    def display_name(self) -> str:
        return self.get("display_name", "")

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.set("display_name", value.strip() if value else "")

    @property
    def name_prompt_completed(self) -> bool:
        return self.get_bool("name_prompt_completed", False)

    @name_prompt_completed.setter
    def name_prompt_completed(self, value: bool) -> None:
        self.set_bool("name_prompt_completed", value)

    # First-Run Onboarding
    @property
    def onboarding_completed(self) -> bool:
        # Migration: users who completed the v3 name prompt skip onboarding.
        if self.get_bool("onboarding_completed", False):
            return True
        if self.get_bool("name_prompt_completed", False):
            self.set_bool("onboarding_completed", True)
            return True
        return False

    @onboarding_completed.setter
    def onboarding_completed(self, value: bool) -> None:
        self.set_bool("onboarding_completed", value)

    # Theme & Appearance Extensions
    @property
    def theme(self) -> str:
        val = self.get("theme", "").lower()
        if val in ("light", "dark", "system"):
            return val
        return "dark" if self.get_bool("dark_mode", True) else "light"

    @theme.setter
    def theme(self, value: str) -> None:
        val = value.lower()
        if val not in ("light", "dark", "system"):
            val = "dark"
        self.set("theme", val)
        if val in ("light", "dark"):
            self.set_bool("dark_mode", val == "dark")

    # SleepGuard Extensions
    @property
    def sleepguard_enabled(self) -> bool:
        return self.get_bool("sleepguard_enabled", True)

    @sleepguard_enabled.setter
    def sleepguard_enabled(self, value: bool) -> None:
        self.set_bool("sleepguard_enabled", value)

    @property
    def sleepguard_action(self) -> str:
        """The power action to execute when SleepGuard timer expires.
        Valid values: lock, sleep, hibernate, shutdown.
        Default: 'lock' (safest option).
        """
        val = self.get("sleepguard_action", "lock").lower()
        if val not in ("lock", "sleep", "hibernate", "shutdown"):
            val = "lock"
        return val

    @sleepguard_action.setter
    def sleepguard_action(self, value: str) -> None:
        val = value.lower()
        if val not in ("lock", "sleep", "hibernate", "shutdown"):
            val = "lock"
        self.set("sleepguard_action", val)

    @property
    def idle_timeout_minutes(self) -> int:
        return self.get_int("idle_timeout_minutes", 20)

    @idle_timeout_minutes.setter
    def idle_timeout_minutes(self, value: int) -> None:
        self.set_int("idle_timeout_minutes", value)

    @property
    def countdown_seconds(self) -> int:
        return self.get_int("countdown_seconds", 60)

    @countdown_seconds.setter
    def countdown_seconds(self, value: int) -> None:
        self.set_int("countdown_seconds", value)

    @property
    def testing_idle_timeout_s(self) -> int:
        return self.get_int("testing_idle_timeout_s", 0)

    @testing_idle_timeout_s.setter
    def testing_idle_timeout_s(self, value: int) -> None:
        self.set_int("testing_idle_timeout_s", value)

    @property
    def shutdown_mode(self) -> str:
        val = self.get("shutdown_mode", "smart").lower()
        if val not in ("smart", "media", "strict"):
            # Map old values if upgrading
            if val == "idle_only": val = "strict"
            elif val == "media_only": val = "smart"
            else: val = "smart"
        return val

    @shutdown_mode.setter
    def shutdown_mode(self, value: str) -> None:
        val = value.lower()
        if val not in ("smart", "media", "strict"):
            val = "smart"
        self.set("shutdown_mode", val)

    @property
    def media_idle_timeout_minutes(self) -> int:
        return self.get_int("media_idle_timeout_minutes", 15)

    @media_idle_timeout_minutes.setter
    def media_idle_timeout_minutes(self, value: int) -> None:
        self.set_int("media_idle_timeout_minutes", value)

    @property
    def media_grace_minutes(self) -> int:
        """Additional grace period (minutes) given when media is actively playing
        at the moment the inactivity threshold is first reached.
        This is a one-shot delay — it cannot be repeated within the same idle cycle.
        Default: 5 minutes. Range: 1–30.
        """
        val = self.get_int("media_grace_minutes", 5)
        return max(1, min(30, val))

    @media_grace_minutes.setter
    def media_grace_minutes(self, value: int) -> None:
        self.set_int("media_grace_minutes", max(1, min(30, int(value))))

    @property
    def bedtime_start(self) -> str:
        return self.get("bedtime_start", "23:00")

    @bedtime_start.setter
    def bedtime_start(self, value: str) -> None:
        self.set("bedtime_start", value)

    @property
    def bedtime_end(self) -> str:
        return self.get("bedtime_end", "06:00")

    @bedtime_end.setter
    def bedtime_end(self, value: str) -> None:
        self.set("bedtime_end", value)

    # Circadian display extensions
    @property
    def circadian_enabled(self) -> bool:
        return self.get_bool("circadian_enabled", False)

    @circadian_enabled.setter
    def circadian_enabled(self, value: bool) -> None:
        self.set_bool("circadian_enabled", value)

    @property
    def circadian_lead_minutes(self) -> int:
        return max(0, min(360, self.get_int("circadian_lead_minutes", 90)))

    @circadian_lead_minutes.setter
    def circadian_lead_minutes(self, value: int) -> None:
        self.set_int("circadian_lead_minutes", max(0, min(360, int(value))))

    @property
    def circadian_target_kelvin(self) -> int:
        return max(1800, min(6500, self.get_int("circadian_target_kelvin", 3400)))

    @circadian_target_kelvin.setter
    def circadian_target_kelvin(self, value: int) -> None:
        self.set_int("circadian_target_kelvin", max(1800, min(6500, int(value))))

    @property
    def debug_tracking(self) -> bool:
        return self.get_bool("debug_tracking", False)

    @debug_tracking.setter
    def debug_tracking(self, value: bool) -> None:
        self.set_bool("debug_tracking", value)

    # Updater Extensions
    @property
    def auto_update_enabled(self) -> bool:
        return self.get_bool("auto_update_enabled", True)

    @auto_update_enabled.setter
    def auto_update_enabled(self, value: bool) -> None:
        self.set_bool("auto_update_enabled", value)

    @property
    def notify_updates(self) -> bool:
        return self.get_bool("notify_updates", True)

    @notify_updates.setter
    def notify_updates(self, value: bool) -> None:
        self.set_bool("notify_updates", value)

    @property
    def last_update_check(self) -> str:
        return self.get("last_update_check", "")

    @last_update_check.setter
    def last_update_check(self, value: str) -> None:
        self.set("last_update_check", value)

    @property
    def install_id(self) -> str:
        import uuid
        val = self.get("install_id", "")
        if not val:
            val = str(uuid.uuid4())
            self.set("install_id", val)
        return val

