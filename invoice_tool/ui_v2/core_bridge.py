"""Track-B UI-v2 Core Bridge — sandbox dry-run seam (Prompt 3/34).

Validates sandbox-only bridge requests, then calls the safe Core Dry-Run API
``invoice_tool.core_dry_run.run_core_dry_run_sandbox``. Never calls
``invoice_tool.run.run_once``, never enables productive execution, never invents
recognition rows beyond the dry-run result.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

from invoice_tool.ui_v2.core_dry_run_contract import (
    CoreDryRunContractViolation,
    CoreDryRunRequest,
    CoreDryRunResult,
    CoreDryRunStatus,
    build_blocked_core_dry_run_result,
    path_looks_like_original as contract_path_looks_like_original,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingResultSummary,
    ProcessingReviewItem,
    ProcessingRunState,
)

CoreBridgeMode = Literal["sandbox_dry_run", "blocked_contract"]

MSG_BRIDGE_SANDBOX_NOT_CONNECTED = "Sandbox nicht verbunden."
MSG_BRIDGE_DRY_RUN_CONTRACT_REQUIRED = (
    "Echte Verarbeitung benötigt noch eine sichere Dry-Run-Schnittstelle im Core."
)
MSG_BRIDGE_NO_ORIGINALS = "Keine Originalordner wurden verwendet."
MSG_BRIDGE_NO_FILES_PROCESSED = "Keine Dateien wurden verarbeitet."
MSG_BRIDGE_MISSING_INPUT = "Eingangsordner fehlt. Bitte einen Ordner explizit wählen."
MSG_BRIDGE_MISSING_OUTPUT = (
    "Ausgabeordner fehlt. Bitte wähle einen Zielordner, "
    "bevor eine Verarbeitung vorbereitet wird."
)
MSG_BRIDGE_MISSING_CONFIGURATION = (
    "Konfiguration fehlt. Bitte eine Konfiguration explizit wählen."
)
MSG_BRIDGE_MISSING_PROFILE = "Profil fehlt. Bitte ein Profil explizit wählen."
MSG_BRIDGE_MISSING_SANDBOX_ROOT = "Sandbox-Root fehlt. Bitte Sandbox-Pfade setzen."
MSG_BRIDGE_ORIGINAL_LOOKING = (
    "Originalähnlicher Ordner abgelehnt. Nur kopierte Sandbox-Eingänge sind erlaubt."
)
MSG_BRIDGE_PRODUCTIVE_BLOCKED = (
    "Produktive Verarbeitung ist gesperrt. Die Core-Bridge erlaubt keinen Produktivmodus."
)
MSG_BRIDGE_OUTSIDE_SANDBOX = (
    "Pfad liegt außerhalb der Sandbox. Verarbeitung wurde nicht gestartet."
)
MSG_BRIDGE_SAME_INPUT_OUTPUT = (
    "Eingangs- und Ausgabeordner dürfen nicht identisch sein."
)
MSG_BRIDGE_INPUT_NOT_DIR = "Sandbox-Eingang existiert nicht oder ist kein Ordner."
MSG_BRIDGE_OUTPUT_NOT_DIR = "Sandbox-Ausgabe existiert nicht oder ist kein Ordner."
MSG_BRIDGE_SAFETY_PROOF = "Originale unverändert · Produktiv gesperrt · Export Vorschau"
MSG_BRIDGE_COMPLETED = "Sandbox-Lauf abgeschlossen"
MSG_BRIDGE_COMPLETED_WITH_REVIEW = "Sandbox-Lauf mit Prüffällen abgeschlossen"
MSG_BRIDGE_FAILED = "Sandbox-Lauf fehlgeschlagen"

ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED = "core_dry_run_contract_required"
ERROR_MISSING_INPUT = "core_bridge_missing_input"
ERROR_MISSING_OUTPUT = "core_bridge_missing_output"
ERROR_MISSING_CONFIGURATION = "core_bridge_missing_configuration"
ERROR_MISSING_PROFILE = "core_bridge_missing_profile"
ERROR_MISSING_SANDBOX_ROOT = "core_bridge_missing_sandbox_root"
ERROR_ORIGINAL_LOOKING = "core_bridge_original_looking"
ERROR_PRODUCTIVE_BLOCKED = "core_bridge_productive_blocked"
ERROR_OUTSIDE_SANDBOX = "core_bridge_outside_sandbox"
ERROR_SAME_INPUT_OUTPUT = "core_bridge_same_input_output"
ERROR_INPUT_NOT_DIR = "core_bridge_input_not_dir"
ERROR_OUTPUT_NOT_DIR = "core_bridge_output_not_dir"

# Token/segment checks only — no filesystem access for heuristic path screening.
_ORIGINAL_LOOKING_PATH_RE = re.compile(
    r"(?:^|[/\\_\-\s])"
    r"(?:somaa|bismarck|amex|voba|volksbank|american express|test rechnungen|"
    r"programm belegerfassung)"
    r"(?:[/\\_\-\s]|$)",
    re.IGNORECASE,
)
_DESKTOP_ORIGINAL_RE = re.compile(
    r"(?:^|[/\\])(?:Desktop|Documents)[/\\].*(?:Rechnung|Invoice|Beleg)",
    re.IGNORECASE,
)


class CoreBridgeStatus(str, Enum):
    """Bridge outcome markers — success means a real Core Dry-Run was executed."""

    COMPLETED = "completed"
    COMPLETED_WITH_REVIEW = "completed_with_review"
    FAILED = "failed"
    BLOCKED = "blocked"
    REQUIRES_CORE_DRY_RUN_CONTRACT = "requires_core_dry_run_contract"  # legacy sentinel
    BLOCKED_MISSING_INPUT = "blocked_missing_input"
    BLOCKED_MISSING_OUTPUT = "blocked_missing_output"
    BLOCKED_MISSING_CONFIGURATION = "blocked_missing_configuration"
    BLOCKED_MISSING_PROFILE = "blocked_missing_profile"
    BLOCKED_MISSING_SANDBOX_ROOT = "blocked_missing_sandbox_root"
    BLOCKED_ORIGINAL_LOOKING = "blocked_original_looking"
    BLOCKED_PRODUCTIVE = "blocked_productive"
    BLOCKED_OUTSIDE_SANDBOX = "blocked_outside_sandbox"
    BLOCKED_SAME_INPUT_OUTPUT = "blocked_same_input_output"
    BLOCKED_INPUT_NOT_DIR = "blocked_input_not_dir"
    BLOCKED_OUTPUT_NOT_DIR = "blocked_output_not_dir"


@dataclass(frozen=True)
class CoreBridgeRequest:
    """Sandbox-only request accepted by the Track-B core bridge."""

    input_folder: str | None
    output_folder: str | None
    sandbox_root: str | None
    profile_id: str | None
    configuration_id: str | None
    original_source_folder: str | None = None
    dry_run: bool = True
    productive_execution_allowed: bool = False
    mode: CoreBridgeMode = "sandbox_dry_run"
    profile_name: str | None = None
    configuration_name: str | None = None
    run_id: str | None = None
    copied_data_confirmation: bool | None = None
    original_folder_exclusion_confirmation: bool | None = None


@dataclass(frozen=True)
class CoreBridgeResult:
    """Honest bridge outcome — rows only from a real Core Dry-Run result."""

    status: CoreBridgeStatus
    ok: bool
    message: str
    errors: tuple[str, ...] = field(default_factory=tuple)
    planned_moves: tuple[str, ...] = field(default_factory=tuple)
    results: tuple[ProcessingResultSummary, ...] = field(default_factory=tuple)
    review_items: tuple[ProcessingReviewItem, ...] = field(default_factory=tuple)
    run_id: str | None = None
    productive_execution_enabled: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)
    planned_destination_count: int = 0
    safety_proof_summary: str | None = None
    recognized_count: int = 0
    review_count: int = 0
    error_count: int = 0


def _norm(path: str | None) -> str | None:
    value = (path or "").strip()
    if not value:
        return None
    return value.replace("\\", "/").rstrip("/")


def _is_under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def path_looks_like_original(
    path: str | None,
    *,
    original_source_folder: str | None = None,
) -> bool:
    """Heuristic original-folder rejection — string-only, no FS IO."""

    if contract_path_looks_like_original(
        path, original_source_folder=original_source_folder
    ):
        return True
    normalized = _norm(path)
    if normalized is None:
        return False
    original = _norm(original_source_folder)
    if original is not None and (
        normalized == original or _is_under(normalized, original)
    ):
        return True
    probe = f"/{normalized}"
    if _ORIGINAL_LOOKING_PATH_RE.search(probe):
        return True
    if _DESKTOP_ORIGINAL_RE.search(normalized):
        return True
    return False


def _blocked(
    status: CoreBridgeStatus,
    message: str,
    *error_codes: str,
) -> CoreBridgeResult:
    return CoreBridgeResult(
        status=status,
        ok=False,
        message=message,
        errors=tuple(error_codes),
        productive_execution_enabled=False,
        safety_proof_summary=MSG_BRIDGE_SAFETY_PROOF,
    )


def build_core_dry_run_request_from_bridge(
    request: CoreBridgeRequest,
    *,
    input_folder: str,
    output_folder: str,
    sandbox_root: str,
    profile_id: str,
    configuration_id: str,
    copied_data_confirmation: bool,
    original_folder_exclusion_confirmation: bool,
) -> CoreDryRunRequest:
    """Build a contract-compliant CoreDryRunRequest from a validated bridge request."""

    run_id = (request.run_id or "").strip() or f"track-b-dry-{uuid.uuid4().hex[:12]}"
    return CoreDryRunRequest(
        input_dir=input_folder,
        output_dir=output_folder,
        dry_run=True,
        no_mutation=True,
        copied_data_confirmation=copied_data_confirmation,
        original_folder_exclusion_confirmation=original_folder_exclusion_confirmation,
        productive_mode_requested=False,
        profile_id=profile_id,
        profile_name=(request.profile_name or "").strip() or None,
        configuration_id=configuration_id,
        configuration_name=(request.configuration_name or "").strip() or None,
        run_id=run_id,
        sandbox_root=sandbox_root,
        original_source_folder=_norm(request.original_source_folder),
    )


def map_core_dry_run_result_to_bridge_result(
    dry: CoreDryRunResult,
) -> CoreBridgeResult:
    """Map CoreDryRunResult into CoreBridgeResult — never invent document rows."""

    results = tuple(
        ProcessingResultSummary(
            document_name=item.document_name,
            document_type=item.document_type,
            classification_status=item.classification_status,
            status_label=item.status_label,
            confidence_label=item.confidence_label,
            target_hint=item.target_hint,
        )
        for item in dry.recognized
    )
    review_items = tuple(
        ProcessingReviewItem(
            document_name=item.document_name,
            reason=item.reason,
            status_label=item.status_label,
            document_id=item.document_id,
            evidence_summary=item.evidence_summary,
            next_action_hint=item.next_action_hint,
        )
        for item in dry.review
    )
    error_messages = tuple(
        f"{item.error_code}: {item.message}" if item.error_code else item.message
        for item in dry.errors
    )
    if dry.contract_error_codes:
        error_messages = error_messages + tuple(dry.contract_error_codes)
    planned = tuple(item.planned_path for item in dry.planned_destinations)
    summary = dry.summary
    proof = dry.safety_proof
    safety_ok = proof is not None and proof.no_original_mutation and (
        proof.productive_mode_disabled
    )
    safety_summary = MSG_BRIDGE_SAFETY_PROOF if safety_ok or proof is not None else None

    if dry.status == CoreDryRunStatus.BLOCKED:
        status = CoreBridgeStatus.BLOCKED
        ok = False
        message = dry.message or MSG_BRIDGE_FAILED
    elif dry.status == CoreDryRunStatus.FAILED:
        status = CoreBridgeStatus.FAILED
        ok = False
        message = dry.message or MSG_BRIDGE_FAILED
    elif dry.status == CoreDryRunStatus.COMPLETED_WITH_REVIEW:
        status = CoreBridgeStatus.COMPLETED_WITH_REVIEW
        ok = True
        message = dry.message or MSG_BRIDGE_COMPLETED_WITH_REVIEW
    elif dry.status == CoreDryRunStatus.COMPLETED:
        status = CoreBridgeStatus.COMPLETED
        ok = True
        message = dry.message or MSG_BRIDGE_COMPLETED
    else:
        # READY or unexpected — treat as non-success without inventing rows.
        status = CoreBridgeStatus.FAILED
        ok = False
        message = dry.message or MSG_BRIDGE_FAILED

    return CoreBridgeResult(
        status=status,
        ok=ok,
        message=message,
        errors=error_messages,
        planned_moves=planned,
        results=results,
        review_items=review_items,
        run_id=dry.run_id,
        productive_execution_enabled=False,
        warnings=tuple(dry.warnings or ()),
        planned_destination_count=summary.planned_destination_count,
        safety_proof_summary=safety_summary,
        recognized_count=summary.recognized_count,
        review_count=summary.review_count,
        error_count=summary.error_count,
    )


def run_core_bridge_sandbox_dry_run(request: CoreBridgeRequest) -> CoreBridgeResult:
    """Validate sandbox dry-run intent and call the safe Core Dry-Run API.

    Never imports ``invoice_tool.run`` / ``processing`` / routing / classification.
    Never enables productive execution. Never invents result rows.
    """

    if (
        not request.dry_run
        or request.productive_execution_allowed
        or request.mode != "sandbox_dry_run"
    ):
        return _blocked(
            CoreBridgeStatus.BLOCKED_PRODUCTIVE,
            MSG_BRIDGE_PRODUCTIVE_BLOCKED,
            ERROR_PRODUCTIVE_BLOCKED,
        )

    input_folder = _norm(request.input_folder)
    output_folder = _norm(request.output_folder)
    sandbox_root = _norm(request.sandbox_root)
    profile_id = (request.profile_id or "").strip() or None
    configuration_id = (request.configuration_id or "").strip() or None
    profile_name = (request.profile_name or "").strip() or None
    configuration_name = (request.configuration_name or "").strip() or None
    original = _norm(request.original_source_folder)

    if input_folder is None:
        return _blocked(
            CoreBridgeStatus.BLOCKED_MISSING_INPUT,
            MSG_BRIDGE_MISSING_INPUT,
            ERROR_MISSING_INPUT,
        )
    if output_folder is None:
        return _blocked(
            CoreBridgeStatus.BLOCKED_MISSING_OUTPUT,
            MSG_BRIDGE_MISSING_OUTPUT,
            ERROR_MISSING_OUTPUT,
        )
    if sandbox_root is None:
        return _blocked(
            CoreBridgeStatus.BLOCKED_MISSING_SANDBOX_ROOT,
            MSG_BRIDGE_MISSING_SANDBOX_ROOT,
            ERROR_MISSING_SANDBOX_ROOT,
        )
    if profile_id is None and profile_name is None:
        return _blocked(
            CoreBridgeStatus.BLOCKED_MISSING_PROFILE,
            MSG_BRIDGE_MISSING_PROFILE,
            ERROR_MISSING_PROFILE,
        )
    if configuration_id is None and configuration_name is None:
        return _blocked(
            CoreBridgeStatus.BLOCKED_MISSING_CONFIGURATION,
            MSG_BRIDGE_MISSING_CONFIGURATION,
            ERROR_MISSING_CONFIGURATION,
        )

    if input_folder == output_folder:
        return _blocked(
            CoreBridgeStatus.BLOCKED_SAME_INPUT_OUTPUT,
            MSG_BRIDGE_SAME_INPUT_OUTPUT,
            ERROR_SAME_INPUT_OUTPUT,
        )

    if path_looks_like_original(input_folder, original_source_folder=original):
        return _blocked(
            CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING,
            MSG_BRIDGE_ORIGINAL_LOOKING,
            ERROR_ORIGINAL_LOOKING,
        )
    if path_looks_like_original(output_folder, original_source_folder=original):
        return _blocked(
            CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING,
            MSG_BRIDGE_ORIGINAL_LOOKING,
            ERROR_ORIGINAL_LOOKING,
        )

    if not _is_under(input_folder, sandbox_root) or not _is_under(
        output_folder, sandbox_root
    ):
        return _blocked(
            CoreBridgeStatus.BLOCKED_OUTSIDE_SANDBOX,
            MSG_BRIDGE_OUTSIDE_SANDBOX,
            ERROR_OUTSIDE_SANDBOX,
        )

    input_path = Path(input_folder)
    output_path = Path(output_folder)
    if not input_path.is_dir():
        return _blocked(
            CoreBridgeStatus.BLOCKED_INPUT_NOT_DIR,
            MSG_BRIDGE_INPUT_NOT_DIR,
            ERROR_INPUT_NOT_DIR,
        )
    if not output_path.is_dir():
        return _blocked(
            CoreBridgeStatus.BLOCKED_OUTPUT_NOT_DIR,
            MSG_BRIDGE_OUTPUT_NOT_DIR,
            ERROR_OUTPUT_NOT_DIR,
        )

    # Confirmations only when boundary/gate already approved sandbox/copy policy.
    copied_ok = (
        True
        if request.copied_data_confirmation is None
        else bool(request.copied_data_confirmation)
    )
    original_excluded = (
        True
        if request.original_folder_exclusion_confirmation is None
        else bool(request.original_folder_exclusion_confirmation)
    )
    if not copied_ok or not original_excluded:
        return _blocked(
            CoreBridgeStatus.BLOCKED,
            MSG_BRIDGE_ORIGINAL_LOOKING,
            ERROR_ORIGINAL_LOOKING,
        )

    dry_request = build_core_dry_run_request_from_bridge(
        request,
        input_folder=input_folder,
        output_folder=output_folder,
        sandbox_root=sandbox_root,
        profile_id=profile_id or profile_name or "",
        configuration_id=configuration_id or configuration_name or "",
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )

    # Lazy import keeps AST/static coupling to processing-core free; core_dry_run
    # is the additive Prompt-2 module (not run_once / processing / routing).
    from invoice_tool.core_dry_run import (  # noqa: PLC0415
        run_core_dry_run_sandbox,
    )

    try:
        dry_result = run_core_dry_run_sandbox(dry_request)
    except CoreDryRunContractViolation as exc:
        blocked = build_blocked_core_dry_run_result(exc, run_id=dry_request.run_id)
        mapped = map_core_dry_run_result_to_bridge_result(blocked)
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED,
            ok=False,
            message=mapped.message or exc.message,
            errors=mapped.errors or (exc.code,),
            planned_moves=(),
            results=(),
            review_items=(),
            run_id=mapped.run_id,
            productive_execution_enabled=False,
            warnings=mapped.warnings,
            planned_destination_count=0,
            safety_proof_summary=MSG_BRIDGE_SAFETY_PROOF,
            recognized_count=0,
            review_count=0,
            error_count=0,
        )

    return map_core_dry_run_result_to_bridge_result(dry_result)


def map_core_result_to_processing_run_state(
    result: CoreBridgeResult,
    *,
    execution_gate: str | None = "ready_for_sandbox_execution",
    dry_run_gate: str | None = "dry_run_available",
    core_dry_run_status: str | None = "dry_run_available",
) -> ProcessingRunState:
    """Map bridge outcome into ProcessingRunState — never invents rows."""

    if result.status in {
        CoreBridgeStatus.COMPLETED,
        CoreBridgeStatus.COMPLETED_WITH_REVIEW,
    }:
        status = "completed"
    elif result.status == CoreBridgeStatus.FAILED:
        status = "failed"
    elif result.status == CoreBridgeStatus.REQUIRES_CORE_DRY_RUN_CONTRACT:
        status = "failed"
        execution_gate = execution_gate or "unsupported_without_core_change"
        dry_run_gate = "unsupported_without_core_change"
        core_dry_run_status = "unsupported_without_core_change"
    elif result.status in {
        CoreBridgeStatus.BLOCKED_MISSING_INPUT,
        CoreBridgeStatus.BLOCKED_MISSING_OUTPUT,
        CoreBridgeStatus.BLOCKED_MISSING_CONFIGURATION,
        CoreBridgeStatus.BLOCKED_MISSING_PROFILE,
        CoreBridgeStatus.BLOCKED_MISSING_SANDBOX_ROOT,
        CoreBridgeStatus.BLOCKED_INPUT_NOT_DIR,
        CoreBridgeStatus.BLOCKED_OUTPUT_NOT_DIR,
    }:
        status = "not_configured"
    else:
        status = "blocked"

    message = result.message
    if result.safety_proof_summary and result.safety_proof_summary not in message:
        message = f"{message} {result.safety_proof_summary}".strip()

    return ProcessingRunState(
        status=status,  # type: ignore[arg-type]
        message=message,
        run_id=result.run_id,
        results=tuple(result.results),
        review_items=tuple(result.review_items),
        errors=tuple(result.errors),
        execution_gate=execution_gate,  # type: ignore[arg-type]
        dry_run_gate=dry_run_gate,  # type: ignore[arg-type]
        core_dry_run_status=core_dry_run_status,  # type: ignore[arg-type]
        warnings=tuple(result.warnings),
        planned_destination_count=result.planned_destination_count,
        safety_proof_summary=result.safety_proof_summary,
    )


def core_bridge_request_from_sandbox_args(
    *,
    input_folder: str,
    output_folder: str,
    sandbox_root: str,
    profile_id: str,
    configuration_id: str,
    original_source_folder: str | None = None,
    profile_name: str | None = None,
    configuration_name: str | None = None,
    run_id: str | None = None,
) -> CoreBridgeRequest:
    """Build a sandbox dry-run bridge request from boundary args."""

    return CoreBridgeRequest(
        input_folder=input_folder,
        output_folder=output_folder,
        sandbox_root=sandbox_root,
        profile_id=profile_id,
        configuration_id=configuration_id,
        original_source_folder=original_source_folder,
        dry_run=True,
        productive_execution_allowed=False,
        mode="sandbox_dry_run",
        profile_name=profile_name,
        configuration_name=configuration_name,
        run_id=run_id,
        copied_data_confirmation=True,
        original_folder_exclusion_confirmation=True,
    )


__all__ = (
    "CoreBridgeMode",
    "CoreBridgeRequest",
    "CoreBridgeResult",
    "CoreBridgeStatus",
    "ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED",
    "ERROR_INPUT_NOT_DIR",
    "ERROR_MISSING_CONFIGURATION",
    "ERROR_MISSING_INPUT",
    "ERROR_MISSING_OUTPUT",
    "ERROR_MISSING_PROFILE",
    "ERROR_MISSING_SANDBOX_ROOT",
    "ERROR_ORIGINAL_LOOKING",
    "ERROR_OUTSIDE_SANDBOX",
    "ERROR_OUTPUT_NOT_DIR",
    "ERROR_PRODUCTIVE_BLOCKED",
    "ERROR_SAME_INPUT_OUTPUT",
    "MSG_BRIDGE_COMPLETED",
    "MSG_BRIDGE_COMPLETED_WITH_REVIEW",
    "MSG_BRIDGE_DRY_RUN_CONTRACT_REQUIRED",
    "MSG_BRIDGE_FAILED",
    "MSG_BRIDGE_MISSING_CONFIGURATION",
    "MSG_BRIDGE_MISSING_INPUT",
    "MSG_BRIDGE_MISSING_OUTPUT",
    "MSG_BRIDGE_NO_FILES_PROCESSED",
    "MSG_BRIDGE_NO_ORIGINALS",
    "MSG_BRIDGE_ORIGINAL_LOOKING",
    "MSG_BRIDGE_PRODUCTIVE_BLOCKED",
    "MSG_BRIDGE_SAME_INPUT_OUTPUT",
    "MSG_BRIDGE_SANDBOX_NOT_CONNECTED",
    "MSG_BRIDGE_SAFETY_PROOF",
    "build_core_dry_run_request_from_bridge",
    "core_bridge_request_from_sandbox_args",
    "map_core_dry_run_result_to_bridge_result",
    "map_core_result_to_processing_run_state",
    "path_looks_like_original",
    "run_core_bridge_sandbox_dry_run",
)
