"""Track-B Core Dry-Run Sandbox API contract (types + validation only).

Prompt 1/34 — defines the safe no-mutation API surface that Prompt 2/34 must
implement in processing-core. This module:

- defines request / result / safety types
- validates dry-run / no-mutation / sandbox preconditions
- never imports processing-core
- never processes PDFs, never mutates folders, never calls OCR/AI
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Modes / status
# ---------------------------------------------------------------------------


class CoreDryRunMode(str, Enum):
    """Only sandbox dry-run is in scope for Track B."""

    SANDBOX_DRY_RUN = "sandbox_dry_run"


class CoreDryRunStatus(str, Enum):
    """Lifecycle statuses returned by the Core Dry-Run API."""

    BLOCKED = "blocked"
    READY = "ready"
    COMPLETED = "completed"
    COMPLETED_WITH_REVIEW = "completed_with_review"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Errors / messages
# ---------------------------------------------------------------------------


class CoreDryRunContractViolation(ValueError):
    """Raised when a request violates the Core Dry-Run Sandbox contract."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


ERROR_MISSING_INPUT = "core_dry_run_missing_input"
ERROR_MISSING_OUTPUT = "core_dry_run_missing_output"
ERROR_SAME_INPUT_OUTPUT = "core_dry_run_same_input_output"
ERROR_DRY_RUN_REQUIRED = "core_dry_run_dry_run_required"
ERROR_NO_MUTATION_REQUIRED = "core_dry_run_no_mutation_required"
ERROR_PRODUCTIVE_BLOCKED = "core_dry_run_productive_blocked"
ERROR_COPIED_DATA_CONFIRMATION = "core_dry_run_copied_data_confirmation_required"
ERROR_ORIGINAL_EXCLUSION_CONFIRMATION = (
    "core_dry_run_original_folder_exclusion_confirmation_required"
)
ERROR_MISSING_PROFILE = "core_dry_run_missing_profile"
ERROR_MISSING_CONFIGURATION = "core_dry_run_missing_configuration"
ERROR_ORIGINAL_LOOKING = "core_dry_run_original_looking_path"
ERROR_OUTSIDE_SANDBOX = "core_dry_run_outside_sandbox"
ERROR_SAFETY_FLAG = "core_dry_run_safety_flag_violation"
ERROR_MODE = "core_dry_run_mode_invalid"

MSG_MISSING_INPUT = "Eingangsordner fehlt. Nur ein expliziter kopierter Sandbox-Eingang ist erlaubt."
MSG_MISSING_OUTPUT = "Ausgabeordner fehlt. Nur ein expliziter Sandbox-Ausgabeordner ist erlaubt."
MSG_SAME_INPUT_OUTPUT = "Eingangs- und Ausgabeordner dürfen nicht identisch sein."
MSG_DRY_RUN_REQUIRED = "dry_run muss true sein. Produktivläufe sind außerhalb dieses Contracts."
MSG_NO_MUTATION_REQUIRED = "no_mutation muss true sein. Source-Mutationen sind verboten."
MSG_PRODUCTIVE_BLOCKED = "Produktiver Modus ist gesperrt (productive_mode_requested muss false sein)."
MSG_COPIED_DATA_CONFIRMATION = (
    "copied_data_confirmation muss true sein. Nur kopierte Testdaten sind erlaubt."
)
MSG_ORIGINAL_EXCLUSION = (
    "original_folder_exclusion_confirmation muss true sein. "
    "Originalordner sind ausgeschlossen."
)
MSG_MISSING_PROFILE = "Profil fehlt (profile_id oder profile_name erforderlich)."
MSG_MISSING_CONFIGURATION = (
    "Konfiguration fehlt (configuration_id oder configuration_name erforderlich)."
)
MSG_ORIGINAL_LOOKING = "Pfad wirkt wie Original-/Produktivordner"
MSG_OUTSIDE_SANDBOX = "Pfad liegt außerhalb der expliziten Sandbox-Policy."
MSG_SAFETY_FLAG = "Sicherheitsflag verletzt die Core-Dry-Run-No-Mutation-Policy."
MSG_MODE = "mode muss sandbox_dry_run sein."

