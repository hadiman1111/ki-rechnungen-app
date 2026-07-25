"""Non-mutating input-folder document listing for Track-B workspace live pairs.

Only lists visible document basenames. No recognition, no core runner calls,
no mutation, no productive processing. Archive/technical subfolders are not entered.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LIVE_INPUT_LISTING_MARKER = "workspace_live_input_listing_v1_non_mutating"

# Subfolder names never entered when listing (existing ignore convention).
IGNORED_DIR_NAMES = frozenset(
    {
        "archiv",
        "archive",
        "archives",
        "technisch",
        "technical",
        "__pycache__",
        ".git",
        ".venv",
        "node_modules",
        ".ds_store",
    }
)

DOCUMENT_EXTENSIONS = frozenset({".pdf"})

MSG_FILES_FOUND = "{count} Dateien gefunden"
MSG_NO_FILES_IN_INPUT = "Keine Belege im Eingangsordner gefunden."
MSG_INPUT_FOLDER_UNREADABLE = "Eingangsordner konnte nicht gelesen werden."


@dataclass(frozen=True)
class WorkspaceInputListingResult:
    """Pure listing result — filenames only, never file contents."""

    folder: str | None
    filenames: tuple[str, ...]
    count: int
    empty_message: str | None
    marker: str = LIVE_INPUT_LISTING_MARKER
    mutated: bool = False
    called_run_once: bool = False
    ocr_started: bool = False
    ignored_archive_or_technical: bool = True
    error: str | None = None


def _is_document_file(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in DOCUMENT_EXTENSIONS


def list_workspace_input_documents(
    folder: str | None,
    *,
    limit: int = 200,
) -> WorkspaceInputListingResult:
    """List top-level PDF basenames in the input folder — read-only, non-mutating.

    Does not recurse into archive/technical folders. Does not open PDF content,
    OCR, call run_once, or mutate any file.
    """

    cleaned = (folder or "").strip() or None
    if not cleaned:
        return WorkspaceInputListingResult(
            folder=None,
            filenames=(),
            count=0,
            empty_message=None,
        )
    root = Path(cleaned).expanduser()
    try:
        if not root.is_dir():
            return WorkspaceInputListingResult(
                folder=cleaned,
                filenames=(),
                count=0,
                empty_message=MSG_NO_FILES_IN_INPUT,
                error="not_a_directory",
            )
    except OSError as exc:
        return WorkspaceInputListingResult(
            folder=cleaned,
            filenames=(),
            count=0,
            empty_message=MSG_INPUT_FOLDER_UNREADABLE,
            error=str(exc),
        )

    names: list[str] = []
    try:
        for entry in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
            try:
                if entry.is_dir():
                    # Never enter archive/technical/hidden dirs.
                    if entry.name.casefold() in IGNORED_DIR_NAMES or entry.name.startswith("."):
                        continue
                    continue
                if _is_document_file(entry):
                    names.append(entry.name)
            except OSError:
                continue
            if len(names) >= limit:
                break
    except OSError as exc:
        return WorkspaceInputListingResult(
            folder=cleaned,
            filenames=(),
            count=0,
            empty_message=MSG_INPUT_FOLDER_UNREADABLE,
            error=str(exc),
        )

    filenames = tuple(names)
    if not filenames:
        return WorkspaceInputListingResult(
            folder=cleaned,
            filenames=(),
            count=0,
            empty_message=MSG_NO_FILES_IN_INPUT,
        )
    return WorkspaceInputListingResult(
        folder=cleaned,
        filenames=filenames,
        count=len(filenames),
        empty_message=None,
    )


def refresh_workspace_input_listing_on_state(state: object) -> WorkspaceInputListingResult:
    """Refresh cached input filenames on UI state from the selected folder."""

    folder = str(getattr(state, "workspace_input_folder_override", None) or "").strip() or None
    result = list_workspace_input_documents(folder)
    setattr(state, "workspace_input_filenames", result.filenames)
    setattr(state, "workspace_input_listing_folder", result.folder)
    setattr(state, "workspace_input_listing_count", result.count)
    setattr(state, "workspace_input_listing_empty_message", result.empty_message)
    setattr(state, "workspace_input_listing_marker", result.marker)
    return result


__all__ = (
    "DOCUMENT_EXTENSIONS",
    "IGNORED_DIR_NAMES",
    "LIVE_INPUT_LISTING_MARKER",
    "MSG_FILES_FOUND",
    "MSG_INPUT_FOLDER_UNREADABLE",
    "MSG_NO_FILES_IN_INPUT",
    "WorkspaceInputListingResult",
    "list_workspace_input_documents",
    "refresh_workspace_input_listing_on_state",
)
