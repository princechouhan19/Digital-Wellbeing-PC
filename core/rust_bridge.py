"""Optional ctypes bridge to the dependency-free Rust core.

The Rust implementation is opt-in until parity tests and the benchmark have
been run on a representative Windows build. Missing/incompatible native code is
not fatal: callers receive ``None`` and keep using their Python implementation.
Set ``DW_USE_RUST_CORE=1`` and optionally ``DW_RUST_CORE_LIBRARY`` to enable it.
"""
from __future__ import annotations

import ctypes
import os
import sys
import threading
from pathlib import Path
from typing import Optional

_ABI_VERSION = 4
_LOAD_LOCK = threading.Lock()
_LOAD_ATTEMPTED = False
_LIBRARY: Optional[ctypes.CDLL] = None


class _UrlRuleView(ctypes.Structure):
    _fields_ = [
        ("host", ctypes.c_void_p),
        ("path", ctypes.c_void_p),
        ("action", ctypes.c_uint8),
        ("enabled", ctypes.c_uint8),
    ]


def _enabled() -> bool:
    return os.environ.get("DW_USE_RUST_CORE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _library_names() -> tuple[str, ...]:
    if sys.platform == "win32":
        return ("digital_wellbeing_core.dll",)
    if sys.platform == "darwin":
        return ("libdigital_wellbeing_core.dylib", "digital_wellbeing_core.dylib")
    return ("libdigital_wellbeing_core.so",)


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    explicit = os.environ.get("DW_RUST_CORE_LIBRARY", "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())

    names = _library_names()
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        candidates.extend(Path(frozen_root) / name for name in names)

    project_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        project_root / "rust-core" / "target" / "release" / name
        for name in names
    )
    executable_dir = Path(sys.executable).resolve().parent
    candidates.extend(executable_dir / name for name in names)

    # Preserve search order while removing duplicate paths.
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _configure_library(library: ctypes.CDLL) -> bool:
    try:
        library.dw_core_abi_version.argtypes = []
        library.dw_core_abi_version.restype = ctypes.c_uint32
        if library.dw_core_abi_version() != _ABI_VERSION:
            return False

        library.dw_extract_domain_from_title.argtypes = (
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char),
            ctypes.c_size_t,
        )
        library.dw_extract_domain_from_title.restype = ctypes.c_ssize_t

        library.dw_normalize_domain.argtypes = (
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char),
            ctypes.c_size_t,
        )
        library.dw_normalize_domain.restype = ctypes.c_ssize_t

        library.dw_domain_matches.argtypes = (ctypes.c_char_p, ctypes.c_char_p)
        library.dw_domain_matches.restype = ctypes.c_int32

        library.dw_select_url_rule.argtypes = (
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_uint8,
            ctypes.POINTER(_UrlRuleView),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_ssize_t),
        )
        library.dw_select_url_rule.restype = ctypes.c_int32

        library.dw_categorize_process.argtypes = (
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_char),
            ctypes.c_size_t,
        )
        library.dw_categorize_process.restype = ctypes.c_int32

        library.dw_decide_tracking_transition.argtypes = (
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_uint64,
        )
        library.dw_decide_tracking_transition.restype = ctypes.c_uint32
        return True
    except (AttributeError, OSError, TypeError):
        return False


def _load_library() -> Optional[ctypes.CDLL]:
    global _LOAD_ATTEMPTED, _LIBRARY
    if not _enabled():
        return None
    if _LOAD_ATTEMPTED:
        return _LIBRARY

    with _LOAD_LOCK:
        if _LOAD_ATTEMPTED:
            return _LIBRARY
        _LOAD_ATTEMPTED = True
        for path in _candidate_paths():
            if not path.is_file():
                continue
            try:
                library = ctypes.CDLL(str(path))
            except OSError:
                continue
            if _configure_library(library):
                _LIBRARY = library
                break
    return _LIBRARY


def rust_core_available() -> bool:
    """Return whether the opt-in native library is loadable and ABI-compatible."""
    return _load_library() is not None


def _encode(value: str) -> Optional[ctypes.Array]:
    try:
        encoded = value.encode("utf-8")
    except (AttributeError, UnicodeEncodeError):
        return None
    if b"\0" in encoded:
        return None
    return ctypes.create_string_buffer(encoded)


def _call_string_function(function_name: str, value: str) -> Optional[str]:
    library = _load_library()
    if library is None:
        return None
    input_buffer = _encode(value)
    if input_buffer is None:
        return None

    output = ctypes.create_string_buffer(512)
    function = getattr(library, function_name)
    try:
        written = function(
            ctypes.cast(input_buffer, ctypes.c_char_p),
            ctypes.cast(output, ctypes.POINTER(ctypes.c_char)),
            ctypes.sizeof(output),
        )
    except (OSError, ValueError, TypeError):
        return None
    if written < 0 or written >= ctypes.sizeof(output):
        return None
    try:
        return output.raw[:written].decode("utf-8")
    except UnicodeDecodeError:
        return None


