"""Lightweight source-folder inventory helpers for the workspace UI."""

from __future__ import annotations

from pathlib import Path

_DEFAULT_ARCHIVE_DIRNAME = "archiv"


def discover_source_pdfs(
    source: Path,
    *,
    archive_dirname: str = _DEFAULT_ARCHIVE_DIRNAME,
) -> list[Path]:
    """Return top-level PDF files from source, excluding the archive subtree."""
    source = source.resolve()
    if not source.is_dir():
        return []
    pdfs: list[Path] = []
    for path in sorted(source.iterdir()):
        if path.is_dir():
            if path.name == archive_dirname:
                continue
            continue
        if path.is_file() and path.suffix.lower() == ".pdf":
            pdfs.append(path)
    return pdfs
