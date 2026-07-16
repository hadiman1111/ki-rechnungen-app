"""Canonical folder destination model for profile routing (CFG-001).

Persists user-configured relative or absolute output targets and resolves them
safely at runtime. Legacy ``folder_name`` entries are migrated on read.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from invoice_tool.file_lifecycle import PathSafetyError, path_is_within, resolve_safe_target_directory

MODE_RELATIVE = "relative_to_output_root"
MODE_ABSOLUTE = "absolute"
VALID_MODES = frozenset({MODE_RELATIVE, MODE_ABSOLUTE})


def normalize_folder_destination(folder: dict[str, Any]) -> dict[str, str]:
    """Return canonical ``{mode, path}`` from a folders[] entry."""
    if not isinstance(folder, dict):
        raise ValueError("Ordner-Eintrag muss ein dict sein.")

    destination = folder.get("destination")
    if isinstance(destination, dict):
        mode = str(destination.get("mode") or MODE_RELATIVE).strip()
        path = str(destination.get("path") or "").strip()
        if path:
            return {"mode": mode, "path": path}

    legacy = folder.get("folder_name") or folder.get("name")
    if legacy is not None and str(legacy).strip():
        return {"mode": MODE_RELATIVE, "path": str(legacy).strip()}

    folder_id = folder.get("id", "?")
    raise ValueError(
        f"Ordner '{folder_id}' hat weder 'destination' noch 'folder_name'."
    )


def destination_from_folder_entry(folder: dict[str, Any]) -> dict[str, str]:
    """Alias for :func:`normalize_folder_destination`."""
    return normalize_folder_destination(folder)


def migrate_folder_entry(folder: dict[str, Any]) -> dict[str, Any]:
    """Ensure a folder dict contains a canonical ``destination`` field."""
    result = dict(folder)
    dest = normalize_folder_destination(result)
    result["destination"] = dest
    if "folder_name" not in result and dest["mode"] == MODE_RELATIVE:
        result["folder_name"] = dest["path"]
    return result


def migrate_profile_destinations(profile: dict[str, Any]) -> dict[str, Any]:
    """Return a profile copy with normalized ``destination`` on every folder."""
    result = dict(profile)
    folders = result.get("folders")
    if not isinstance(folders, list):
        return result
    result["folders"] = [
        migrate_folder_entry(f) if isinstance(f, dict) else f for f in folders
    ]
    return result


def validate_destination(
    destination: dict[str, Any],
    *,
    prefix: str = "destination",
) -> list[str]:
    """Validate a destination dict; return German error messages."""
    errors: list[str] = []
    if not isinstance(destination, dict):
        return [f"{prefix}: muss ein Objekt sein."]

    mode = destination.get("mode")
    path = destination.get("path")

    if mode not in VALID_MODES:
        errors.append(
            f"{prefix}: mode muss '{MODE_RELATIVE}' oder '{MODE_ABSOLUTE}' sein "
            f"(ist {mode!r})."
        )

    if not path or not isinstance(path, str) or not str(path).strip():
        errors.append(f"{prefix}: path fehlt oder ist leer.")
        return errors

    path_str = str(path).strip()

    if mode == MODE_RELATIVE:
        normalized = path_str.replace("\\", "/")
        if normalized.startswith("/") or ":" in normalized:
            errors.append(
                f"{prefix}: relativer Pfad darf nicht absolut sein ({path_str!r})."
            )
        for part in Path(normalized).parts:
            if part in ("", ".", ".."):
                errors.append(
                    f"{prefix}: ungültiger relativer Pfadbestandteil '{part}'."
                )
    elif mode == MODE_ABSOLUTE:
        expanded = os.path.expanduser(path_str)
        candidate = Path(expanded)
        if not candidate.is_absolute():
            errors.append(
                f"{prefix}: absoluter Pfad muss vollständig qualifiziert sein "
                f"({path_str!r})."
            )
        else:
            for part in candidate.parts:
                if part == "..":
                    errors.append(
                        f"{prefix}: absoluter Pfad darf '..' nicht enthalten."
                    )
                    break

    return errors


def format_destination_display(
    destination: dict[str, str],
    *,
    output_root: Path | None = None,
) -> str:
    """Human-readable destination label for UI."""
    mode = destination.get("mode", MODE_RELATIVE)
    path = destination.get("path", "")
    if mode == MODE_ABSOLUTE:
        return f"Absolut: {path}"
    if output_root is not None:
        try:
            resolved = resolve_configured_target_directory(output_root, destination)
            return f"Relativ: {path} → {resolved}"
        except PathSafetyError:
            pass
    return f"Relativ: {path}"


def resolve_configured_target_directory(
    output_root: Path,
    destination: dict[str, str],
) -> Path:
    """Resolve a configured destination to an absolute target directory."""
    mode = destination.get("mode", MODE_RELATIVE)
    path = str(destination.get("path") or "").strip()
    if not path:
        raise PathSafetyError(
            "Zielordner-Pfad ist leer",
            code="invalid_target_directory",
            status="output_failed",
        )

    if mode == MODE_ABSOLUTE:
        return _resolve_absolute_target_directory(path)

    if mode != MODE_RELATIVE:
        raise PathSafetyError(
            f"Unbekannter Zielmodus: {mode}",
            code="invalid_target_mode",
            status="output_failed",
        )

    return resolve_safe_target_directory(output_root.resolve(), path)


def _resolve_absolute_target_directory(path_str: str) -> Path:
    expanded = os.path.expanduser(path_str.strip())
    candidate = Path(expanded)
    if not candidate.is_absolute():
        raise PathSafetyError(
            f"Absoluter Zielordner ist nicht vollständig qualifiziert: {path_str}",
            code="absolute_target_rejected",
            status="output_failed",
        )
    for part in candidate.parts:
        if part == "..":
            raise PathSafetyError(
                f"Pfad-Traversal im absoluten Zielordner abgelehnt: {path_str}",
                code="path_traversal",
                status="output_failed",
            )
    return candidate.resolve()


def build_folder_destinations(folders: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Build folder_id → destination map from profile folders."""
    result: dict[str, dict[str, str]] = {}
    for folder in folders:
        if not isinstance(folder, dict):
            continue
        folder_id = folder.get("id")
        if not folder_id:
            continue
        try:
            result[str(folder_id)] = normalize_folder_destination(folder)
        except ValueError:
            continue
    return result