def extract_domain_from_title(title: str) -> Optional[str]:
    """Return the Rust result, or ``None`` when native code should be bypassed.

    An empty string is a valid Rust result meaning that the title had no
    recognizable domain; ``None`` means that Python should run its fallback.
    """
    return _call_string_function("dw_extract_domain_from_title", title)


def normalize_domain(value: str) -> Optional[str]:
    """Normalize a domain through Rust, or return ``None`` for Python fallback."""
    return _call_string_function("dw_normalize_domain", value)


def domain_matches(host: str, rule_host: str) -> Optional[bool]:
    """Compare hosts in Rust, returning ``None`` when the native path is absent."""
    library = _load_library()
    if library is None:
        return None
    host_buffer = _encode(host)
    rule_buffer = _encode(rule_host)
    if host_buffer is None or rule_buffer is None:
        return None
    try:
        result = library.dw_domain_matches(
            ctypes.cast(host_buffer, ctypes.c_char_p),
            ctypes.cast(rule_buffer, ctypes.c_char_p),
        )
    except (OSError, ValueError, TypeError):
        return None
    if result not in (0, 1):
        return None
    return result == 1


def select_url_rule(
    url_host: str,
    url_path: str,
    default_action: str,
    rules: list[tuple[str, str, str, bool]],
) -> Optional[tuple[str, Optional[int]]]:
    """Select a normalized URL rule in Rust; return ``None`` to use Python."""
    library = _load_library()
    if library is None or len(rules) > 4_096:
        return None
    action_codes = {"allow": 0, "block": 1}
    if default_action not in action_codes:
        return None

    host_buffer = _encode(url_host)
    path_buffer = _encode(url_path)
    if host_buffer is None or path_buffer is None:
        return None

    views = (_UrlRuleView * len(rules))() if rules else None
    rule_buffers: list[ctypes.Array] = []
    for index, (rule_host, rule_path, action, enabled) in enumerate(rules):
        action_code = action_codes.get(action)
        rule_host_buffer = _encode(rule_host)
        rule_path_buffer = _encode(rule_path)
        if action_code is None or rule_host_buffer is None or rule_path_buffer is None:
            return None
        rule_buffers.extend((rule_host_buffer, rule_path_buffer))
        assert views is not None
        views[index].host = ctypes.cast(rule_host_buffer, ctypes.c_void_p)
        views[index].path = ctypes.cast(rule_path_buffer, ctypes.c_void_p)
        views[index].action = action_code
        views[index].enabled = int(bool(enabled))

    selected_index = ctypes.c_ssize_t(-1)
    try:
        action_code = int(
            library.dw_select_url_rule(
                ctypes.cast(host_buffer, ctypes.c_char_p),
                ctypes.cast(path_buffer, ctypes.c_char_p),
                action_codes[default_action],
                views,
                len(rules),
                ctypes.byref(selected_index),
            )
        )
    except (OSError, OverflowError, TypeError, ValueError):
        return None
    if action_code not in (0, 1):
        return None
    if selected_index.value < -1 or selected_index.value >= len(rules):
        return None
    action = "allow" if action_code == 0 else "block"
    return action, (selected_index.value if selected_index.value >= 0 else None)


def categorize_process(
    process_name: str,
    exe_path: str = "",
) -> Optional[tuple[int, int, str]]:
    """Return native category/reason codes, or ``None`` for Python fallback."""
    library = _load_library()
    if library is None:
        return None
    name_buffer = _encode(process_name)
    path_buffer = _encode(exe_path)
    if name_buffer is None or path_buffer is None:
        return None

    category = ctypes.c_uint32()
    reason_kind = ctypes.c_uint32()
    reason_value = ctypes.create_string_buffer(512)
    try:
        status = library.dw_categorize_process(
            ctypes.cast(name_buffer, ctypes.c_char_p),
            ctypes.cast(path_buffer, ctypes.c_char_p),
            ctypes.byref(category),
            ctypes.byref(reason_kind),
            ctypes.cast(reason_value, ctypes.POINTER(ctypes.c_char)),
            ctypes.sizeof(reason_value),
        )
    except (OSError, ValueError, TypeError):
        return None
    if status != 0 or category.value not in range(11) or reason_kind.value not in range(4):
        return None
    try:
        decoded_reason = reason_value.value.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return category.value, reason_kind.value, decoded_reason


def decide_tracking_transition(
    has_current_app: bool,
    same_process: bool,
    idle_changed: bool,
    title_changed: bool,
    fullscreen_game: bool,
    session_duration_ms: int,
) -> Optional[int]:
    """Select a Rust tracking transition, or ``None`` to use Python policy."""
    library = _load_library()
    if library is None:
        return None
    try:
        duration_ms = max(0, min(int(session_duration_ms), 0xFFFFFFFFFFFFFFFF))
        result = int(
            library.dw_decide_tracking_transition(
                int(bool(has_current_app)),
                int(bool(same_process)),
                int(bool(idle_changed)),
                int(bool(title_changed)),
                int(bool(fullscreen_game)),
                duration_ms,
            )
        )
    except (OSError, OverflowError, TypeError, ValueError):
        return None
    return result if result in range(7) else None
