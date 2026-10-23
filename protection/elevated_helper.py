"""
elevated_helper.py — Single-action privileged worker for hosts-file operations.

Invoked as:
    <exe> --elevated-helper --action <focus-apply|focus-remove|content-apply|content-remove> [--domains a.com,b.com]

Runs only under an elevated (administrator) token, performs exactly one
hosts mutation, writes a JSON status handshake to AppData, and exits.
It never touches the GUI, the tracker, or any other subsystem.
"""
from __future__ import annotations

from typing import List

from core.logger import logger
from utils.elevation import write_status


def run_elevated_action(action: str, domains_csv: str = "") -> bool:
    """Execute a privileged hosts operation. Returns True on success."""
    logger.info("[ELEVATED_HELPER] action=%s domains=%d chars", action, len(domains_csv))

    try:
        if action == "focus-apply":
            return _apply_focus(domains_csv)
        if action == "focus-remove":
            return _remove_focus()
        if action == "content-apply":
            return _apply_content_filter()
        if action == "content-remove":
            return _remove_content_filter()
        write_status(action, False, "Unknown action", f"Unsupported action: {action}")
        return False
    except Exception as exc:
        logger.critical("[ELEVATED_HELPER] Fatal error: %s", exc, exc_info=True)
        write_status(action, False, "Unexpected error", str(exc))
        return False


def _apply_focus(domains_csv: str) -> bool:
    from protection.website_blocker import WebsiteBlocker
    domains: List[str] = [d for d in (domains_csv or "").split(",") if d.strip()]
    blocker = WebsiteBlocker()
    ok, msg = blocker.block_websites(domains)
    write_status("focus-apply", ok, msg, "" if ok else msg)
    return ok


def _remove_focus() -> bool:
    from protection.website_blocker import WebsiteBlocker
    blocker = WebsiteBlocker()
    ok, msg = blocker.unblock_all()
    write_status("focus-remove", ok, msg, "" if ok else msg)
    return ok


def _apply_content_filter() -> bool:
    from protection.content_blocker import ContentBlocker
    blocker = ContentBlocker.instance()
    ok, msg = blocker.apply_hosts_block_elevated()
    write_status("content-apply", ok, msg, "" if ok else msg)
    return ok


def _remove_content_filter() -> bool:
    from protection.content_blocker import ContentBlocker
    blocker = ContentBlocker.instance()
    ok, msg = blocker.remove_hosts_block_elevated()
    write_status("content-remove", ok, msg, "" if ok else msg)
    return ok