def resolve_folder_by_id(
    folder_id: str,
    folder_destinations: dict[str, dict[str, str]],
    output_root: Path,
) -> Path:
    """Resolve a folder id through the compiled destination map."""
    destination = folder_destinations.get(folder_id)
    if destination is None:
        raise PathSafetyError(
            f"Unbekannter Zielordner '{folder_id}'",
            code="unknown_target_folder",
            status="output_failed",
        )
    return resolve_configured_target_directory(output_root, destination)


def resolve_routing_folder_key(
    folder_key: str,
    *,
    output_root: Path,
    folder_destinations: dict[str, dict[str, str]],
    zielordner_map: dict[str, str],
) -> Path:
    """Resolve invoice routing zielordner key to a target directory.

    Prefers ``folder_destinations[folder_key]`` when present; otherwise uses the
    legacy ``zielordner_map`` value as a relative path under ``output_root``.
    """
    key = str(folder_key or "").strip()
    if not key:
        raise PathSafetyError(
            "Routing-Zielordner ist leer",
            code="invalid_target_directory",
            status="output_failed",
        )

    if key in folder_destinations:
        return resolve_configured_target_directory(output_root, folder_destinations[key])

    mapped = zielordner_map.get(key, key)
    return resolve_safe_target_directory(output_root.resolve(), str(mapped))


def destination_display_name(destination: dict[str, str]) -> str:
    """Short display string for dropdowns."""
    mode = destination.get("mode", MODE_RELATIVE)
    path = destination.get("path", "")
    if mode == MODE_ABSOLUTE:
        return path
    return path


def _path_under_forbidden_root(resolved: Path, forbidden: Path) -> bool:
    try:
        forbidden_resolved = forbidden.resolve()
    except OSError:
        return False
    return path_is_within(resolved, forbidden_resolved)


def _is_unsafe_project_code_path(
    resolved: Path,
    *,
    project_root_path: Path,
    output_root: Path,
) -> bool:
    """Reject destinations inside application source trees, not user output areas."""
    if path_is_within(resolved, output_root.resolve()):
        return False
    code_dirs = ("invoice_tool", "scripts", ".venv", ".venv-flet085")
    project_resolved = project_root_path.resolve()
    for subdir in code_dirs:
        candidate = project_resolved / subdir
        if candidate.exists() and path_is_within(resolved, candidate.resolve()):
            return True
    return False


