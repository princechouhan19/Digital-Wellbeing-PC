"""
url_rules.py — Granular sub-path web rules for Digital Wellbeing.

Rules are intentionally simple and local: each rule is a host + optional path
prefix with an ``allow`` or ``block`` action. The most specific matching rule
wins (longest path, then longest host); if nothing matches, the caller supplies
the default action derived from the Focus mode's domain blocklist.

Examples:
    block  reddit.com/r/all
    allow  reddit.com/r/programming
    block  youtube.com/shorts

A default of ``block`` for reddit.com therefore permits only the productive
sub-path, while a default of ``allow`` for youtube.com blocks only Shorts.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlsplit

_SETTING_KEY = "focus_url_rules"
_VALID_ACTIONS = ("allow", "block")
_HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")


@dataclass(frozen=True)
class UrlRule:
    pattern: str
    action: str
    label: str = ""
    enabled: bool = True
    id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id or uuid.uuid4().hex[:12],
            "pattern": self.pattern,
            "action": self.action,
            "label": self.label,
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class UrlDecision:
    action: str
    reason: str
    matched_rule: Optional[str]
    normalized_url: str
    domain: str


def _split_host_path(value: str) -> Tuple[str, str]:
    """Normalize a URL/rule into (host, /path) without scheme/query/fragment."""
    text = (value or "").strip()
    if not text:
        return "", ""

    if "://" not in text:
        text = "//" + text
    try:
        parsed = urlsplit(text)
    except ValueError:
        return "", ""

    host = (parsed.hostname or "").strip().lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    path = unquote(parsed.path or "").lower()
    if path == "/":
        path = ""
    if path:
        path = path.rstrip("/")
    return host, path


def normalize_url(url: str) -> str:
    host, path = _split_host_path(url)
    return f"{host}{path}" if host else ""


def normalize_pattern(pattern: str) -> str:
    """Validate and normalize a user-entered rule pattern.

    Accepts ``example.com``, ``https://example.com/path`` or
    ``example.com/path?x=1``; rejects patterns without a valid host.
    """
    host, path = _split_host_path(pattern)
    if not host or not _HOST_RE.match(host) or "." not in host:
        return ""
    return f"{host}{path}" if path else host


def domain_of(url: str) -> str:
    host, _ = _split_host_path(url)
    return host


def _host_matches(url_host: str, rule_host: str) -> bool:
    return url_host == rule_host or url_host.endswith("." + rule_host)


def _matches(normalized_url: str, pattern: str) -> bool:
    url_host, url_path = _split_host_path(normalized_url)
    rule_host, rule_path = _split_host_path(pattern)
    if not rule_host or not _host_matches(url_host, rule_host):
        return False
    if not rule_path:
        return True
    return url_path == rule_path or url_path.startswith(rule_path + "/")


class UrlRuleEngine:
    """Pure rule evaluation + SQLite-backed persistence."""

    def __init__(self, repo=None) -> None:
        self._repo = repo

    # ── Persistence ────────────────────────────────────────────────────────

    def load(self) -> List[UrlRule]:
        if self._repo is None:
            from database.repository import Repository

            self._repo = Repository()
        raw = self._repo.get_setting(_SETTING_KEY) or "[]"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        rules: List[UrlRule] = []
        if not isinstance(data, list):
            return rules
        for item in data:
            if not isinstance(item, dict):
                continue
            pattern = normalize_pattern(str(item.get("pattern", "")))
            action = str(item.get("action", "")).lower()
            if not pattern or action not in _VALID_ACTIONS:
                continue
            rules.append(
                UrlRule(
                    pattern=pattern,
                    action=action,
                    label=str(item.get("label", ""))[:80],
                    enabled=bool(item.get("enabled", True)),
                    id=str(item.get("id", "")) or uuid.uuid4().hex[:12],
                )
            )
        return rules

    def save(self, rules: Sequence[UrlRule]) -> None:
        if self._repo is None:
            from database.repository import Repository

            self._repo = Repository()
        payload = [r.to_dict() for r in rules]
        self._repo.set_setting(_SETTING_KEY, json.dumps(payload, separators=(",", ":")))

    def add(self, pattern: str, action: str, label: str = "") -> Optional[UrlRule]:
        normalized = normalize_pattern(pattern)
        action = action.lower()
        if not normalized or action not in _VALID_ACTIONS:
            return None
        rules = self.load()
        rule = UrlRule(
            pattern=normalized,
            action=action,
            label=label.strip()[:80],
            enabled=True,
            id=uuid.uuid4().hex[:12],
        )
        rules.append(rule)
        self.save(rules)
        return rule

    def remove(self, rule_id: str) -> bool:
        rules = self.load()
        remaining = [r for r in rules if r.id != rule_id]
        if len(remaining) == len(rules):
            return False
        self.save(remaining)
        return True

    def set_enabled(self, rule_id: str, enabled: bool) -> bool:
        rules = self.load()
        changed = False
        updated = []
        for rule in rules:
            if rule.id == rule_id:
                rule = UrlRule(
                    pattern=rule.pattern,
                    action=rule.action,
                    label=rule.label,
                    enabled=enabled,
                    id=rule.id,
                )
                changed = True
            updated.append(rule)
        if changed:
            self.save(updated)
        return changed

    # ── Presets & portability ───────────────────────────────────────────────

    def apply_preset(self, preset_name: str) -> int:
        preset = RULE_PRESETS.get(preset_name, [])
        if not preset:
            return 0
        rules = self.load()
        existing = {(r.pattern, r.action) for r in rules}
        added = 0
        for rule in preset:
            if (rule.pattern, rule.action) in existing:
                continue
            rules.append(
                UrlRule(
                    pattern=rule.pattern,
                    action=rule.action,
                    label=rule.label,
                    enabled=True,
                    id=uuid.uuid4().hex[:12],
                )
            )
            existing.add((rule.pattern, rule.action))
            added += 1
        if added:
            self.save(rules)
        return added

    def export_to_file(self, path: str) -> int:
        rules = self.load()
        payload = {
            "format": "digital-wellbeing-url-rules",
            "version": 1,
            "rules": [r.to_dict() for r in rules],
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return len(rules)

    def import_from_file(self, path: str) -> Tuple[int, str]:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return 0, f"Could not read rules: {exc}"
        items = payload.get("rules") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return 0, "File does not contain a rules list."
        rules = self.load()
        existing = {(r.pattern, r.action) for r in rules}
        added = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            pattern = normalize_pattern(str(item.get("pattern", "")))
            action = str(item.get("action", "")).lower()
            if not pattern or action not in _VALID_ACTIONS:
                continue
            if (pattern, action) in existing:
                continue
            rules.append(
                UrlRule(
                    pattern=pattern,
                    action=action,
                    label=str(item.get("label", ""))[:80],
                    enabled=bool(item.get("enabled", True)),
                    id=uuid.uuid4().hex[:12],
                )
            )
            existing.add((pattern, action))
            added += 1
        if added:
            self.save(rules)
        return added, ""

    # ── Evaluation ─────────────────────────────────────────────────────────

    @staticmethod
    def decide(
        url: str,
        default_action: str = "allow",
        rules: Optional[Iterable[UrlRule]] = None,
    ) -> UrlDecision:
        normalized = normalize_url(url)
        domain = domain_of(url)
        default_action = default_action if default_action in _VALID_ACTIONS else "allow"
        if not normalized:
            return UrlDecision(default_action, "No URL supplied", None, "", "")

        best: Optional[UrlRule] = None
        best_key = (-1, -1, 0)
        for rule in rules or []:
            if not rule.enabled:
                continue
            if not _matches(normalized, rule.pattern):
                continue
            rule_host, rule_path = _split_host_path(rule.pattern)
            # Longest path first; then most specific host; ties favour block.
            key = (len(rule_path), len(rule_host), 1 if rule.action == "block" else 0)
            if key > best_key:
                best = rule
                best_key = key

        if best is None:
            return UrlDecision(
                default_action,
                f"Default {default_action} for {domain or 'this page'}",
                None,
                normalized,
                domain,
            )

        return UrlDecision(
            best.action,
            f"{best.action.title()} rule: {best.pattern}",
            best.pattern,
            normalized,
            domain,
        )


def default_rules() -> List[UrlRule]:
    """Suggested starter rules shown in the editor."""
    return [
        UrlRule(pattern="youtube.com/shorts", action="block", label="YouTube Shorts"),
        UrlRule(pattern="reddit.com/r/all", action="block", label="Reddit r/all"),
        UrlRule(pattern="reddit.com/r/programming", action="allow", label="Reddit programming"),
    ]


RULE_PRESETS: dict[str, List[UrlRule]] = {
    "study": [
        UrlRule(pattern="youtube.com/shorts", action="block", label="YouTube Shorts"),
        UrlRule(pattern="reddit.com/r/all", action="block", label="Reddit r/all"),
        UrlRule(pattern="reddit.com/r/programming", action="allow", label="Reddit programming"),
        UrlRule(pattern="youtube.com/education", action="allow", label="YouTube education"),
    ],
    "deep_work": [
        UrlRule(pattern="youtube.com/shorts", action="block", label="YouTube Shorts"),
        UrlRule(pattern="reddit.com/r/all", action="block", label="Reddit r/all"),
        UrlRule(pattern="x.com", action="block", label="X / Twitter"),
        UrlRule(pattern="instagram.com", action="block", label="Instagram"),
        UrlRule(pattern="tiktok.com", action="block", label="TikTok"),
    ],
    "evening": [
        UrlRule(pattern="youtube.com/shorts", action="block", label="YouTube Shorts"),
        UrlRule(pattern="tiktok.com", action="block", label="TikTok"),
        UrlRule(pattern="instagram.com/reels", action="block", label="Instagram Reels"),
        UrlRule(pattern="netflix.com", action="allow", label="Netflix"),
    ],
}
