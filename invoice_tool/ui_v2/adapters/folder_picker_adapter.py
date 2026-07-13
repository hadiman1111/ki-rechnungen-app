"""Folder picker and validation helpers for UI-v2."""

from __future__ import annotations

import flet as ft

from invoice_tool.ui_v2.adapters.path_display import path_exists_on_disk, sanitize_path_for_display
from invoice_tool.ui_v2.adapters.write_result import WriteOperationResult
from invoice_tool.ui_v2.validation import validate_target_folder


async def choose_target_folder(*, dialog_title: str = "Zielordner auswählen") -> str | None:
    path = await ft.FilePicker().get_directory_path(dialog_title=dialog_title)
    if path and str(path).strip():
        return str(path).strip()
    return None


def validate_target_folder_selection(path: str, *, require_exists: bool = True) -> WriteOperationResult:
    errors = validate_target_folder(path, require_exists=require_exists)
    if errors:
        return WriteOperationResult.fail(*errors)
    return WriteOperationResult.ok(message="Zielordner gültig.")


def folder_selection_summary(path: str) -> tuple[str, bool]:
    cleaned = (path or "").strip()
    if not cleaned:
        return "Ordner noch auswählen", False
    return sanitize_path_for_display(cleaned), path_exists_on_disk(cleaned)
