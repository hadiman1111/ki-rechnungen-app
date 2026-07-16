"""Path validation for the internal SOMAA launcher."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from invoice_tool.app_paths import profile_storage_dir, project_root, user_support_dir
from invoice_tool.file_lifecycle import path_is_within, validate_input_output_roots
from invoice_tool.source_inventory import discover_source_pdfs

_DEFAULT_ARCHIVE_DIRNAME = "archiv"


@dataclass(frozen=True)
class PathValidationResult:
    ok: bool
    messages: tuple[str, ...]
    resolved_path: Path | None = None
    pdf_count: int = 0


def default_internal_deny_paths() -> tuple[Path, ...]:
    """Local safety denylist for first internal use (not distributed defaults)."""
    parent = project_root().resolve().parent
    return (
        (parent / "output").resolve(),
        project_root().resolve(),
        user_support_dir().resolve(),
    )


def _resolve_existing(path: Path) -> Path | None:
    try:
        return path.expanduser().resolve(strict=False)
    except OSError:
        return None


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def count_source_pdfs(source: Path) -> int:
    """Count top-level PDFs, excluding hidden files and the archive subtree."""
    source = source.resolve()
    if not source.is_dir():
        return 0
    count = 0
    for path in source.iterdir():
        if path.is_dir():
            if path.name == _DEFAULT_ARCHIVE_DIRNAME:
                continue
            continue
        if path.is_file() and path.suffix.lower() == ".pdf" and not _is_hidden(path.name):
            count += 1
    return count


def list_source_pdfs(source: Path) -> list[Path]:
    """Return visible top-level PDFs (same rules as count_source_pdfs)."""
    source = source.resolve()
    if not source.is_dir():
        return []
    pdfs: list[Path] = []
    for path in sorted(source.iterdir()):
        if path.is_dir():
            continue
        if path.is_file() and path.suffix.lower() == ".pdf" and not _is_hidden(path.name):
            pdfs.append(path)
    return pdfs


def _check_symlink_escape(selected: Path, resolved: Path) -> str | None:
    """Detect symlink-based path escapes between selected and resolved paths."""
    if selected == resolved:
        return None
    try:
        selected.relative_to(resolved)
    except ValueError:
        pass
    else:
        return None
    if selected.is_symlink() or any(part.is_symlink() for part in selected.parents if part != selected.anchor):
        return "Der ausgewählte Pfad enthält symbolische Links mit unerwarteter Auflösung."
    return None


def _is_protected_output(path: Path, deny_paths: tuple[Path, ...]) -> str | None:
    resolved = path.resolve()
    repo = project_root().resolve()
    profile_dir = profile_storage_dir().resolve()

    if resolved == repo:
        return "Der Ausgabeordner darf nicht das Programmverzeichnis sein."
    if resolved == profile_dir or path_is_within(resolved, profile_dir):
        return "Der Ausgabeordner darf nicht im Profil-Speicher liegen."
    for denied in deny_paths:
        denied_resolved = denied.resolve()
        if resolved == denied_resolved or path_is_within(resolved, denied_resolved):
            return f"Dieser Ausgabeordner ist aus Sicherheitsgründen gesperrt: {resolved}"
        if path_is_within(denied_resolved, resolved) and denied_resolved != resolved:
            return f"Dieser Ausgabeordner umschließt einen gesperrten Bereich: {resolved}"
    return None


def validate_source_path(
    path: str | Path | None,
    *,
    deny_paths: tuple[Path, ...] | None = None,
) -> PathValidationResult:
    if path is None or not str(path).strip():
        return PathValidationResult(False, ("Bitte einen Eingangsordner auswählen.",))

    selected = Path(str(path).strip()).expanduser()
    resolved = _resolve_existing(selected)
    if resolved is None:
        return PathValidationResult(False, ("Der Eingangsordner konnte nicht aufgelöst werden.",))

    if not resolved.exists():
        return PathValidationResult(False, (f"Der Eingangsordner existiert nicht: {resolved}",))
    if not resolved.is_dir():
        return PathValidationResult(False, (f"Der Eingangsordner ist kein Verzeichnis: {resolved}",))
    if not os.access(resolved, os.R_OK):
        return PathValidationResult(False, (f"Der Eingangsordner ist nicht lesbar: {resolved}",))

    symlink_msg = _check_symlink_escape(selected, resolved)
    if symlink_msg:
        return PathValidationResult(False, (symlink_msg,), resolved_path=resolved)

    pdf_count = count_source_pdfs(resolved)
    if pdf_count < 1:
        return PathValidationResult(
            False,
            ("Im Eingangsordner wurde keine PDF-Datei gefunden (Archiv wird ignoriert).",),
            resolved_path=resolved,
            pdf_count=0,
        )

    return PathValidationResult(True, (), resolved_path=resolved, pdf_count=pdf_count)


def validate_output_path(
    path: str | Path | None,
    *,
    source: Path | None = None,
    deny_paths: tuple[Path, ...] | None = None,
    allow_create: bool = True,
) -> PathValidationResult:
    if path is None or not str(path).strip():
        return PathValidationResult(False, ("Bitte einen Ausgabeordner auswählen.",))

    deny = deny_paths if deny_paths is not None else default_internal_deny_paths()
    selected = Path(str(path).strip()).expanduser()
    resolved = _resolve_existing(selected)
    if resolved is None:
        return PathValidationResult(False, ("Der Ausgabeordner konnte nicht aufgelöst werden.",))

    symlink_msg = _check_symlink_escape(selected, resolved)
    if symlink_msg:
        return PathValidationResult(False, (symlink_msg,), resolved_path=resolved)

    protected = _is_protected_output(resolved, deny)
    if protected:
        return PathValidationResult(False, (protected,), resolved_path=resolved)

    if not resolved.exists():
        if not allow_create:
            return PathValidationResult(False, (f"Der Ausgabeordner existiert nicht: {resolved}",))
        try:
            resolved.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return PathValidationResult(
                False,
                (f"Der Ausgabeordner konnte nicht erstellt werden: {exc}",),
                resolved_path=resolved,
            )

    if not resolved.is_dir():
        return PathValidationResult(False, (f"Der Ausgabeordner ist kein Verzeichnis: {resolved}",))

    if not os.access(resolved, os.W_OK):
        return PathValidationResult(False, (f"Der Ausgabeordner ist nicht beschreibbar: {resolved}",))

    if source is not None:
        try:
            validate_input_output_roots(source.resolve(), resolved)
        except Exception as exc:
            return PathValidationResult(False, (str(exc),), resolved_path=resolved)

    return PathValidationResult(True, (), resolved_path=resolved)


def validate_run_paths(
    source: str | Path | None,
    output: str | Path | None,
    *,
    deny_paths: tuple[Path, ...] | None = None,
) -> tuple[PathValidationResult, PathValidationResult]:
    source_result = validate_source_path(source, deny_paths=deny_paths)
    output_source = source_result.resolved_path if source_result.ok else None
    output_result = validate_output_path(
        output,
        source=output_source,
        deny_paths=deny_paths,
    )
    return source_result, output_result


def run_paths_ready(source_result: PathValidationResult, output_result: PathValidationResult) -> bool:
    return source_result.ok and output_result.ok
