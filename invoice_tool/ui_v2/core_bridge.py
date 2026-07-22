"""Track-B UI-v2 Core Bridge — sandbox / dry-run contract seam.

Path B (current): existing processing-core has no safe dry/no-mutation API.
``run_once`` always snapshots, writes outputs, archives source files, and
persists technical run artifacts outside a sandbox root. Track B therefore
must not call processing-core from this bridge.

This module:
- validates sandbox-only bridge requests
- rejects original-looking / productive paths
- returns an explicit REQUIRES_CORE_DRY_RUN_CONTRACT status
- never imports or invokes processing-core
- never invents recognition / review / export rows
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from invoice_tool.ui_v2.processing_state import (
    MSG_DRY_RUN_UNAVAILABLE,
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

ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED = "core_dry_run_contract_required"
ERROR_MISSING_INPUT = "core_bridge_missing_input"
ERROR_MISSING_OUTPUT = "core_bridge_missing_output"
ERROR_MISSING_CONFIGURATION = "core_bridge_missing_configuration"
ERROR_MISSING_PROFILE = "core_bridge_missing_profile"
ERROR_MISSING_SANDBOX_ROOT = "core_bridge_missing_sandbox_root"
ERROR_ORIGINAL_LOOKING = "core_bridge_original_looking"
ERROR_PRODUCTIVE_BLOCKED = "core_bridge_productive_blocked"
ERROR_OUTSIDE_SANDBOX = "core_bridge_outside_sandbox"

# Token/segment checks only — no filesystem access.
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
    """Bridge outcome markers — Path B never reaches a live core call."""

    REQUIRES_CORE_DRY_RUN_CONTRACT = "requires_core_dry_run_contract"
    BLOCKED_MISSING_INPUT = "blocked_missing_input"
    BLOCKED_MISSING_OUTPUT = "blocked_missing_output"
    BLOCKED_MISSING_CONFIGURATION = "blocked_missing_configuration"
    BLOCKED_MISSING_PROFILE = "blocked_missing_profile"
    BLOCKED_MISSING_SANDBOX_ROOT = "blocked_missing_sandbox_root"
    BLOCKED_ORIGINAL_LOOKING = "blocked_original_looking"
    BLOCKED_PRODUCTIVE = "blocked_productive"
    BLOCKED_OUTSIDE_SANDBOX = "blocked_outside_sandbox"


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


@dataclass(frozen=True)
class CoreBridgeResult:
    """Honest bridge outcome — never invents processed document rows."""

    status: CoreBridgeStatus
    ok: bool
    message: str
    errors: tuple[str, ...] = field(default_factory=tuple)
    planned_moves: tuple[str, ...] = field(default_factory=tuple)
    results: tuple[ProcessingResultSummary, ...] = field(default_factory=tuple)
    review_items: tuple[ProcessingReviewItem, ...] = field(default_factory=tuple)
    run_id: str | None = None
    productive_execution_enabled: bool = False


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


def run_core_bridge_sandbox_dry_run(request: CoreBridgeRequest) -> CoreBridgeResult:
    """Validate sandbox dry-run intent and refuse live core execution.

    Never imports ``invoice_tool.run`` / ``processing`` / routing / classification.
    Never enables productive execution. Never invents result rows.
    """

    if (
        not request.dry_run
        or request.productive_execution_allowed
        or request.mode != "sandbox_dry_run"
    ):
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_PRODUCTIVE,
            ok=False,
            message=MSG_BRIDGE_PRODUCTIVE_BLOCKED,
            errors=(ERROR_PRODUCTIVE_BLOCKED,),
            productive_execution_enabled=False,
        )

    input_folder = _norm(request.input_folder)
    output_folder = _norm(request.output_folder)
    sandbox_root = _norm(request.sandbox_root)
    profile_id = (request.profile_id or "").strip() or None
    configuration_id = (request.configuration_id or "").strip() or None
    original = _norm(request.original_source_folder)

    if input_folder is None:
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_MISSING_INPUT,
            ok=False,
            message=MSG_BRIDGE_MISSING_INPUT,
            errors=(ERROR_MISSING_INPUT,),
        )
    if output_folder is None:
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_MISSING_OUTPUT,
            ok=False,
            message=MSG_BRIDGE_MISSING_OUTPUT,
            errors=(ERROR_MISSING_OUTPUT,),
        )
    if sandbox_root is None:
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_MISSING_SANDBOX_ROOT,
            ok=False,
            message=MSG_BRIDGE_MISSING_SANDBOX_ROOT,
            errors=(ERROR_MISSING_SANDBOX_ROOT,),
        )
    if profile_id is None:
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_MISSING_PROFILE,
            ok=False,
            message=MSG_BRIDGE_MISSING_PROFILE,
            errors=(ERROR_MISSING_PROFILE,),
        )
    if configuration_id is None:
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_MISSING_CONFIGURATION,
            ok=False,
            message=MSG_BRIDGE_MISSING_CONFIGURATION,
            errors=(ERROR_MISSING_CONFIGURATION,),
        )

    if path_looks_like_original(input_folder, original_source_folder=original):
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING,
            ok=False,
            message=MSG_BRIDGE_ORIGINAL_LOOKING,
            errors=(ERROR_ORIGINAL_LOOKING,),
        )
    if path_looks_like_original(output_folder, original_source_folder=original):
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_ORIGINAL_LOOKING,
            ok=False,
            message=MSG_BRIDGE_ORIGINAL_LOOKING,
            errors=(ERROR_ORIGINAL_LOOKING,),
        )

    if not _is_under(input_folder, sandbox_root) or not _is_under(
        output_folder, sandbox_root
    ):
        return CoreBridgeResult(
            status=CoreBridgeStatus.BLOCKED_OUTSIDE_SANDBOX,
            ok=False,
            message=MSG_BRIDGE_OUTSIDE_SANDBOX,
            errors=(ERROR_OUTSIDE_SANDBOX,),
        )

    # Path B: safe dry-run core API does not exist — stop before any core call.
    return CoreBridgeResult(
        status=CoreBridgeStatus.REQUIRES_CORE_DRY_RUN_CONTRACT,
        ok=False,
        message=(
            f"{MSG_BRIDGE_SANDBOX_NOT_CONNECTED} "
            f"{MSG_BRIDGE_DRY_RUN_CONTRACT_REQUIRED} "
            f"{MSG_BRIDGE_NO_ORIGINALS} {MSG_BRIDGE_NO_FILES_PROCESSED} "
            f"{MSG_DRY_RUN_UNAVAILABLE}"
        ),
        errors=(ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED,),
        planned_moves=(),
        results=(),
        review_items=(),
        run_id=None,
        productive_execution_enabled=False,
    )


def map_core_result_to_processing_run_state(
    result: CoreBridgeResult,
    *,
    execution_gate: str | None = "unsupported_without_core_change",
    dry_run_gate: str | None = "unsupported_without_core_change",
    core_dry_run_status: str | None = "unsupported_without_core_change",
) -> ProcessingRunState:
    """Map bridge outcome into ProcessingRunState — never invents rows."""

    if result.status == CoreBridgeStatus.REQUIRES_CORE_DRY_RUN_CONTRACT:
        status = "failed"
    elif result.status in {
        CoreBridgeStatus.BLOCKED_MISSING_INPUT,
        CoreBridgeStatus.BLOCKED_MISSING_OUTPUT,
        CoreBridgeStatus.BLOCKED_MISSING_CONFIGURATION,
        CoreBridgeStatus.BLOCKED_MISSING_PROFILE,
        CoreBridgeStatus.BLOCKED_MISSING_SANDBOX_ROOT,
    }:
        status = "not_configured"
    else:
        status = "blocked"

    return ProcessingRunState(
        status=status,  # type: ignore[arg-type]
        message=result.message,
        run_id=result.run_id,
        results=tuple(result.results),
        review_items=tuple(result.review_items),
        errors=tuple(result.errors),
        execution_gate=execution_gate,  # type: ignore[arg-type]
        dry_run_gate=dry_run_gate,  # type: ignore[arg-type]
        core_dry_run_status=core_dry_run_status,  # type: ignore[arg-type]
    )


def core_bridge_request_from_sandbox_args(
    *,
    input_folder: str,
    output_folder: str,
    sandbox_root: str,
    profile_id: str,
    configuration_id: str,
    original_source_folder: str | None = None,
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
    )


__all__ = (
    "CoreBridgeMode",
    "CoreBridgeRequest",
    "CoreBridgeResult",
    "CoreBridgeStatus",
    "ERROR_CORE_DRY_RUN_CONTRACT_REQUIRED",
    "ERROR_MISSING_CONFIGURATION",
    "ERROR_MISSING_INPUT",
    "ERROR_MISSING_OUTPUT",
    "ERROR_MISSING_PROFILE",
    "ERROR_MISSING_SANDBOX_ROOT",
    "ERROR_ORIGINAL_LOOKING",
    "ERROR_OUTSIDE_SANDBOX",
    "ERROR_PRODUCTIVE_BLOCKED",
    "MSG_BRIDGE_DRY_RUN_CONTRACT_REQUIRED",
    "MSG_BRIDGE_MISSING_CONFIGURATION",
    "MSG_BRIDGE_MISSING_INPUT",
    "MSG_BRIDGE_MISSING_OUTPUT",
    "MSG_BRIDGE_NO_FILES_PROCESSED",
    "MSG_BRIDGE_NO_ORIGINALS",
    "MSG_BRIDGE_ORIGINAL_LOOKING",
    "MSG_BRIDGE_PRODUCTIVE_BLOCKED",
    "MSG_BRIDGE_SANDBOX_NOT_CONNECTED",
    "core_bridge_request_from_sandbox_args",
    "map_core_result_to_processing_run_state",
    "path_looks_like_original",
    "run_core_bridge_sandbox_dry_run",
)
