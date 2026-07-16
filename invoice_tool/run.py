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
- Source PDFs in the user input folder are NEVER modified in place during processing.
- A fresh input_snapshot is created per run by copying (not moving).
- Processing runs exclusively on the snapshot, not on the original source.
- Final renamed copies are written directly to the user-selected output root.
- Originals are archived to <input>/archiv/<run-id>/ only after verified output success.
- Technical run artifacts live under ~/Library/Application Support/KI-Rechnungen/runs/<run-id>/.
- No hard-coded user paths. All paths are supplied by the caller or CLI.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from invoice_tool.app_paths import create_run_support_dir, project_root, run_support_root
from invoice_tool.config import (
    ConfigError,
    load_app_config,
    load_document_profiles_from_runtime_rules,
    load_folder_destinations_from_runtime_rules,
    load_office_rules,
    load_office_rules_from_dict,
    merge_rules_dicts,
)
from invoice_tool.extraction import ExtractionCoordinator, OpenAIVisionExtractor, TesseractExtractor
from invoice_tool.folder_destination import validate_runtime_destinations_preflight
from invoice_tool.models import AppConfig, OfficeRules, ProcessingPreset
from invoice_tool.file_lifecycle import (
    MAPPING_FILENAME,
    OutputMappingStore,
    validate_input_output_roots,
)
from invoice_tool.processing import InvoiceProcessor, ProcessorError
from invoice_tool.target_routing import (
    load_target_routing_config,
    profile_uses_cfg001_runtime_routing,
    validate_target_routing_config,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_FILENAME = "invoice_config.json"
_SNAPSHOT_DIRNAME = "input_snapshot"
_RUNTIME_DIRNAME = "runtime"
_LOGS_DIRNAME = "logs"
_PROFILE_SNAPSHOT_FILENAME = "profile_snapshot.json"
_RUNTIME_RULES_FILENAME = "runtime_rules.json"
_OUTPUT_MAPPING_FILENAME = "output_mapping.json"
_DEFAULT_ARCHIVE_DIRNAME = "archiv"
_DEFAULT_DOCUMENTS_SUBDIR = "documents"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class RunError(RuntimeError):
    """Raised when a run cannot proceed due to an invalid configuration."""


from invoice_tool.source_inventory import discover_source_pdfs


def _validate_source_and_output(source: Path, output: Path) -> None:
    """Raise RunError if source/output combination is unsafe."""
    source = source.resolve()
    output = output.resolve()

    if not source.exists():
        raise RunError(f"source existiert nicht: {source}")
    if not source.is_dir():
        raise RunError(f"source ist kein Ordner: {source}")

    pdf_files = discover_source_pdfs(source)
    if not pdf_files:
        raise RunError(f"source enthält keine PDF-Dateien: {source}")

    try:
        validate_input_output_roots(source, output)
    except Exception as exc:
        raise RunError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Run directory (legacy helper kept for tests)
# ---------------------------------------------------------------------------

def create_run_dir(output: Path) -> Path:
    """Create a unique timestamped run directory under output.

    Legacy helper retained for unit tests. Production runs use Application Support
    via create_run_support_dir().
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

def create_run_snapshot(
    source: Path,
    run_dir: Path,
    pdf_files: list[Path] | None = None,
) -> tuple[Path, dict[Path, Path]]:
    """Copy selected PDFs from source into run_dir/input_snapshot/.

    Original files in source are NEVER modified, moved, or deleted.
    Only .pdf and .PDF files are copied; all other files are ignored.

    Returns:
        (snapshot_dir, snapshot_to_original) mapping snapshot paths to originals.
    """
    source = source.resolve()
    snapshot_dir = run_dir / _SNAPSHOT_DIRNAME
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    selected = pdf_files if pdf_files is not None else discover_source_pdfs(source)
    snapshot_to_original: dict[Path, Path] = {}

    for pdf in selected:
        dest = snapshot_dir / pdf.name
        if dest.exists():
            stem = pdf.stem
            suffix = pdf.suffix
            counter = 2
            while dest.exists():
                dest = snapshot_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        shutil.copy2(pdf, dest)
        snapshot_to_original[dest.resolve()] = pdf.resolve()

    return snapshot_dir, snapshot_to_original


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def build_run_config(
    base_config: AppConfig,
    run_dir: Path,
    snapshot_dir: Path,
    user_output_root: Path,
) -> AppConfig:
    """Build an AppConfig with run-scoped technical paths and user output root.

    Path overrides:
        eingangsordner  = snapshot_dir
        ausgangsordner  = user_output_root
        runtime_ordner  = run_dir / "runtime"
        log_ordner      = run_dir / "logs"
    """
    return dataclasses.replace(
        base_config,
        eingangsordner=snapshot_dir,
        ausgangsordner=user_output_root.resolve(),
        runtime_ordner=run_dir / _RUNTIME_DIRNAME,
        log_ordner=run_dir / _LOGS_DIRNAME,
    )


def _with_documents_basis(office_rules: OfficeRules, basis_path: Path) -> OfficeRules:
    preset = office_rules.preset
    new_dokumente = dataclasses.replace(preset.dokumente, basis_pfad=basis_path.resolve())
    new_preset: ProcessingPreset = dataclasses.replace(preset, dokumente=new_dokumente)
    new_presets = dict(office_rules.presets)
    new_presets[office_rules.active_preset] = new_preset
    return dataclasses.replace(office_rules, presets=new_presets)


def _write_output_mapping(
    run_dir: Path,
    *,
    run_id: str,
    mappings: list[dict[str, str | None]],
) -> Path:
    mapping_path = run_dir / _OUTPUT_MAPPING_FILENAME
    payload = {
        "run_id": run_id,
        "mappings": mappings,
    }
    mapping_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return mapping_path


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

    Returns:
        Path to the technical run directory under Application Support.

    Raises:
        RunError:    For invalid source/output combinations or missing files.
        ConfigError: If invoice_config.json cannot be loaded.
    """
    source = source.resolve()
    output = output.resolve()

    _validate_source_and_output(source, output)

    if rules_path is not None:
        raise RunError(
            "rules_path ist in diesem MVP noch nicht unterstützt. "
            "Bitte lassen Sie --rules weg; die Regeln werden aus der invoice_config.json geladen."
        )

    resolved_config = (
        config_path.resolve() if config_path is not None
        else Path(_DEFAULT_CONFIG_FILENAME).resolve()
    )
    base_config = load_app_config(resolved_config)

    try:
        base_rules_dict = json.loads(base_config.regeln_datei.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RunError(f"Regeldatei konnte nicht gelesen werden: {exc}") from exc

    base_rules_dir = base_config.regeln_datei.parent.resolve()
    active_preset = base_config.aktives_preset or "office_default"

    run_dir, run_id = create_run_support_dir()
    (run_dir / _RUNTIME_DIRNAME).mkdir(parents=True, exist_ok=True)
    (run_dir / _LOGS_DIRNAME).mkdir(parents=True, exist_ok=True)

    active_profile_id: str | None = None
    profile_data: dict | None = None

    if profile_path is not None:
        profile_src = profile_path.resolve()
        if not profile_src.exists():
            raise RunError(f"profile_path existiert nicht: {profile_src}")

        try:
            profile_data = json.loads(profile_src.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RunError(f"profile_path ist kein gueltiges JSON: {exc}") from exc

        if not isinstance(profile_data, dict):
            raise RunError("profile_path muss ein JSON-Objekt sein.")

        preflight_errors = validate_runtime_destinations_preflight(
            profile_data,
            output_root=output,
            source_root=source,
            run_support_root=run_support_root(),
            project_root_path=project_root(),
        )
        if profile_uses_cfg001_runtime_routing(profile_data):
            preflight_errors.extend(
                validate_target_routing_config(load_target_routing_config(profile_data))
            )
        if preflight_errors:
            raise RunError(
                "Profil-Zielordner sind ungültig; Verarbeitung wurde nicht gestartet: "
                + "; ".join(preflight_errors)
            )

        active_profile_id = profile_src.stem if profile_src.parent.name == "profiles" else "local"

    source_pdfs = discover_source_pdfs(source)
    snapshot_dir, snapshot_to_original = create_run_snapshot(source, run_dir, source_pdfs)

    if profile_path is not None:
        profile_src = profile_path.resolve()
        shutil.copy2(profile_src, run_dir / _PROFILE_SNAPSHOT_FILENAME)

        from invoice_tool.profile_compiler import compile_profile_to_rules  # noqa: PLC0415
        generated = compile_profile_to_rules(profile_data, preset_name=active_preset)
        merged_dict = merge_rules_dicts(base_rules_dict, generated)

        gen_preset = generated.get("presets", {}).get(active_preset, {})
        gen_routing = gen_preset.get("routing", {})
        generated_sections = [
            f"routing.{section}"
            for section in (
                "strassen", "prioritaetsregeln", "konten",
                "business_context_rules", "payment_detection_rules",
            )
            if section in gen_routing
        ]
        if "classification" in gen_preset:
            generated_sections.append("classification")
        if "dateiname_schema" in gen_preset:
            generated_sections.append("dateiname_schema")
        if "routing_overrides" in gen_preset:
            generated_sections.append("routing_overrides")

        prepended_sections = [
            f"routing.{section}"
            for section in ("payment_detection_rules",)
            if section in gen_routing
        ]

        all_protected = [
            "routing.konten",
            "routing.business_context_rules",
            "routing.final_assignment_rules",
            "routing.output_route_rules",
            "classification",
            "supplier_cleaning",
            "dateiname_schema",
            "invoice_fallbacks",
        ]
        protected_sections = [s for s in all_protected if s not in generated_sections]

        merged_dict["_meta"] = {
            "profile_applied": True,
            "base_rules_source": str(base_config.regeln_datei),
            "profile_source": str(profile_src),
            "generated_sections": generated_sections,
            "prepended_sections": prepended_sections,
            "protected_sections": protected_sections,
            "merge_strategy": "replace_generated_sections_prepend_payment_detection",
        }

        if "document_profiles" in generated:
            merged_dict["document_profiles"] = generated["document_profiles"]

        doc_profile_warnings = generated.get("_meta", {}).get(
            "document_profiles_warnings", []
        )
        if doc_profile_warnings:
            merged_dict.setdefault("_meta", {})
            merged_dict["_meta"]["document_profiles_warnings"] = doc_profile_warnings

        runtime_rules_path = run_dir / _RUNTIME_RULES_FILENAME
        runtime_rules_path.write_text(
            json.dumps(merged_dict, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[run] Runtime-Regeln geschrieben: {runtime_rules_path}")

        office_rules = load_office_rules_from_dict(
            merged_dict,
            base_rules_dir,
            active_preset_override=active_preset,
        )
        document_profiles = load_document_profiles_from_runtime_rules(merged_dict)
        folder_destinations = load_folder_destinations_from_runtime_rules(merged_dict)
        if document_profiles:
            print(f"[run] {len(document_profiles)} document_profile(s) geladen.")
        if folder_destinations:
            print(f"[run] {len(folder_destinations)} Zielordner-Destination(s) geladen.")
    else:
        office_rules = load_office_rules(
            base_config.regeln_datei,
            active_preset_override=base_config.aktives_preset,
        )
        document_profiles = []
        folder_destinations = {}

    documents_basis = output / _DEFAULT_DOCUMENTS_SUBDIR
    documents_basis.mkdir(parents=True, exist_ok=True)
    office_rules = _with_documents_basis(office_rules, documents_basis)

    run_config = build_run_config(base_config, run_dir, snapshot_dir, output)

    try:
        fallback = TesseractExtractor()
    except Exception:  # noqa: BLE001
        fallback = None

    extractor = ExtractionCoordinator(
        primary=OpenAIVisionExtractor(run_config.api_key_pfad, run_config.openai_model),
        fallback=fallback,
    )

    mapping_store = OutputMappingStore(run_dir, run_id)
    processor = InvoiceProcessor(
        run_config,
        extractor,
        office_rules=office_rules,
        document_profiles=document_profiles if document_profiles else None,
        folder_destinations=folder_destinations or None,
        original_source_dir=source,
        snapshot_to_original=snapshot_to_original,
        technical_run_dir=run_dir,
        mapping_store=mapping_store,
        active_profile_id=active_profile_id,
        profile_data=profile_data,
        target_routing_config=(
            load_target_routing_config(profile_data)
            if profile_data is not None
            and profile_uses_cfg001_runtime_routing(profile_data)
            else None
        ),
    )
    results = processor.process_all()
    mapping_path = mapping_store.flush()
    print(f"[run] Output-Mapping geschrieben: {mapping_path}")

    return run_dir


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m invoice_tool.run",
        description=(
            "Run the PDF processing pipeline with freely chosen source and output paths. "
            "Original files in --source are never modified in place."
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
        help="User output root for final renamed copies.",
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
        help="Path to profile_config.json.",
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
            profile_path=args.profile,
        )
        print(f"[run] Lauf abgeschlossen. Technischer Run-Ordner: {run_dir}")
        return 0
    except (RunError, ConfigError, ProcessorError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
