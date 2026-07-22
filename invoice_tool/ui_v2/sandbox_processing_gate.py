"""Track-B UI-v2 sandbox processing run gate.

Pure path/contract validation for a future sandbox-only processing call.
String-only checks — no filesystem writes, no folder creation, no folder scan,
no PDF processing, no processing-core import, no Track-A import.

Productive execution remains blocked. Original invoice folders must never be
accepted as processing input.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from invoice_tool.ui_v2.clarity_copy import (
    MSG_CLARITY_NO_ORIGINAL_FOLDERS,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
    MSG_CLARITY_SANDBOX_COPIED_DATA_ONLY,
    MSG_CLARITY_SANDBOX_COPIED_RUN,
)
from invoice_tool.ui_v2.processing_contract import (
    SOURCE_EXPLICIT_USER_SELECTION,
    SOURCE_UNSET,
    ProcessingRunRequest,
)

SandboxProcessingMode = Literal["disabled", "sandbox", "productive"]
SandboxReasonCode = Literal[
    "blocked_missing_sandbox",
    "blocked_missing_sandbox_root",
    "blocked_missing_input",
    "blocked_missing_output",
    "blocked_missing_copied_data_confirmation",
    "blocked_missing_user_confirmation",
    "blocked_missing_original_source",
    "blocked_original_folder",
    "blocked_same_input_output",
    "blocked_output_inside_original",
    "blocked_input_outside_sandbox",
    "blocked_output_outside_sandbox",
    "blocked_productive_execution",
    "blocked_missing_policy_intent",
    "blocked_missing_profile",
    "blocked_missing_configuration",
    "blocked_missing_explicit_source",
    "ready_for_sandbox_execution",
]
ExecutionScope = Literal["blocked", "sandbox", "dry_run", "productive"]

MSG_SANDBOX_MODE_PREPARED = "Sandbox-Modus: vorbereitet"
MSG_SANDBOX_COPIED_RUN = MSG_CLARITY_SANDBOX_COPIED_RUN
MSG_SANDBOX_COPIED_DATA_ONLY = MSG_CLARITY_SANDBOX_COPIED_DATA_ONLY
MSG_SANDBOX_NO_ORIGINAL_INPUT = MSG_CLARITY_NO_ORIGINAL_FOLDERS
MSG_SANDBOX_PRODUCTIVE_BLOCKED = MSG_CLARITY_PRODUCTIVE_NOT_RELEASED
MSG_SANDBOX_CORE_DRY_ABSENT = "Core-Dry-Run ist noch nicht vorhanden."
MSG_SANDBOX_CORE_DRY_WIRED = (
    "Sicherer Core-Dry-Run ist angebunden (Sandbox, keine Originalmutation)."
)
MSG_SANDBOX_EXECUTION_WIRED = (
    "Sandbox-Ausführung nur nach Gate-Freigabe gegen kopierte Testdaten."
)
MSG_SANDBOX_READY_PENDING_WIRING = (
    "Sandbox-Gate freigegeben; Sandbox-Ausführung gegen kopierte Testdaten "
    f"ist freigegeben. {MSG_SANDBOX_CORE_DRY_WIRED}"
)
MSG_BLOCKED_MISSING_SANDBOX = (
    "Sandbox-Modus fehlt. Verarbeitung ist nur im expliziten Sandbox-Modus "
    "mit kopierten Testdaten vorbereitbar."
)
MSG_BLOCKED_MISSING_SANDBOX_ROOT = (
    "Sandbox-Wurzel fehlt. Eingangs- und Ausgabeordner müssen unter einer "
    "expliziten Sandbox-Wurzel liegen."
)
MSG_BLOCKED_MISSING_COPIED_DATA = (
    "Bestätigung für kopierte Testdaten fehlt. "
    "Originalordner dürfen nicht verarbeitet werden."
)
MSG_BLOCKED_ORIGINAL_AS_INPUT = (
    "Original-Quellordner darf nicht als Verarbeitungseingang verwendet werden."
)
MSG_BLOCKED_SAME_INPUT_OUTPUT = (
    "Eingangs- und Ausgabeordner dürfen nicht identisch sein."
)
MSG_BLOCKED_OUTPUT_INSIDE_ORIGINAL = (
    "Ausgabeordner darf nicht innerhalb des Original-Quellordners liegen."
)
MSG_BLOCKED_OUTSIDE_SANDBOX = (
    "Ordner liegt außerhalb der expliziten Sandbox-Wurzel."
)
MSG_BLOCKED_PRODUCTIVE = MSG_SANDBOX_PRODUCTIVE_BLOCKED
MSG_BLOCKED_MISSING_ORIGINAL_SOURCE = (
    "Original-Quellordner fehlt. Ohne expliziten Originalpfad kann der "
    "Ausschluss vom Sandbox-Eingang nicht geprüft werden."
)

WORKSPACE_SANDBOX_READINESS_LINES = (
    MSG_SANDBOX_COPIED_RUN,
    MSG_SANDBOX_MODE_PREPARED,
    MSG_SANDBOX_COPIED_DATA_ONLY,
    MSG_SANDBOX_NO_ORIGINAL_INPUT,
    MSG_SANDBOX_PRODUCTIVE_BLOCKED,
    MSG_SANDBOX_EXECUTION_WIRED,
    MSG_SANDBOX_CORE_DRY_WIRED,
)


def _normalize_path_key(path: str | None) -> str | None:
    """Normalize a path string for comparison — no filesystem access."""

    if path is None:
        return None
    value = path.strip()
    if not value:
        return None
    # os.path.normpath does not require the path to exist.
    normalized = os.path.normpath(value.replace("\\", "/"))
    return normalized or None


def _paths_equal(left: str | None, right: str | None) -> bool:
    a = _normalize_path_key(left)
    b = _normalize_path_key(right)
    if a is None or b is None:
        return False
    return a == b


def _is_under(child: str | None, parent: str | None) -> bool:
    """True when child equals parent or is nested under parent (string-only)."""

    c = _normalize_path_key(child)
    p = _normalize_path_key(parent)
    if c is None or p is None:
        return False
    if c == p:
        return True
    prefix = p.rstrip("/") + "/"
    return c.startswith(prefix)


@dataclass(frozen=True)
class SandboxPathValidationResult:
    """Outcome of pure sandbox path/contract validation."""

    approved: bool
    reason_code: SandboxReasonCode
    message: str
    sandbox_root: str | None = None
    input_folder: str | None = None
    output_folder: str | None = None
    original_source_folder: str | None = None
    execution_scope: ExecutionScope = "blocked"
    creates_folders: bool = False
    scans_folders: bool = False
    processes_pdfs: bool = False


@dataclass(frozen=True)
class SandboxProcessingGate:
    """Explicit sandbox gate inputs (defaults are safe / blocked)."""

    mode: SandboxProcessingMode = "disabled"
    sandbox_root: str | None = None
    input_folder: str | None = None
    output_folder: str | None = None
    original_source_folder: str | None = None
    copied_data_confirmed: bool = False
    user_confirmed_start: bool = False
    productive_execution_allowed: bool = False
    dry_run: bool = True
    profile_id: str | None = None
    configuration_id: str | None = None
    has_policy_intent: bool = False
    has_explicit_user_source: bool = False

    @property
    def sandbox_mode_enabled(self) -> bool:
        return self.mode == "sandbox"


def validate_sandbox_paths(
    gate: SandboxProcessingGate,
) -> SandboxPathValidationResult:
    """Validate sandbox confinement rules without FS IO or PDF processing."""

    input_folder = _normalize_path_key(gate.input_folder)
    output_folder = _normalize_path_key(gate.output_folder)
    sandbox_root = _normalize_path_key(gate.sandbox_root)
    original = _normalize_path_key(gate.original_source_folder)

    base_kwargs = dict(
        sandbox_root=sandbox_root,
        input_folder=input_folder,
        output_folder=output_folder,
        original_source_folder=original,
        creates_folders=False,
        scans_folders=False,
        processes_pdfs=False,
    )

    if gate.productive_execution_allowed or gate.mode == "productive" or not gate.dry_run:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_productive_execution",
            message=MSG_BLOCKED_PRODUCTIVE,
            execution_scope="productive" if not gate.dry_run else "blocked",
            **base_kwargs,
        )

    if not gate.sandbox_mode_enabled:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_sandbox",
            message=MSG_BLOCKED_MISSING_SANDBOX,
            **base_kwargs,
        )

    if sandbox_root is None:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_sandbox_root",
            message=MSG_BLOCKED_MISSING_SANDBOX_ROOT,
            **base_kwargs,
        )

    if not gate.has_explicit_user_source:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_explicit_source",
            message="Keine explizite Benutzerauswahl als Quelle gesetzt.",
            **base_kwargs,
        )

    if input_folder is None:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_input",
            message="Eingangsordner fehlt. Bitte einen Sandbox-Eingangsordner explizit wählen.",
            **base_kwargs,
        )

    if output_folder is None:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_output",
            message="Ausgabeordner fehlt. Bitte einen Sandbox-Ausgabeordner explizit wählen.",
            **base_kwargs,
        )

    if not gate.copied_data_confirmed:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_copied_data_confirmation",
            message=MSG_BLOCKED_MISSING_COPIED_DATA,
            **base_kwargs,
        )

    if not gate.user_confirmed_start:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_user_confirmation",
            message=(
                "Explizite Benutzerbestätigung fehlt. "
                "Sandbox-Verarbeitung startet nur nach CTA-Bestätigung."
            ),
            **base_kwargs,
        )

    # Original path is an optional exclusion marker. Copied-data confirmation
    # is already required above; without a declared original we still refuse
    # productive/original mutation via other gates, but do not no-op the CTA.
    if original is not None and (
        _paths_equal(input_folder, original) or _is_under(input_folder, original)
    ):
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_original_folder",
            message=MSG_BLOCKED_ORIGINAL_AS_INPUT,
            **base_kwargs,
        )

    if _paths_equal(input_folder, output_folder):
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_same_input_output",
            message=MSG_BLOCKED_SAME_INPUT_OUTPUT,
            **base_kwargs,
        )

    if original is not None and _is_under(output_folder, original):
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_output_inside_original",
            message=MSG_BLOCKED_OUTPUT_INSIDE_ORIGINAL,
            **base_kwargs,
        )

    if not _is_under(input_folder, sandbox_root):
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_input_outside_sandbox",
            message=f"{MSG_BLOCKED_OUTSIDE_SANDBOX} (Eingang).",
            **base_kwargs,
        )

    if not _is_under(output_folder, sandbox_root):
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_output_outside_sandbox",
            message=f"{MSG_BLOCKED_OUTSIDE_SANDBOX} (Ausgabe).",
            **base_kwargs,
        )

    if not (gate.profile_id or "").strip():
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_profile",
            message="Profil fehlt. Bitte ein Profil explizit wählen.",
            **base_kwargs,
        )

    if not (gate.configuration_id or "").strip():
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_configuration",
            message="Konfiguration fehlt. Bitte eine Konfiguration explizit wählen.",
            **base_kwargs,
        )

    if not gate.has_policy_intent:
        return SandboxPathValidationResult(
            approved=False,
            reason_code="blocked_missing_policy_intent",
            message="Verarbeitungsregeln / Policy-Intent fehlen für den Sandbox-Lauf.",
            **base_kwargs,
        )

    return SandboxPathValidationResult(
        approved=True,
        reason_code="ready_for_sandbox_execution",
        message=MSG_SANDBOX_READY_PENDING_WIRING,
        execution_scope="sandbox",
        **base_kwargs,
    )


def sandbox_gate_from_request(request: ProcessingRunRequest) -> SandboxProcessingGate:
    """Map a ProcessingRunRequest onto SandboxProcessingGate (pure, no FS)."""

    mode: SandboxProcessingMode = "disabled"
    if request.sandbox_mode:
        mode = "sandbox"
    if request.productive_execution_allowed or request.execution_scope == "productive":
        mode = "productive"

    policy = request.effective_policy_bridge_result()
    has_policy = (
        request.policy_intent is not None
        or (policy is not None and policy.status == "ready" and policy.intent is not None)
    )
    return SandboxProcessingGate(
        mode=mode,
        sandbox_root=request.normalized_sandbox_root(),
        input_folder=request.normalized_input_folder(),
        output_folder=request.normalized_output_folder(),
        original_source_folder=request.normalized_original_source_folder(),
        copied_data_confirmed=bool(request.copied_data_confirmed),
        user_confirmed_start=bool(request.user_confirmed_start),
        productive_execution_allowed=bool(request.productive_execution_allowed),
        dry_run=bool(request.dry_run),
        profile_id=request.normalized_profile_id(),
        configuration_id=request.normalized_configuration_id(),
        has_policy_intent=has_policy,
        has_explicit_user_source=request.has_explicit_user_source(),
    )


def evaluate_sandbox_gate(request: ProcessingRunRequest) -> SandboxPathValidationResult:
    """Validate sandbox rules for a processing request — no core call."""

    return validate_sandbox_paths(sandbox_gate_from_request(request))


def build_sandbox_run_request(
    *,
    sandbox_root: str,
    input_folder: str,
    output_folder: str,
    original_source_folder: str,
    profile_id: str,
    configuration_id: str,
    copied_data_confirmed: bool = True,
    user_confirmed_start: bool = True,
    dry_run: bool = True,
    policy_intent=None,
    policy_bridge_result=None,
) -> ProcessingRunRequest:
    """Build an explicit sandbox-scoped request (defaults stay non-productive)."""

    return ProcessingRunRequest(
        input_folder=input_folder,
        output_folder=output_folder,
        profile_id=profile_id,
        configuration_id=configuration_id,
        dry_run=dry_run,
        source=SOURCE_EXPLICIT_USER_SELECTION,
        policy_intent=policy_intent,
        policy_bridge_result=policy_bridge_result,
        user_confirmed_start=user_confirmed_start,
        sandbox_mode=True,
        sandbox_root=sandbox_root,
        original_source_folder=original_source_folder,
        copied_data_confirmed=copied_data_confirmed,
        productive_execution_allowed=False,
        execution_scope="sandbox" if dry_run else "blocked",
    )


def workspace_sandbox_readiness_copy() -> tuple[str, ...]:
    """Honest workspace sandbox readiness lines — no private/default paths."""

    return WORKSPACE_SANDBOX_READINESS_LINES


# Re-export for callers that need the unset sentinel without importing contract.
__all__ = (
    "ExecutionScope",
    "MSG_BLOCKED_MISSING_COPIED_DATA",
    "MSG_BLOCKED_MISSING_SANDBOX",
    "MSG_BLOCKED_MISSING_SANDBOX_ROOT",
    "MSG_BLOCKED_ORIGINAL_AS_INPUT",
    "MSG_BLOCKED_OUTPUT_INSIDE_ORIGINAL",
    "MSG_BLOCKED_PRODUCTIVE",
    "MSG_BLOCKED_SAME_INPUT_OUTPUT",
    "MSG_SANDBOX_COPIED_DATA_ONLY",
    "MSG_SANDBOX_COPIED_RUN",
    "MSG_SANDBOX_CORE_DRY_ABSENT",
    "MSG_SANDBOX_CORE_DRY_WIRED",
    "MSG_SANDBOX_EXECUTION_WIRED",
    "MSG_SANDBOX_MODE_PREPARED",
    "MSG_SANDBOX_NO_ORIGINAL_INPUT",
    "MSG_SANDBOX_PRODUCTIVE_BLOCKED",
    "MSG_SANDBOX_READY_PENDING_WIRING",
    "SOURCE_UNSET",
    "SandboxPathValidationResult",
    "SandboxProcessingGate",
    "SandboxProcessingMode",
    "SandboxReasonCode",
    "WORKSPACE_SANDBOX_READINESS_LINES",
    "build_sandbox_run_request",
    "evaluate_sandbox_gate",
    "sandbox_gate_from_request",
    "validate_sandbox_paths",
    "workspace_sandbox_readiness_copy",
)
