"""Safe path resolution and display helpers for UI-v2 read-only views."""

from __future__ import annotations

import os
from pathlib import Path

from invoice_tool.configuration_model import destination_display
from invoice_tool.file_lifecycle import PathSafetyError, resolve_safe_target_directory
from invoice_tool.target_routing import DEST_TYPE_LEGACY_RELATIVE, DEST_TYPE_LOCAL


def resolve_output_root() -> Path | None:
    """Configured ausgangsordner — base for legacy-relative routing folders."""
    try:
        from invoice_tool.app_paths import resolve_invoice_config_path
        from invoice_tool.config import load_app_config

        config_path = resolve_invoice_config_path()
        if not config_path.is_file():
            return None
        return load_app_config(config_path).ausgangsordner
    except Exception:
        return None


def resolve_configured_path(raw: str, *, base_dir: Path | None = None) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    expanded = os.path.expanduser(text)
    path = Path(expanded)
    if not path.is_absolute():
        root = base_dir or Path.cwd()
        path = (root / path).resolve()
    else:
        path = path.resolve()
    return path


def resolve_destination_path(
    destination: dict[str, str] | None = None,
    *,
    raw_path: str | None = None,
    base_dir: Path | None = None,
) -> Path | None:
    """Resolve a configuration destination to an absolute path."""
    if destination is not None:
        dest_type = str(destination.get("type") or DEST_TYPE_LOCAL)
        path = str(destination.get("path") or "").strip()
    else:
        dest_type = DEST_TYPE_LOCAL
        path = str(raw_path or "").strip()

    if not path:
        return None

    expanded = Path(os.path.expanduser(path))
    if expanded.is_absolute():
        return expanded.resolve()

    output_root = resolve_output_root()
    if dest_type == DEST_TYPE_LEGACY_RELATIVE:
        if output_root is None:
            return None
        try:
            return resolve_safe_target_directory(output_root.resolve(), path)
        except PathSafetyError:
            return None

    if output_root is not None:
        try:
            return resolve_safe_target_directory(output_root.resolve(), path)
        except PathSafetyError:
            pass

    return resolve_configured_path(path, base_dir=base_dir)


def format_resolved_path(path: Path) -> str:
    home = Path.home()
    try:
        rel = path.resolve().relative_to(home.resolve())
        return f"~/{rel.as_posix()}"
    except ValueError:
        return str(path.resolve())


def destination_summary_for_display(destination: dict[str, str]) -> str:
    raw = str(destination.get("path") or "").strip()
    if not raw:
        return "Noch nicht konfiguriert"
    resolved = resolve_destination_path(destination)
    if resolved is None:
        return destination_display(raw)
    return format_resolved_path(resolved)


def destination_is_missing(destination: dict[str, str]) -> bool:
    raw = str(destination.get("path") or "").strip()
    if not raw:
        return True

    dest_type = str(destination.get("type") or DEST_TYPE_LOCAL)
    if dest_type == DEST_TYPE_LEGACY_RELATIVE:
        output_root = resolve_output_root()
        if output_root is None or not output_root.is_dir():
            return True
        try:
            resolve_safe_target_directory(output_root.resolve(), raw)
            return False
        except PathSafetyError:
            return True

    resolved = resolve_destination_path(destination)
    if resolved is None:
        return True
    return not resolved.is_dir()


def sanitize_path_for_display(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return "Noch nicht konfiguriert"
    resolved = resolve_destination_path(raw_path=text)
    if resolved is not None:
        return format_resolved_path(resolved)
    return destination_display(text)


def path_exists_on_disk(raw: str, *, base_dir: Path | None = None) -> bool:
    path = resolve_destination_path(raw_path=raw, base_dir=base_dir)
    if path is None:
        return False
    return path.is_dir()


def folder_name_summary(raw: str, *, base_dir: Path | None = None) -> str:
    path = resolve_destination_path(raw_path=raw, base_dir=base_dir)
    if path is None:
        return "—"
    return path.name or "—"


def redact_private_path(text: str) -> str:
    home = str(Path.home())
    if home and home in text:
        return text.replace(home, "~")
    return text
