"""Read-only active profile display for the internal launcher."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from invoice_tool.app_paths import (
    PROFILE_LOCAL_FILENAME,
    resolve_active_profile_id,
    resolve_profile_path,
    sanitize_profile_display_name,
    user_support_dir,
)
from invoice_tool.profile_compiler import compile_profile_to_rules
from invoice_tool.profile_store import load_profile_bundle
from invoice_tool.scan_models import get_scan_model


@dataclass(frozen=True)
class ProfileDisplayInfo:
    ok: bool
    profile_name: str
    scan_model_id: str
    scan_model_label: str
    profile_path: Path | None
    error_message: str | None = None


def default_active_profile_path() -> Path:
    return user_support_dir() / PROFILE_LOCAL_FILENAME


def load_active_profile_display(profile_path: Path | None = None) -> ProfileDisplayInfo:
    """Load and validate the active profile without mutating it."""
    resolved = (profile_path or resolve_profile_path() or default_active_profile_path()).expanduser()
    if not resolved.is_file():
        return ProfileDisplayInfo(
            ok=False,
            profile_name="",
            scan_model_id="",
            scan_model_label="",
            profile_path=resolved,
            error_message=f"Profil nicht gefunden: {resolved}",
        )

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ProfileDisplayInfo(
            ok=False,
            profile_name="",
            scan_model_id="",
            scan_model_label="",
            profile_path=resolved,
            error_message=f"Profil ist kein gültiges JSON: {exc}",
        )

    if not isinstance(raw, dict):
        return ProfileDisplayInfo(
            ok=False,
            profile_name="",
            scan_model_id="",
            scan_model_label="",
            profile_path=resolved,
            error_message="Profil hat ein ungültiges Format.",
        )

    try:
        compile_profile_to_rules(raw)
    except Exception as exc:
        return ProfileDisplayInfo(
            ok=False,
            profile_name="",
            scan_model_id="",
            scan_model_label="",
            profile_path=resolved,
            error_message=f"Profil konnte nicht kompiliert werden: {exc}",
        )

    profile_id = resolve_active_profile_id()
    try:
        bundle = load_profile_bundle(profile_id)
        scan_model_id = bundle.scan_model_id
        profile_name = sanitize_profile_display_name(bundle.name)
    except Exception:
        scan_model_id = str(raw.get("scan_model_id") or raw.get("active_scan_model") or "rechnungen")
        profile_name = sanitize_profile_display_name(
            str(raw.get("profile_name") or raw.get("name") or "Profil")
        )

    if not scan_model_id.strip():
        return ProfileDisplayInfo(
            ok=False,
            profile_name=profile_name,
            scan_model_id="",
            scan_model_label="",
            profile_path=resolved,
            error_message="Kein aktives Scan-Modell im Profil gefunden.",
        )

    try:
        scan_model_label = get_scan_model(scan_model_id).label
    except KeyError:
        return ProfileDisplayInfo(
            ok=False,
            profile_name=profile_name,
            scan_model_id=scan_model_id,
            scan_model_label="",
            profile_path=resolved,
            error_message=f"Unbekanntes Scan-Modell: {scan_model_id}",
        )

    return ProfileDisplayInfo(
        ok=True,
        profile_name=profile_name,
        scan_model_id=scan_model_id,
        scan_model_label=scan_model_label,
        profile_path=resolved,
    )