def validate_runtime_destinations_preflight(
    profile: dict,
    *,
    output_root: Path,
    source_root: Path,
    run_support_root: Path,
    project_root_path: Path,
    archive_dirname: str = "archiv",
) -> list[str]:
    """Validate all configured destinations before a processing run starts.

    Returns German error messages identifying the affected folder, fallback,
    or document rule. An empty list means all destinations are safe to use.
    """
    errors: list[str] = []
    output_root = output_root.resolve()
    source_root = source_root.resolve()
    archive_root = (source_root / archive_dirname).resolve()
    forbidden_roots = (
        archive_root,
        run_support_root.resolve(),
    )

    folders = profile.get("folders")
    if not isinstance(folders, list):
        return []

    folder_destinations: dict[str, dict[str, str]] = {}
    for idx, folder in enumerate(folders):
        if not isinstance(folder, dict):
            continue
        folder_id = str(folder.get("id") or f"index-{idx}")
        prefix = f"folders[{folder_id}]"
        try:
            destination = normalize_folder_destination(folder)
        except ValueError as exc:
            errors.append(f"{prefix}: {exc}")
            continue

        folder_errors = validate_destination(destination, prefix=f"{prefix}.destination")
        errors.extend(folder_errors)
        if folder_errors:
            continue

        try:
            resolved = resolve_configured_target_directory(output_root, destination)
        except PathSafetyError as exc:
            errors.append(f"{prefix}: {exc}")
            continue

        if destination["mode"] == MODE_ABSOLUTE:
            expanded = Path(os.path.expanduser(destination["path"]))
            if not expanded.exists():
                errors.append(f"{prefix}: absoluter Zielordner existiert nicht: {destination['path']}")
            elif not expanded.is_dir():
                errors.append(f"{prefix}: absoluter Zielordner ist kein Verzeichnis: {destination['path']}")

        for forbidden in forbidden_roots:
            if _path_under_forbidden_root(resolved, forbidden):
                errors.append(
                    f"{prefix}: Zielordner liegt in einem verbotenen Bereich: {resolved}"
                )
                break
        else:
            if _is_unsafe_project_code_path(
                resolved,
                project_root_path=project_root_path,
                output_root=output_root,
            ):
                errors.append(
                    f"{prefix}: Zielordner liegt im Anwendungscode-Verzeichnis: {resolved}"
                )

        folder_destinations[folder_id] = destination

    review = profile.get("review_policy")
    if isinstance(review, dict):
        unclear_id = review.get("unclear_folder_id")
        if unclear_id:
            prefix = f"review_policy.unclear_folder_id='{unclear_id}'"
            destination = folder_destinations.get(str(unclear_id))
            if destination is None:
                errors.append(f"{prefix}: existiert nicht in folders.")
            else:
                try:
                    resolved = resolve_configured_target_directory(output_root, destination)
                    for forbidden in forbidden_roots:
                        if _path_under_forbidden_root(resolved, forbidden):
                            errors.append(
                                f"{prefix}: Fallback-Ziel liegt in einem verbotenen Bereich: {resolved}"
                            )
                            break
                    else:
                        if _is_unsafe_project_code_path(
                            resolved,
                            project_root_path=project_root_path,
                            output_root=output_root,
                        ):
                            errors.append(
                                f"{prefix}: Fallback-Ziel liegt im Anwendungscode-Verzeichnis: {resolved}"
                            )
                except PathSafetyError as exc:
                    errors.append(f"{prefix}: {exc}")

    for dp in profile.get("document_profiles") or []:
        if not isinstance(dp, dict) or dp.get("enabled") is False:
            continue
        dp_id = str(dp.get("id") or "?")
        for field_name in ("target_folder_id", "fallback_folder_id"):
            folder_id = dp.get(field_name)
            if not folder_id:
                continue
            prefix = f"document_profiles[{dp_id}].{field_name}='{folder_id}'"
            destination = folder_destinations.get(str(folder_id))
            if destination is None:
                errors.append(f"{prefix}: existiert nicht in folders.")
                continue
            try:
                resolved = resolve_configured_target_directory(output_root, destination)
                for forbidden in forbidden_roots:
                    if _path_under_forbidden_root(resolved, forbidden):
                        errors.append(
                            f"{prefix}: Zielordner liegt in einem verbotenen Bereich: {resolved}"
                        )
                        break
                else:
                    if _is_unsafe_project_code_path(
                        resolved,
                        project_root_path=project_root_path,
                        output_root=output_root,
                    ):
                        errors.append(
                            f"{prefix}: Zielordner liegt im Anwendungscode-Verzeichnis: {resolved}"
                        )
            except PathSafetyError as exc:
                errors.append(f"{prefix}: {exc}")

    return errors
