"""
debug_lifecycle.py — lifecycle state dumper for shutdown debugging.
Call log_lifecycle_state(label) at any point to dump:
  - every active Python thread (name, id, daemon, alive)
  - every QTimer found via gc (active, interval)
  - every QThread found via gc
  - every QSystemTrayIcon found via gc
  - every top-level Qt widget
Remove this module once the root cause is confirmed.
"""
from __future__ import annotations

import gc
import threading


def log_lifecycle_state(label: str) -> None:
    """Dump the full lifecycle state to the application log."""
    from core.logger import logger

    sep = "=" * 60
    logger.info("%s", sep)
    logger.info("LIFECYCLE SNAPSHOT: %s", label)
    logger.info("%s", sep)

    # ── 1. Python threads ────────────────────────────────────────
    all_threads = threading.enumerate()
    logger.info("[THREADS] Active Python threads: %d", len(all_threads))
    for t in all_threads:
        logger.info(
            "  thread  name=%-30s  id=%-8s  daemon=%-5s  alive=%s",
            repr(t.name), t.ident, t.daemon, t.is_alive(),
        )

    # ── 2. Qt top-level widgets ───────────────────────────────────
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            widgets = app.topLevelWidgets()
            logger.info("[QT] Top-level widgets: %d", len(widgets))
            for w in widgets:
                logger.info(
                    "  widget  type=%-30s  visible=%-5s  title=%s",
                    type(w).__name__, w.isVisible(), repr(w.windowTitle()),
                )
            windows = app.topLevelWindows()
            logger.info("[QT] Top-level windows: %d", len(windows))
            for w in windows:
                try:
                    logger.info(
                        "  window  type=%-30s  visible=%-5s  title=%s",
                        type(w).__name__, w.isVisible(), repr(w.title()),
                    )
                except Exception:
                    logger.info("  window  type=%s  (title error)", type(w).__name__)
        else:
            logger.info("[QT] No QApplication instance found.")
    except Exception as exc:
        logger.info("[QT] Widget inspection error: %s", exc)

    # ── 3. QTimer instances (via gc) ──────────────────────────────
    try:
        from PySide6.QtCore import QTimer
        timers = [o for o in gc.get_objects() if type(o) is QTimer]
        active = [t for t in timers if t.isActive()]
        logger.info("[QTIMER] Total QTimer objects in gc: %d  (active: %d)", len(timers), len(active))
        for t in timers:
            try:
                logger.info(
                    "  timer  active=%-5s  interval=%dms  singleShot=%s",
                    t.isActive(), t.interval(), t.isSingleShot(),
                )
            except Exception:
                logger.info("  timer  (inspection failed)")
    except Exception as exc:
        logger.info("[QTIMER] Inspection error: %s", exc)

    # ── 4. QThread instances (via gc) ────────────────────────────
    try:
        from PySide6.QtCore import QThread
        qthreads = [o for o in gc.get_objects() if isinstance(o, QThread)]
        logger.info("[QTHREAD] QThread objects in gc: %d", len(qthreads))
        for t in qthreads:
            try:
                logger.info(
                    "  qthread  type=%-30s  running=%s",
                    type(t).__name__, t.isRunning(),
                )
            except Exception:
                logger.info("  qthread  (inspection failed)")
    except Exception as exc:
        logger.info("[QTHREAD] Inspection error: %s", exc)

    # ── 5. QSystemTrayIcon instances (via gc) ────────────────────
    try:
        from PySide6.QtWidgets import QSystemTrayIcon
        trays = [o for o in gc.get_objects() if isinstance(o, QSystemTrayIcon)]
        logger.info("[TRAY] QSystemTrayIcon objects in gc: %d", len(trays))
        for t in trays:
            try:
                logger.info(
                    "  tray  visible=%-5s  tooltip=%s",
                    t.isVisible(), repr(t.toolTip()),
                )
            except Exception:
                logger.info("  tray  (inspection failed)")
    except Exception as exc:
        logger.info("[TRAY] Inspection error: %s", exc)

    logger.info("%s END: %s", sep, label)
