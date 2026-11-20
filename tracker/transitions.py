"""Pure session-transition policy with an optional Rust implementation.

Win32 sampling, timestamps, database writes and callbacks stay in the Python
tracking adapter. The Rust path only chooses the action for a sampled state.
"""
from __future__ import annotations

import math
from enum import IntEnum
from typing import Optional

from core.rust_bridge import decide_tracking_transition as _rust_decide_transition


class TrackingTransition(IntEnum):
    KEEP = 0
    START = 1
    APP_SWITCH = 2
    IDLE_SWITCH = 3
    FULLSCREEN_TITLE_UPDATE = 4
    TITLE_SPLIT = 5
    TITLE_UPDATE = 6


MIN_TITLE_SPLIT_MS = 2_000
_UINT64_MAX = 0xFFFFFFFFFFFFFFFF


def _select_transition_python(
    has_current_app: bool,
    same_process: bool,
    idle_changed: bool,
    title_changed: bool,
    fullscreen_game: bool,
    session_duration_s: float,
) -> TrackingTransition:
    """Reference policy; keep precedence aligned with the shared Rust corpus."""
    if not has_current_app:
        return TrackingTransition.START
    if not same_process:
        return TrackingTransition.APP_SWITCH
    if idle_changed:
        return TrackingTransition.IDLE_SWITCH
    if title_changed and fullscreen_game:
        return TrackingTransition.FULLSCREEN_TITLE_UPDATE
    if title_changed and session_duration_s >= (MIN_TITLE_SPLIT_MS / 1000.0):
        return TrackingTransition.TITLE_SPLIT
    if title_changed:
        return TrackingTransition.TITLE_UPDATE
    return TrackingTransition.KEEP


def _duration_milliseconds(session_duration_s: float) -> int:
    try:
        duration = float(session_duration_s)
    except (TypeError, ValueError, OverflowError):
        return 0
    if math.isnan(duration) or duration <= 0:
        return 0
    if math.isinf(duration):
        return _UINT64_MAX
    duration_ms = duration * 1000
    if math.isinf(duration_ms):
        return _UINT64_MAX
    return min(int(duration_ms), _UINT64_MAX)


def select_transition(
    has_current_app: bool,
    same_process: bool,
    idle_changed: bool,
    title_changed: bool,
    fullscreen_game: bool,
    session_duration_s: float = 0.0,
) -> TrackingTransition:
    """Select a transition, falling back to the reference policy on any miss."""
    native_code: Optional[int] = _rust_decide_transition(
        has_current_app,
        same_process,
        idle_changed,
        title_changed,
        fullscreen_game,
        _duration_milliseconds(session_duration_s),
    )
    if native_code is not None:
        try:
            return TrackingTransition(native_code)
        except ValueError:
            # Treat an unknown result as a native ABI failure and fail safely.
            pass
    return _select_transition_python(
        has_current_app,
        same_process,
        idle_changed,
        title_changed,
        fullscreen_game,
        session_duration_s,
    )
