"""Persistente Startup-Diagnose für Standalone- und Entwicklungsläufe."""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

LOG_PATH = Path.home() / "Library/Application Support/KI-Rechnungen/logs/ui-startup.log"


def log_startup(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def log_startup_exception(context: str) -> None:
    log_startup(f"{context}:\n{traceback.format_exc()}")


def install_exception_hook() -> None:
    previous_hook = sys.excepthook

    def hook(exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        log_startup_exception(f"Unhandled {getattr(exc_type, '__name__', exc_type)}")
        previous_hook(exc_type, exc, tb)

    sys.excepthook = hook
