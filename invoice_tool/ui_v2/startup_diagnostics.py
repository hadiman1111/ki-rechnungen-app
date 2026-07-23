"""UI-v2 startup guards — prevent blank windows and surface startup failures."""

from __future__ import annotations

import sys
import traceback
from typing import Any

REQUIRED_FLET_MIN = (0, 85, 0)

DIAGNOSTIC_KEY = "ui-v2-startup-diagnostic"
DIAGNOSTIC_TITLE_KEY = "ui-v2-startup-diagnostic-title"


def get_flet_version_tuple() -> tuple[int, int, int]:
    """Return installed Flet version as (major, minor, patch)."""
    raw = "0.0.0"
    try:
        from flet.version import flet_version as fv  # type: ignore[attr-defined]

        raw = str(fv)
    except Exception:
        try:
            from flet.version import version as fv  # type: ignore[attr-defined]

            raw = str(fv)
        except Exception:
            raw = "0.0.0"

    parts: list[int] = []
    for token in str(raw).split(".")[:3]:
        digits = "".join(ch for ch in token if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def format_flet_version() -> str:
    major, minor, patch = get_flet_version_tuple()
    return f"{major}.{minor}.{patch}"


def flet_meets_ui_v2_requirement() -> bool:
    return get_flet_version_tuple() >= REQUIRED_FLET_MIN


def wrong_flet_version_message() -> tuple[str, str, str]:
    found = format_flet_version()
    title = "UI-v2 Start blockiert: falsche Flet-Version"
    detail = (
        f"Gefunden: Flet {found}. "
        "UI-v2 benötigt Flet >= 0.85 (.venv-flet085). "
        "Mit .venv (Flet 0.28) bleibt das Fenster leer, weil Padding.symmetric fehlt."
    )
    hint = (
        "Bitte neu starten mit:\n"
        ".venv-flet085/bin/python app_ui_v2.py\n"
        "oder: ./scripts/run_ui_v2_flet085.sh"
    )
    return title, detail, hint


def build_startup_diagnostic_control(
    *,
    title: str,
    detail: str,
    hint: str = "",
) -> Any:
    """Build a visible diagnostic panel (no blank window)."""
    import flet as ft

    lines = [
        ft.Text(
            title,
            key=DIAGNOSTIC_TITLE_KEY,
            size=20,
            weight=ft.FontWeight.W_700,
            color="#1a1a1c",
        ),
        ft.Container(height=12),
        ft.Text(detail, size=14, color="#3c3c40"),
    ]
    if hint:
        lines.extend(
            [
                ft.Container(height=16),
                ft.Text(hint, size=13, color="#2558c7", selectable=True),
            ]
        )
    lines.extend(
        [
            ft.Container(height=16),
            ft.Text(
                "Kein produktiver Lauf. Keine PDF-Verarbeitung. Track A unverändert.",
                size=12,
                color="#636368",
            ),
        ]
    )
    return ft.Container(
        key=DIAGNOSTIC_KEY,
        expand=True,
        bgcolor="#f3f2ef",
        padding=24,
        content=ft.Column(lines, expand=True, scroll=ft.ScrollMode.AUTO),
    )


def mount_startup_diagnostic(
    page: Any,
    *,
    title: str,
    detail: str,
    hint: str = "",
    exc: BaseException | None = None,
) -> None:
    """Mount diagnostic controls and log the failure to stderr."""
    if exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        print(f"[UI-v2 startup] {title}: {exc}", file=sys.stderr)
    else:
        print(f"[UI-v2 startup] {title}\n{detail}\n{hint}", file=sys.stderr)

    try:
        page.title = "NAME.IT PRO — Start-Diagnostik"
    except Exception:
        pass
    try:
        page.bgcolor = "#f3f2ef"
    except Exception:
        pass
    try:
        page.padding = 0
    except Exception:
        pass

    control = build_startup_diagnostic_control(title=title, detail=detail, hint=hint)
    try:
        if hasattr(page, "clean") and callable(page.clean):
            page.clean()
        elif hasattr(page, "controls"):
            page.controls.clear()
    except Exception:
        pass

    page.add(control)
    try:
        page.update()
    except Exception:
        pass


def start_ui_v2(page: Any) -> str:
    """Safe UI-v2 root start: workspace on Flet>=0.85, else visible diagnostic.

    Returns:
        "workspace" when the normal shell was mounted,
        "diagnostic" when a visible diagnostic panel was mounted.
    """
    if not flet_meets_ui_v2_requirement():
        title, detail, hint = wrong_flet_version_message()
        mount_startup_diagnostic(page, title=title, detail=detail, hint=hint)
        return "diagnostic"

    try:
        from invoice_tool.ui_v2.app import build_ui_v2

        build_ui_v2(page)
        return "workspace"
    except Exception as exc:
        mount_startup_diagnostic(
            page,
            title="UI-v2 Startfehler — Workspace nicht gerendert",
            detail=f"{type(exc).__name__}: {exc}",
            hint=(
                "Traceback steht im Terminal. "
                "Prüfen Sie Flet >= 0.85 (.venv-flet085/bin/python app_ui_v2.py)."
            ),
            exc=exc,
        )
        return "diagnostic"
