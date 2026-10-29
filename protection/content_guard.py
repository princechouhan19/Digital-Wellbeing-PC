"""
content_guard.py — Always-on parental / productivity URL guard.

Unlike Focus URL rules (which only apply during a session), ContentGuard is a
persistent policy used by the extension bridge and foreground browser checks:

* short-form blockers: YouTube Shorts, Instagram Reels, TikTok, Facebook Reels,
  Snapchat Spotlight;
* category packs: esports, gaming, battle-royale (Free Fire / PUBG / BGMI);
* user-defined domains or sub-path patterns.

Sub-path blocking depends on the bundled browser extension; domain packs are
also matched by the foreground browser check.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import List, Optional

from core.logger import logger
from database.repository import Repository
from protection.url_rules import UrlRule, UrlRuleEngine, domain_of, normalize_pattern

SETTING_ENABLED = "parental_controls_enabled"
SETTING_SHORTFORM = "shortform_blocking_enabled"
SETTING_PRESETS = "content_guard_presets"
SETTING_CUSTOM = "content_guard_custom"

SHORTFORM_PATTERNS = (
    "youtube.com/shorts",
    "youtube.com/reel",
    "youtu.be/shorts",
    "m.youtube.com/shorts",
    "instagram.com/reel",
    "instagram.com/reels",
    "tiktok.com",
    "vm.tiktok.com",
    "m.tiktok.com",
    "facebook.com/reel",
    "facebook.com/reels",
    "fb.watch/reel",
    "snapchat.com/spotlight",
)

PRESET_DOMAINS: dict[str, tuple[str, ...]] = {
    "esports": (
        "twitch.tv",
        "kick.com",
        "esports.net",
        "hltv.org",
        "vlr.gg",
        "dotesports.com",
        "liquipedia.net",
        "afkgaming.com",
        "eslgaming.com",
        "pglesports.com",
        "strafe.com",
        "gosugamers.net",
    ),
    "gaming": (
        "steamcommunity.com",
        "store.steampowered.com",
        "epicgames.com",
        "ea.com",
        "roblox.com",
        "callofduty.com",
        "minecraft.net",
        "xbox.com",
        "riotgames.com",
        "blizzard.com",
        "battle.net",
        "ubisoft.com",
    ),
    "battle_royale": (
        "freefiremobile.com",
        "ff.garena.com",
        "pubgmobile.com",
        "bgmi.com",
        "battlegroundsmobileindia.com",
        "krafton.com",
        "garena.com",
        "mobilelegends.com",
        "callofduty.com/mobile",
        "pubg.com",
    ),
}

PRESET_LABELS = {
    "esports": "Esports & streaming (Twitch, Kick, HLTV, Liquipedia)",
    "gaming": "Gaming platforms (Steam, Epic, EA, Roblox, Riot, Blizzard)",
    "battle_royale": "Battle Royale & Mobile Gaming (Free Fire, PUBG, BGMI, COD Mobile)",
}

_CACHE_SECONDS = 2.0


@dataclass(frozen=True)
class GuardDecision:
    action: str
    reason: str
    rule: str = ""
    category: str = ""

    @property
    def blocked(self) -> bool:
        return self.action == "block"


class ContentGuard:
    _instance: Optional["ContentGuard"] = None

    def __init__(self, repo: Optional[Repository] = None) -> None:
        self._repo = repo or Repository()
        self._loaded_at = 0.0
        self._enabled = False
        self._shortform = True
        self._presets: List[str] = []
        self._custom: List[str] = []
        self._rules: List[UrlRule] = []
        self._domains: set[str] = set()
        self._reload()

    @classmethod
    def instance(cls) -> "ContentGuard":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def invalidate(self) -> None:
        self._loaded_at = 0.0

    def _reload(self) -> None:
        self._enabled = self._get_bool(SETTING_ENABLED, False)
        self._shortform = self._get_bool(SETTING_SHORTFORM, True)
        self._presets = self._read_list(SETTING_PRESETS)
        self._custom = self._read_list(SETTING_CUSTOM)
        rules: List[UrlRule] = []
        if self._shortform:
            for pattern in SHORTFORM_PATTERNS:
                rules.append(UrlRule(pattern=normalize_pattern(pattern), action="block", label="Short-form"))
        for item in self._custom:
            pattern = normalize_pattern(item)
            if not pattern:
                continue
            if "/" in pattern:
                rules.append(UrlRule(pattern=pattern, action="block", label="Custom rule"))
        self._rules = rules
        domains = set()
        for name in self._presets:
            domains.update(PRESET_DOMAINS.get(name, ()))
        for item in self._custom:
            if "/" not in item:
                normalized = domain_of(item)
                if normalized:
                    domains.add(normalized)
        self._domains = domains
        self._loaded_at = time.monotonic()

    def _read_list(self, key: str) -> List[str]:
        raw = self._repo.get_setting(key) or "[]"
        try:
            data = json.loads(raw)
            return [str(v) for v in data if str(v).strip()] if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _get_bool(self, key: str, default: bool) -> bool:
        raw = self._repo.get_setting(key)
        if raw is None:
            return default
        return str(raw).strip().lower() in ("1", "true", "yes", "on")

    def _ensure_fresh(self) -> None:
        if time.monotonic() - self._loaded_at > _CACHE_SECONDS:
            self._reload()

    @property
    def enabled(self) -> bool:
        self._ensure_fresh()
        return self._enabled

    @property
    def shortform_enabled(self) -> bool:
        self._ensure_fresh()
        return self._shortform

    @property
    def presets(self) -> List[str]:
        self._ensure_fresh()
        return list(self._presets)

    @property
    def custom_items(self) -> List[str]:
        self._ensure_fresh()
        return list(self._custom)

    def evaluate(self, url: str) -> GuardDecision:
        self._ensure_fresh()
        if not self._enabled:
            return GuardDecision("allow", "Parental controls are off")
        domain = domain_of(url)
        if domain and self._domains and any(
            domain == blocked or domain.endswith("." + blocked)
            for blocked in self._domains
        ):
            return GuardDecision("block", "Blocked by parental controls", domain, "domain")
        if self._rules:
            decision = UrlRuleEngine.decide(url, default_action="allow", rules=self._rules)
            if decision.action == "block":
                return GuardDecision(
                    "block",
                    decision.reason or "Blocked by parental controls",
                    decision.matched_rule or "",
                    "shortform" if decision.matched_rule in SHORTFORM_PATTERNS else "custom",
                )
        return GuardDecision("allow", "Allowed")

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "shortform": self.shortform_enabled,
            "presets": self.presets,
            "custom": self.custom_items,
            "rules": len(self._rules),
            "domains": len(self._domains),
        }

    # -- mutators used by Settings -----------------------------------------

    def set_enabled(self, enabled: bool) -> None:
        self._repo.set_setting(SETTING_ENABLED, "true" if enabled else "false")
        self.invalidate()

    def set_shortform(self, enabled: bool) -> None:
        self._repo.set_setting(SETTING_SHORTFORM, "true" if enabled else "false")
        self.invalidate()

    def set_presets(self, values: List[str]) -> None:
        valid = [v for v in values if v in PRESET_DOMAINS]
        self._repo.set_setting(SETTING_PRESETS, json.dumps(valid))
        self.invalidate()

    def add_custom(self, value: str) -> bool:
        pattern = normalize_pattern(value)
        if not pattern:
            return False
        self._ensure_fresh()
        items = [item for item in self._custom if item.lower() != pattern.lower()]
        items.append(pattern)
        self._repo.set_setting(SETTING_CUSTOM, json.dumps(items))
        self.invalidate()
        return True

    def remove_custom(self, value: str) -> None:
        self._ensure_fresh()
        items = [item for item in self._custom if item.lower() != value.lower()]
        self._repo.set_setting(SETTING_CUSTOM, json.dumps(items))
        self.invalidate()