# Optional env-scoped copied sandbox/test roots (colon/semicolon/newline separated).
# Product defaults stay empty — no Hadi-specific hardcoding.
ENV_COPIED_SANDBOX_TEST_ROOTS = "KI_RECHNUNGEN_COPIED_SANDBOX_TEST_ROOTS"

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

# Hard productive/original markers — never overridden by sandbox/test signals.
_FORBIDDEN_PRODUCTIVE_MARKERS = (
    "/rechnungen/",
    "/02_rechnungseingang/",
    "/rechnungseingang/",
    "/original/",
    "/produktiv/",
)
_FORBIDDEN_PRODUCTIVE_SEGMENTS = frozenset(
    {
        "rechnungen",
        "02_rechnungseingang",
        "rechnungseingang",
        "original",
        "produktiv",
    }
)
_POSITIVE_SANDBOX_SEGMENTS = frozenset(
    {
        "sandbox",
        "test",
        "tests",
        "testdata",
        "test_data",
        "input_copy",
        "output_preview",
    }
)
# Token "test" inside a segment (KI-Rechnungen-Test) — not bare substring of "latest".
_POSITIVE_TEST_TOKEN_RE = re.compile(
    r"(?:^|[-_\s])test(?:$|[-_\s])",
    re.IGNORECASE,
)
_POSITIVE_SANDBOX_TOKEN_RE = re.compile(
    r"(?:^|[-_\s])sandbox(?:$|[-_\s])",
    re.IGNORECASE,
)
_POSITIVE_INPUT_COPY_RE = re.compile(
    r"(?:^|[-_\s])input_copy(?:$|[-_\s])",
    re.IGNORECASE,
)
_POSITIVE_OUTPUT_PREVIEW_RE = re.compile(
    r"(?:^|[-_\s])output_preview(?:$|[-_\s])",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Safety policy / request / result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoreDryRunSafetyPolicy:
    """Mandatory safety defaults for Core Dry-Run Sandbox runs."""

    dry_run: bool = True
    no_mutation: bool = True
    no_move_originals: bool = True
    no_archive_source: bool = True
    no_rename_source: bool = True
    no_delete_source: bool = True
    no_write_outside_sandbox: bool = True
    no_productive_mode: bool = True
    no_real_datev_cloud_export: bool = True
    no_private_defaults: bool = True
    no_filename_as_truth: bool = True
    require_copied_input: bool = True
    require_explicit_sandbox_output: bool = True
    forbid_app_support_side_effects: bool = True
    planned_destinations_data_only: bool = True


@dataclass(frozen=True)
class CoreDryRunRequest:
    """Caller-facing request for a Core Dry-Run Sandbox run.

    Prompt 2/34 must implement processing against this shape without mutating
    source folders or writing outside the sandbox output root.
    """

    input_dir: str | None
    output_dir: str | None
    dry_run: bool = True
    no_mutation: bool = True
    copied_data_confirmation: bool = False
    original_folder_exclusion_confirmation: bool = False
    productive_mode_requested: bool = False
    profile_id: str | None = None
    profile_name: str | None = None
    configuration_id: str | None = None
    configuration_name: str | None = None
    run_id: str | None = None
    sandbox_root: str | None = None
    original_source_folder: str | None = None
    mode: CoreDryRunMode = CoreDryRunMode.SANDBOX_DRY_RUN
    no_move_originals: bool = True
    no_archive_source: bool = True
    no_rename_source: bool = True
    no_delete_source: bool = True
    no_write_outside_sandbox: bool = True


@dataclass(frozen=True)
class CoreDryRunPlannedDestination:
    """Data-only planned destination — never implies a performed file move."""

    document_name: str
    planned_path: str
    destination_label: str | None = None
    reason: str | None = None
    applied: bool = False  # always False in dry-run contract semantics


@dataclass(frozen=True)
class CoreDryRunDocumentResult:
    """Recognized / successfully classified document row (structured data)."""

    document_name: str
    document_type: str
    classification_status: str
    status_label: str
    confidence_label: str | None = None
    target_hint: str | None = None
    evidence_summary: str | None = None


@dataclass(frozen=True)
class CoreDryRunReviewItem:
    """Review / unclear document that needs human attention."""

    document_name: str
    reason: str
    status_label: str = "unklar"
    document_id: str | None = None
    evidence_summary: str | None = None
    next_action_hint: str | None = None


@dataclass(frozen=True)
class CoreDryRunErrorItem:
    """Failed / error document row."""

    document_name: str
    error_code: str
    message: str
    status_label: str = "fehler"


@dataclass(frozen=True)
class CoreDryRunSummary:
    """Aggregate counts for a dry-run result."""

    total_documents: int = 0
    recognized_count: int = 0
    review_count: int = 0
    error_count: int = 0
    planned_destination_count: int = 0


@dataclass(frozen=True)
class CoreDryRunSafetyProof:
    """Post-run / contract-level no-mutation proof metadata."""

    no_original_mutation: bool
    no_source_archive: bool
    no_source_rename: bool
    no_source_delete: bool
    no_source_move: bool
    writes_confined_to_sandbox_output: bool
    productive_mode_disabled: bool
    real_datev_cloud_export_disabled: bool
    filename_as_truth_disabled: bool
    private_defaults_disabled: bool
    planned_destinations_not_applied: bool
    evidence_notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CoreDryRunResult:
    """Structured result sufficient for Track-B bridge / workspace mapping."""

    status: CoreDryRunStatus
    run_id: str | None = None
    recognized: tuple[CoreDryRunDocumentResult, ...] = field(default_factory=tuple)
    review: tuple[CoreDryRunReviewItem, ...] = field(default_factory=tuple)
    errors: tuple[CoreDryRunErrorItem, ...] = field(default_factory=tuple)
    planned_destinations: tuple[CoreDryRunPlannedDestination, ...] = field(
        default_factory=tuple
    )
    summary: CoreDryRunSummary = field(default_factory=CoreDryRunSummary)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    safety_proof: CoreDryRunSafetyProof | None = None
    message: str | None = None
    contract_error_codes: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Path helpers (string-only — no FS IO)
# ---------------------------------------------------------------------------


def _norm(path: str | None) -> str | None:
    value = (path or "").strip()
    if not value:
        return None
    return value.replace("\\", "/").rstrip("/")


def _is_under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _path_segments(normalized: str) -> tuple[str, ...]:
    return tuple(seg for seg in normalized.replace("\\", "/").split("/") if seg)


def _env_copied_sandbox_test_roots() -> tuple[str, ...]:
    """Optional explicit copied sandbox/test roots from env — never product defaults."""

    raw = (os.environ.get(ENV_COPIED_SANDBOX_TEST_ROOTS) or "").strip()
    if not raw:
        return ()
    roots: list[str] = []
    for part in re.split(r"[:;\n]+", raw):
        normalized = _norm(part)
        if normalized is not None:
            roots.append(normalized)
    return tuple(roots)


def path_has_forbidden_productive_marker(path: str | None) -> bool:
    """True when a path contains hard productive/original markers."""

    normalized = _norm(path)
    if normalized is None:
        return False
    probe = f"/{normalized.lower()}/"
    if any(marker in probe for marker in _FORBIDDEN_PRODUCTIVE_MARKERS):
        return True
    for segment in _path_segments(normalized):
        if segment.lower() in _FORBIDDEN_PRODUCTIVE_SEGMENTS:
            return True
    return False


def path_has_positive_sandbox_test_signal(path: str | None) -> bool:
    """True when a path carries an explicit copied sandbox/test signal.

    Positive signals are required before Desktop/Rechnung heuristics may be
    overridden. No blanket Desktop or Rechnung allow.
    """

    normalized = _norm(path)
    if normalized is None:
        return False
    for root in _env_copied_sandbox_test_roots():
        if _is_under(normalized, root):
            return True
    for segment in _path_segments(normalized):
        lowered = segment.lower()
        if lowered in _POSITIVE_SANDBOX_SEGMENTS:
            return True
        if _POSITIVE_TEST_TOKEN_RE.search(segment):
            return True
        if _POSITIVE_SANDBOX_TOKEN_RE.search(segment):
            return True
        if _POSITIVE_INPUT_COPY_RE.search(segment):
            return True
        if _POSITIVE_OUTPUT_PREVIEW_RE.search(segment):
            return True
    return False


def is_explicit_copied_sandbox_test_path(path: str | None) -> bool:
    """Positive sandbox/test path that is not a hard productive/original path."""

    if path_has_forbidden_productive_marker(path):
        return False
    normalized = _norm(path)
    if normalized is None:
        return False
    probe = f"/{normalized}"
    # Named original-looking folders (somaa, test rechnungen, …) stay blocked.
    if _ORIGINAL_LOOKING_PATH_RE.search(probe):
        return False
    return path_has_positive_sandbox_test_signal(normalized)


def path_looks_like_original(
    path: str | None,
    *,
    original_source_folder: str | None = None,
) -> bool:
    """Heuristic original-folder rejection — string-only, no FS IO.

    Positive copied sandbox/test paths may override Desktop/Rechnung heuristics
    only when hard productive markers and named original patterns are absent.
    """

    normalized = _norm(path)
    if normalized is None:
        return False
    original = _norm(original_source_folder)
    if original is not None and (
        normalized == original or _is_under(normalized, original)
    ):
        return True
    if path_has_forbidden_productive_marker(normalized):
        return True
    probe = f"/{normalized}"
    if _ORIGINAL_LOOKING_PATH_RE.search(probe):
        return True
    # Positive sandbox/test override — do not weaken hard blocks above.
    if is_explicit_copied_sandbox_test_path(normalized):
        return False
    if _DESKTOP_ORIGINAL_RE.search(normalized):
        return True
    return False


def _has_profile(request: CoreDryRunRequest) -> bool:
    return bool((request.profile_id or "").strip() or (request.profile_name or "").strip())


def _has_configuration(request: CoreDryRunRequest) -> bool:
    return bool(
        (request.configuration_id or "").strip()
        or (request.configuration_name or "").strip()
    )


def _reject(code: str, message: str) -> None:
    raise CoreDryRunContractViolation(code, message)


# ---------------------------------------------------------------------------
# Validation / requirements
# ---------------------------------------------------------------------------


def build_core_dry_run_contract_requirements(
    policy: CoreDryRunSafetyPolicy | None = None,
) -> Mapping[str, Any]:
    """Machine-readable contract requirements for docs/tests/Prompt 2."""

    safety = policy or CoreDryRunSafetyPolicy()
    return {
        "api_name": "core_dry_run_sandbox",
        "mode": CoreDryRunMode.SANDBOX_DRY_RUN.value,
        "next_implementation_task": (
            "KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01"
        ),
        "required_request_fields": (
            "input_dir",
            "output_dir",
            "profile_id|profile_name",
            "configuration_id|configuration_name",
            "dry_run=true",
            "no_mutation=true",
            "copied_data_confirmation=true",
            "original_folder_exclusion_confirmation=true",
            "productive_mode_requested=false",
        ),
        "forbidden_mutations": (
            "move_source",
            "archive_source",
            "rename_source",
            "delete_source",
            "write_outside_sandbox_output",
            "productive_mode",
            "real_datev_cloud_export",
            "private_defaults",
            "filename_as_truth",
            "app_support_side_effects_outside_sandbox",
        ),
        "allowed_sandbox_artifacts": (
            "structured_result_payload",
            "optional_sandbox_output_reports_under_output_dir",
            "planned_destination_records_data_only",
        ),
        "result_buckets": ("recognized", "review", "errors", "planned_destinations"),
        "statuses": tuple(status.value for status in CoreDryRunStatus),
        "safety_policy": {
            "dry_run": safety.dry_run,
            "no_mutation": safety.no_mutation,
            "no_move_originals": safety.no_move_originals,
            "no_archive_source": safety.no_archive_source,
            "no_rename_source": safety.no_rename_source,
            "no_delete_source": safety.no_delete_source,
            "no_write_outside_sandbox": safety.no_write_outside_sandbox,
            "no_productive_mode": safety.no_productive_mode,
            "no_real_datev_cloud_export": safety.no_real_datev_cloud_export,
            "no_private_defaults": safety.no_private_defaults,
            "no_filename_as_truth": safety.no_filename_as_truth,
            "require_copied_input": safety.require_copied_input,
            "require_explicit_sandbox_output": safety.require_explicit_sandbox_output,
            "forbid_app_support_side_effects": safety.forbid_app_support_side_effects,
            "planned_destinations_data_only": safety.planned_destinations_data_only,
        },
        "track_b_call_path": (
            "ui_v2.workspace → sandbox_execution_boundary → core_bridge → "
            "core_dry_run_sandbox_api (Prompt 2) → map to ProcessingRunState"
        ),
        "processing_core_entrypoint_not_safe": "invoice_tool.run.run_once",
    }


def validate_core_dry_run_request(
    request: CoreDryRunRequest,
    *,
    policy: CoreDryRunSafetyPolicy | None = None,
) -> CoreDryRunRequest:
    """Validate a Core Dry-Run request against the sandbox contract.

    Returns the same request on success. Raises ``CoreDryRunContractViolation``
    on any contract breach. Performs no filesystem IO and no processing.
    """

    safety = policy or CoreDryRunSafetyPolicy()

    if request.mode != CoreDryRunMode.SANDBOX_DRY_RUN:
        _reject(ERROR_MODE, MSG_MODE)

    if request.productive_mode_requested or not safety.no_productive_mode:
        _reject(ERROR_PRODUCTIVE_BLOCKED, MSG_PRODUCTIVE_BLOCKED)

    if not request.dry_run or not safety.dry_run:
        _reject(ERROR_DRY_RUN_REQUIRED, MSG_DRY_RUN_REQUIRED)

    if not request.no_mutation or not safety.no_mutation:
        _reject(ERROR_NO_MUTATION_REQUIRED, MSG_NO_MUTATION_REQUIRED)

    if not request.copied_data_confirmation or not safety.require_copied_input:
        _reject(ERROR_COPIED_DATA_CONFIRMATION, MSG_COPIED_DATA_CONFIRMATION)

    if (
        not request.original_folder_exclusion_confirmation
        or not safety.require_copied_input
    ):
        _reject(ERROR_ORIGINAL_EXCLUSION_CONFIRMATION, MSG_ORIGINAL_EXCLUSION)

    flag_pairs = (
        (request.no_move_originals, safety.no_move_originals),
        (request.no_archive_source, safety.no_archive_source),
        (request.no_rename_source, safety.no_rename_source),
        (request.no_delete_source, safety.no_delete_source),
        (request.no_write_outside_sandbox, safety.no_write_outside_sandbox),
    )
    if not all(flag and required for flag, required in flag_pairs):
        _reject(ERROR_SAFETY_FLAG, MSG_SAFETY_FLAG)

    input_dir = _norm(request.input_dir)
    output_dir = _norm(request.output_dir)
    if input_dir is None:
        _reject(ERROR_MISSING_INPUT, MSG_MISSING_INPUT)
    if output_dir is None:
        _reject(ERROR_MISSING_OUTPUT, MSG_MISSING_OUTPUT)
    if input_dir == output_dir:
        _reject(ERROR_SAME_INPUT_OUTPUT, MSG_SAME_INPUT_OUTPUT)

    if not _has_profile(request):
        _reject(ERROR_MISSING_PROFILE, MSG_MISSING_PROFILE)
    if not _has_configuration(request):
        _reject(ERROR_MISSING_CONFIGURATION, MSG_MISSING_CONFIGURATION)

    original = _norm(request.original_source_folder)
    for path in (input_dir, output_dir):
        if path_looks_like_original(path, original_source_folder=original):
            _reject(ERROR_ORIGINAL_LOOKING, MSG_ORIGINAL_LOOKING)

    sandbox_root = _norm(request.sandbox_root)
    if sandbox_root is not None and safety.no_write_outside_sandbox:
        if not _is_under(input_dir, sandbox_root) or not _is_under(
            output_dir, sandbox_root
        ):
            _reject(ERROR_OUTSIDE_SANDBOX, MSG_OUTSIDE_SANDBOX)

    return request


def empty_safety_proof(*, evidence_notes: tuple[str, ...] = ()) -> CoreDryRunSafetyProof:
    """Canonical safety-proof defaults for a compliant dry-run outcome."""

    return CoreDryRunSafetyProof(
        no_original_mutation=True,
        no_source_archive=True,
        no_source_rename=True,
        no_source_delete=True,
        no_source_move=True,
        writes_confined_to_sandbox_output=True,
        productive_mode_disabled=True,
        real_datev_cloud_export_disabled=True,
        filename_as_truth_disabled=True,
        private_defaults_disabled=True,
        planned_destinations_not_applied=True,
        evidence_notes=evidence_notes,
    )


def build_blocked_core_dry_run_result(
    violation: CoreDryRunContractViolation,
    *,
    run_id: str | None = None,
) -> CoreDryRunResult:
    """Map a contract violation into a blocked result (no processing)."""

    return CoreDryRunResult(
        status=CoreDryRunStatus.BLOCKED,
        run_id=run_id,
        message=violation.message,
        contract_error_codes=(violation.code,),
        safety_proof=empty_safety_proof(
            evidence_notes=(
                "request_blocked_before_processing",
                "no_files_processed",
                "no_source_mutation",
            )
        ),
        summary=CoreDryRunSummary(),
    )


def summarize_core_dry_run_buckets(
    *,
    recognized: tuple[CoreDryRunDocumentResult, ...],
    review: tuple[CoreDryRunReviewItem, ...],
    errors: tuple[CoreDryRunErrorItem, ...],
    planned_destinations: tuple[CoreDryRunPlannedDestination, ...],
) -> CoreDryRunSummary:
    """Build summary counts from separated result buckets."""

    return CoreDryRunSummary(
        total_documents=len(recognized) + len(review) + len(errors),
        recognized_count=len(recognized),
        review_count=len(review),
        error_count=len(errors),
        planned_destination_count=len(planned_destinations),
    )


__all__ = (
    "CoreDryRunContractViolation",
    "CoreDryRunDocumentResult",
    "CoreDryRunErrorItem",
    "CoreDryRunMode",
    "CoreDryRunPlannedDestination",
    "CoreDryRunRequest",
    "CoreDryRunResult",
    "CoreDryRunReviewItem",
    "CoreDryRunSafetyPolicy",
    "CoreDryRunSafetyProof",
    "CoreDryRunStatus",
    "CoreDryRunSummary",
    "ENV_COPIED_SANDBOX_TEST_ROOTS",
    "ERROR_COPIED_DATA_CONFIRMATION",
    "ERROR_DRY_RUN_REQUIRED",
    "ERROR_MISSING_CONFIGURATION",
    "ERROR_MISSING_INPUT",
    "ERROR_MISSING_OUTPUT",
    "ERROR_MISSING_PROFILE",
    "ERROR_MODE",
    "ERROR_NO_MUTATION_REQUIRED",
    "ERROR_ORIGINAL_EXCLUSION_CONFIRMATION",
    "ERROR_ORIGINAL_LOOKING",
    "ERROR_OUTSIDE_SANDBOX",
    "ERROR_PRODUCTIVE_BLOCKED",
    "ERROR_SAFETY_FLAG",
    "ERROR_SAME_INPUT_OUTPUT",
    "MSG_ORIGINAL_LOOKING",
    "build_blocked_core_dry_run_result",
    "build_core_dry_run_contract_requirements",
    "empty_safety_proof",
    "is_explicit_copied_sandbox_test_path",
    "path_has_forbidden_productive_marker",
    "path_has_positive_sandbox_test_signal",
    "path_looks_like_original",
    "summarize_core_dry_run_buckets",
    "validate_core_dry_run_request",
)
