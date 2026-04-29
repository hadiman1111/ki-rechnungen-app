"""Run Manager
============
Provides a command-line interface and programmatic API for running the
invoice processing pipeline with freely chosen source and output paths.

Usage:
    python -m invoice_tool.run \\
        --source  /path/to/pdf/folder \\
        --output  /path/to/output/base \\
        [--config /path/to/invoice_config.json] \\
        [--rules  /path/to/office_rules.json] \\
        [--profile /path/to/profile_config.json]

Design principles:
- Source PDFs are NEVER moved, deleted, or modified. Only read.
- A fresh input_snapshot is created per run by copying (not moving).
- Processing runs exclusively on the snapshot, not on the original source.
- Each run gets its own isolated subdirectory: output/<YYYYMMDD_HHMMSS>/
- runtime/, logs/, and output/ are isolated per run.
- No hard-coded user paths. All paths are supplied by the caller or CLI.
"""
from __future__ import annotations

import argparse
import dataclasses
import shutil
import sys
from datetime import datetime
from pathlib import Path

from invoice_tool.config import ConfigError, load_app_config, load_office_rules
from invoice_tool.extraction import ExtractionCoordinator, OpenAIVisionExtractor, TesseractExtractor
from invoice_tool.models import AppConfig
from invoice_tool.processing import InvoiceProcessor, ProcessorError


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_FILENAME = "invoice_config.json"
_SNAPSHOT_DIRNAME = "input_snapshot"
_OUTPUT_DIRNAME = "output"
_RUNTIME_DIRNAME = "runtime"
_LOGS_DIRNAME = "logs"
_PROFILE_SNAPSHOT_FILENAME = "profile_snapshot.json"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class RunError(RuntimeError):
    """Raised when a run cannot proceed due to an invalid configuration."""


def _validate_source_and_output(source: Path, output: Path) -> None:
    """Raise RunError if source/output combination is unsafe."""
    source = source.resolve()
    output = output.resolve()

    if not source.exists():
        raise RunError(f"source existiert nicht: {source}")
    if not source.is_dir():
        raise RunError(f"source ist kein Ordner: {source}")

    pdf_files = [
        p for p in source.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    ]
    if not pdf_files:
        raise RunError(f"source enthält keine PDF-Dateien: {source}")

    if source == output:
        raise RunError(
            f"source und output dürfen nicht identisch sein: {source}"
        )

    # source must not be inside output
    try:
        source.relative_to(output)
        raise RunError(
            f"source darf nicht innerhalb von output liegen: "
            f"source={source}, output={output}"
        )
    except ValueError:
        pass

    # output must not be inside source
    try:
        output.relative_to(source)
        raise RunError(
            f"output darf nicht innerhalb von source liegen: "
            f"source={source}, output={output}"
        )
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Run directory
# ---------------------------------------------------------------------------

def create_run_dir(output: Path) -> Path:
    """Create a unique timestamped run directory under output.

    Format: YYYYMMDD_HHMMSS; appended with _2, _3, … on collision.

    Args:
        output: Base directory that will contain run subdirectories.

    Returns:
        The newly created run directory (already exists on disk).
    """
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = output / timestamp
    if not candidate.exists():
        candidate.mkdir()
        return candidate

    index = 2
    while True:
        suffixed = output / f"{timestamp}_{index}"
        if not suffixed.exists():
            suffixed.mkdir()
            return suffixed
        index += 1


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

def create_run_snapshot(source: Path, run_dir: Path) -> Path:
    """Copy all PDFs from source into run_dir/input_snapshot/.

    Original files in source are NEVER modified, moved, or deleted.
    Only .pdf and .PDF files are copied; all other files are ignored.

    Args:
        source:  Directory containing the original PDF files.
        run_dir: The isolated run directory for this run.

    Returns:
        Path to the created snapshot directory (run_dir/input_snapshot/).
    """
    source = source.resolve()
    snapshot_dir = run_dir / _SNAPSHOT_DIRNAME
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = [
        p for p in source.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    ]
    for pdf in pdf_files:
        dest = snapshot_dir / pdf.name
        # Guard: never overwrite with a different file if name collides
        if dest.exists():
            stem = pdf.stem
            suffix = pdf.suffix
            counter = 2
            while dest.exists():
                dest = snapshot_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        shutil.copy2(pdf, dest)

    return snapshot_dir


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def build_run_config(
    base_config: AppConfig,
    run_dir: Path,
    snapshot_dir: Path,
) -> AppConfig:
    """Build an AppConfig with all paths isolated to this run.

    Uses dataclasses.replace() so the original base_config is unchanged.

    Path overrides:
        eingangsordner  = snapshot_dir
        ausgangsordner  = run_dir / "output"
        runtime_ordner  = run_dir / "runtime"
        log_ordner      = run_dir / "logs"

    Args:
        base_config:  The AppConfig loaded from invoice_config.json.
        run_dir:      The isolated run directory for this run.
        snapshot_dir: The snapshot directory created by create_run_snapshot.

    Returns:
        A new AppConfig instance with overridden paths.
    """
    return dataclasses.replace(
        base_config,
        eingangsordner=snapshot_dir,
        ausgangsordner=run_dir / _OUTPUT_DIRNAME,
        runtime_ordner=run_dir / _RUNTIME_DIRNAME,
        log_ordner=run_dir / _LOGS_DIRNAME,
    )


# ---------------------------------------------------------------------------
# Core run function
# ---------------------------------------------------------------------------

def run_once(
    source: Path,
    output: Path,
    *,
    config_path: Path | None = None,
    rules_path: Path | None = None,
    profile_path: Path | None = None,
) -> Path:
    """Execute a full processing run with isolated source and output paths.

    Args:
        source:      Directory containing PDF files to process (never modified).
        output:      Base directory for run subdirectories.
        config_path: Path to invoice_config.json. Defaults to
                     ./invoice_config.json relative to CWD.
        rules_path:  Path to an alternative office_rules.json.
                     In this MVP: accepted but raises if provided, because
                     the existing config/loader chain does not yet support
                     an external rules override without touching the config
                     file. Will be implemented in a later step.
        profile_path: Path to profile_config.json.
                     In this MVP: the file is copied to the run dir as
                     profile_snapshot.json but is NOT applied to routing.

    Returns:
        Path to the created run directory.

    Raises:
        RunError:    For invalid source/output combinations or missing files.
        ConfigError: If invoice_config.json cannot be loaded.
    """
    source = source.resolve()
    output = output.resolve()

    # --- validation ---
    _validate_source_and_output(source, output)

    # rules_path: MVP limitation
    if rules_path is not None:
        raise RunError(
            "rules_path ist in diesem MVP noch nicht unterstützt. "
            "Bitte lassen Sie --rules weg; die Regeln werden aus der invoice_config.json geladen."
        )

    # --- config ---
    resolved_config = (
        config_path.resolve() if config_path is not None
        else Path(_DEFAULT_CONFIG_FILENAME).resolve()
    )
    base_config = load_app_config(resolved_config)
    office_rules = load_office_rules(
        base_config.regeln_datei,
        active_preset_override=base_config.aktives_preset,
    )

    # --- create run directory and snapshot ---
    run_dir = create_run_dir(output)
    snapshot_dir = create_run_snapshot(source, run_dir)

    # --- profile snapshot (MVP: copy only, not applied) ---
    if profile_path is not None:
        profile_src = profile_path.resolve()
        if not profile_src.exists():
            raise RunError(f"profile_path existiert nicht: {profile_src}")
        shutil.copy2(profile_src, run_dir / _PROFILE_SNAPSHOT_FILENAME)
        print(
            f"[run] Profil nach {run_dir / _PROFILE_SNAPSHOT_FILENAME} kopiert. "
            "Hinweis: Profil wird in diesem MVP noch nicht auf das Routing angewendet."
        )

    # --- build isolated config ---
    run_config = build_run_config(base_config, run_dir, snapshot_dir)

    # --- extractor ---
    try:
        fallback = TesseractExtractor()
    except Exception:  # noqa: BLE001
        fallback = None

    extractor = ExtractionCoordinator(
        primary=OpenAIVisionExtractor(run_config.api_key_pfad, run_config.openai_model),
        fallback=fallback,
    )

    # --- run ---
    processor = InvoiceProcessor(run_config, extractor, office_rules=office_rules)
    processor.process_all()

    return run_dir


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m invoice_tool.run",
        description=(
            "Run the PDF processing pipeline with freely chosen source and output paths. "
            "Original files in --source are never modified."
        ),
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        metavar="DIR",
        help="Directory containing the PDF files to process (read-only, never modified).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        metavar="DIR",
        help="Base directory for run subdirectories. Created if it does not exist.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        metavar="FILE",
        default=None,
        help=(
            f"Path to invoice_config.json. "
            f"Defaults to ./{_DEFAULT_CONFIG_FILENAME} in the current directory."
        ),
    )
    parser.add_argument(
        "--rules",
        type=Path,
        metavar="FILE",
        default=None,
        help=(
            "Path to an alternative office_rules.json. "
            "NOTE: not supported in this MVP; will raise an error if provided."
        ),
    )
    parser.add_argument(
        "--profile",
        type=Path,
        metavar="FILE",
        default=None,
        help=(
            "Path to profile_config.json. "
            "MVP: file is copied to the run directory as profile_snapshot.json "
            "but is NOT yet applied to routing."
        ),
    )
    return parser


def main() -> int:
    """CLI entry point for ``python -m invoice_tool.run``."""
    parser = _build_parser()
    args = parser.parse_args()

    try:
        run_dir = run_once(
            source=args.source,
            output=args.output,
            config_path=args.config,
            rules_path=args.rules,
            profile_path=args.profile,
        )
        print(f"[run] Lauf abgeschlossen. Run-Ordner: {run_dir}")
        return 0
    except (RunError, ConfigError, ProcessorError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
