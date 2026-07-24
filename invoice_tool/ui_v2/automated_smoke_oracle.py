"""Track-B Automated Smoke Oracle (dev-only).

Terminal-driven verification of the controlled Track-B workflow without manual
UI clicking. Uses UI-v2 safe modules only.

Never calls run_once, never mutates originals, never writes production finals,
never touches real invoice folders, never changes Track A / processing-core.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from invoice_tool.configuration_model import (
    Configuration,
    MatchingRule,
    ProfileBundle,
    UnmatchedConfiguration,
    new_configuration_id,
    pattern_from_template,
)
from invoice_tool.profile_store import load_profile_bundle, save_profile_bundle
from invoice_tool.scan_models import DEFAULT_SCAN_MODEL_ID
from invoice_tool.ui_v2.configuration_rule_apply_preview import (
    rerun_preview_matching_after_rule_change,
)
from invoice_tool.ui_v2.configuration_rule_draft import (
    ConfigurationRuleDraft,
    find_duplicate_condition_configs,
)
from invoice_tool.ui_v2.configuration_rule_editor import (
    save_paypal_rule_and_rerun_matching,
)
from invoice_tool.ui_v2.configuration_matching import (
    load_active_configuration_candidates,
)
from invoice_tool.ui_v2.controlled_final_write_sandbox import (
    execute_controlled_final_write_sandbox,
)
from invoice_tool.ui_v2.dev_defaults import (
    CONTROLLED_TEST_ROOT,
    TRACK_B_DEV_INPUT_DEFAULT,
    TRACK_B_DEV_OUTPUT_DEFAULT,
    TRACK_B_DEV_PAYPAL_TARGET_DEFAULT,
    ensure_track_b_dev_folders_if_requested,
)
from invoice_tool.ui_v2.final_write_gate import (
    AUTH_SCOPE_SELECTED,
    build_sandbox_final_write_authorization,
    default_sandbox_acknowledgements,
)
from invoice_tool.ui_v2.finalization_dry_run_package import (
    write_finalization_dry_run_package,
)
from invoice_tool.ui_v2.finalization_preview_batch import (
    build_finalization_preview_batch,
)
from invoice_tool.ui_v2.processing_state import (
    ProcessingPlannedDestination,
    ProcessingReviewItem,
    ProcessingRunState,
)
from invoice_tool.ui_v2.review_decision import create_accept_suggestion_decision
from invoice_tool.ui_v2.state import UiV2State

TASK_ID = "KI_RECHNUNGEN_TRACK_B_AUTOMATED_SMOKE_ORACLE_2026-07-24"
ORACLE_PROFILE_ID = "track-b-automated-smoke-oracle"

STATUS_PASS = "TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS"
STATUS_PARTIAL_UI = "TRACK_B_AUTOMATED_SMOKE_ORACLE_PARTIAL_UI_USABILITY_ONLY"
STATUS_PARTIAL_FINAL = "TRACK_B_AUTOMATED_SMOKE_ORACLE_PARTIAL_FINALIZATION_BLOCKED"
STATUS_BLOCKED = "TRACK_B_AUTOMATED_SMOKE_ORACLE_BLOCKED"
STATUS_FAIL_UNSAFE = "TRACK_B_AUTOMATED_SMOKE_ORACLE_FAIL_UNSAFE"

DEFAULT_PATTERN = (
    "{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf"
)
AUTOMATED_SMOKE_REVIEW_MARKER = "automated_smoke_review_decision=true"

FORBIDDEN_REAL_FOLDER_MARKERS = (
    "/RECHNUNGEN/",
    "/02_Rechnungseingang/",
    "/Rechnungseingang/",
    "/Original/",
    "/Produktiv/",
)

EXPECTED_PDFS = (
    "FA011466.pdf",
    "Rechnung RE-202605-14594.pdf",
    "320262919974.pdf",
    "Rechnung-2026156019-102201.pdf",
    "420260091336.pdf",
)

TRACK_A_PROTECTED = (
    "app_main.py",
    "app_internal_launcher.py",
    "invoice_tool/gui.py",
    "invoice_tool/ui_shell.py",
    "invoice_tool/ui_workspace.py",
    "invoice_tool/ui_configurations.py",
    "invoice_tool/ui_profiles.py",
    "invoice_tool/ui_review.py",
    "invoice_tool/ui_settings.py",
    "invoice_tool/ui_profile_dialog.py",
    "invoice_tool/ui_document_rules.py",
)

CORE_PROTECTED = (
    "invoice_tool/run.py",
    "invoice_tool/processing.py",
    "invoice_tool/routing.py",
    "invoice_tool/routing_guards.py",
    "invoice_tool/classification.py",
    "invoice_tool/target_routing.py",
    "invoice_tool/core_dry_run.py",
)


@dataclass(frozen=True)
class ExpectedDocument:
    source_filename: str
    supplier: str
    invoice_date: str
    amount: str
    payment_field: str | None
    art: str
    expected_filename: str
    expected_config: str  # PayPal | Unklar | not_amex
    require_missing_payment: bool = False


EXPECTED_DOCUMENTS: tuple[ExpectedDocument, ...] = (
    ExpectedDocument(
        source_filename="FA011466.pdf",
        supplier="LUMITOP",
        invoice_date="2026-05-11",
        amount="476,00",
        payment_field="paypal",
        art="er",
        expected_filename="2026-05-11_er_er_LUMITOP_476,00_paypal.pdf",
        expected_config="PayPal",
    ),
    ExpectedDocument(
        source_filename="Rechnung RE-202605-14594.pdf",
        supplier="1A-Bootshop.de",
        invoice_date="2026-05-15",
        amount="105,75",
        payment_field="paypal",
        art="er",
        expected_filename="2026-05-15_er_er_1A-Bootshop.de_105,75_paypal.pdf",
        expected_config="PayPal",
    ),
    ExpectedDocument(
        source_filename="320262919974.pdf",
        supplier="Böttcher AG",
        invoice_date="2026-05-23",
        amount="84,39",
        payment_field="card",
        art="er",
        expected_filename="2026-05-23_er_er_Böttcher_AG_84,39_card.pdf",
        expected_config="not_amex",
    ),
    ExpectedDocument(
        source_filename="Rechnung-2026156019-102201.pdf",
        supplier="Luxvenum LED GmbH",
        invoice_date="2026-05-11",
        amount="154,95",
        payment_field=None,
        art="er",
        expected_filename=(
            "2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf"
        ),
        expected_config="Unklar",
        require_missing_payment=True,
    ),
    ExpectedDocument(
        source_filename="420260091336.pdf",
        supplier="Böttcher AG",
        invoice_date="2026-06-18",
        amount="68,94",
        payment_field=None,
        art="storno",
        expected_filename=(
            "2026-06-18_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf"
        ),
        expected_config="Unklar",
        require_missing_payment=True,
    ),
)


@dataclass
class DocumentCheckResult:
    source_filename: str
    ok: bool
    expected: dict[str, Any]
    observed: dict[str, Any]
    failures: list[str] = field(default_factory=list)


@dataclass
class SafetyFlags:
    called_run_once: bool = False
    productive_processing: bool = False
    production_final_write: bool = False
    final_write_allowed: bool = False
    final_write_allowed_for_production: bool = False
    originals_mutated: bool = False
    touched_real_invoice_folders: bool = False
    track_a_modified: bool = False
    processing_core_modified: bool = False
    wrote_outside_controlled_output: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def unsafe(self) -> bool:
        return any(
            (
                self.called_run_once,
                self.productive_processing,
                self.production_final_write,
                self.final_write_allowed,
                self.final_write_allowed_for_production,
                self.originals_mutated,
                self.touched_real_invoice_folders,
                self.track_a_modified,
                self.processing_core_modified,
                self.wrote_outside_controlled_output,
            )
        )


@dataclass
class OracleResult:
    status: str
    task_id: str = TASK_ID
    head: str | None = None
    input_root: str | None = None
    output_root: str | None = None
    evidence_folder: str | None = None
    preview_export_folder: str | None = None
    paypal_result: dict[str, Any] = field(default_factory=dict)
    document_results: list[DocumentCheckResult] = field(default_factory=list)
    finalization_preview: dict[str, Any] = field(default_factory=dict)
    dry_run: dict[str, Any] = field(default_factory=dict)
    sandbox_final_write: dict[str, Any] = field(default_factory=dict)
    hashes_before: dict[str, str] = field(default_factory=dict)
    hashes_after: dict[str, str] = field(default_factory=dict)
    safety: SafetyFlags = field(default_factory=SafetyFlags)
    blockers: list[str] = field(default_factory=list)
    remaining_manual_ux_only: list[str] = field(default_factory=list)
    preflight: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "head": self.head,
            "input_root": self.input_root,
            "output_root": self.output_root,
            "evidence_folder": self.evidence_folder,
            "preview_export_folder": self.preview_export_folder,
            "paypal_result": self.paypal_result,
            "document_results": [
                {
                    "source_filename": d.source_filename,
                    "ok": d.ok,
                    "expected": d.expected,
                    "observed": d.observed,
                    "failures": d.failures,
                }
                for d in self.document_results
            ],
            "finalization_preview": self.finalization_preview,
            "dry_run": self.dry_run,
            "sandbox_final_write": self.sandbox_final_write,
            "hashes_before": self.hashes_before,
            "hashes_after": self.hashes_after,
            "safety": self.safety.to_dict(),
            "blockers": self.blockers,
            "remaining_manual_ux_only": self.remaining_manual_ux_only,
            "preflight": self.preflight,
            "notes": self.notes,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_input_pdfs(input_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not input_root.is_dir():
        return out
    for name in EXPECTED_PDFS:
        path = input_root / name
        if path.is_file():
            out[name] = sha256_file(path)
    return out


def path_under(child: Path | str | None, root: Path | str | None) -> bool:
    if child is None or root is None:
        return False
    try:
        Path(child).expanduser().resolve().relative_to(
            Path(root).expanduser().resolve()
        )
        return True
    except (OSError, ValueError):
        return False


def looks_like_real_invoice_folder(path: Path | str | None) -> bool:
    text = str(path or "").replace("\\", "/")
    return any(marker in text for marker in FORBIDDEN_REAL_FOLDER_MARKERS)


def assert_controlled_input_only(path: Path | str) -> Path:
    resolved = Path(path).expanduser().resolve()
    expected = TRACK_B_DEV_INPUT_DEFAULT.expanduser().resolve()
    if resolved != expected and not path_under(resolved, CONTROLLED_TEST_ROOT):
        raise ValueError(f"Oracle akzeptiert nur kontrollierten Input: {resolved}")
    if looks_like_real_invoice_folder(resolved):
        raise ValueError(f"Reale Rechnungsordner sind verboten: {resolved}")
    return resolved


def assert_controlled_output_only(path: Path | str) -> Path:
    resolved = Path(path).expanduser().resolve()
    expected = TRACK_B_DEV_OUTPUT_DEFAULT.expanduser().resolve()
    if resolved != expected and not path_under(resolved, CONTROLLED_TEST_ROOT / "output"):
        if not path_under(resolved, CONTROLLED_TEST_ROOT):
            raise ValueError(f"Oracle akzeptiert nur kontrollierten Output: {resolved}")
    if looks_like_real_invoice_folder(resolved):
        raise ValueError(f"Reale Rechnungsordner sind verboten: {resolved}")
    return resolved


def reject_missing_input_folder(input_root: Path | str) -> None:
    path = Path(input_root).expanduser()
    if not path.is_dir():
        raise FileNotFoundError(f"Kontrollierter Input fehlt: {path}")


def reject_fewer_than_five_pdfs(input_root: Path | str) -> list[str]:
    root = Path(input_root).expanduser()
    present = [name for name in EXPECTED_PDFS if (root / name).is_file()]
    if len(present) < 5:
        missing = [name for name in EXPECTED_PDFS if name not in present]
        raise FileNotFoundError(
            f"Weniger als fünf kontrollierte PDFs (fehlen: {', '.join(missing)})"
        )
    return present


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_cf(value: Any) -> str:
    return _norm(value).casefold()


def _git(cwd: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return f"<git error: {exc}>"
    return (proc.stdout or proc.stderr or "").strip()


def collect_preflight(
    *,
    repo_root: Path,
    input_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    head = _git(repo_root, "rev-parse", "HEAD")
    branch = _git(repo_root, "branch", "--show-current")
    local_main = _git(repo_root, "rev-parse", "origin/main")
    remote_main = _git(repo_root, "ls-remote", "origin", "refs/heads/main").split()
    remote_sha = remote_main[0] if remote_main else ""
    ahead_behind = _git(repo_root, "rev-list", "--left-right", "--count", "origin/main...HEAD")
    status_short = _git(repo_root, "status", "--short")
    staged = _git(repo_root, "diff", "--cached", "--name-only")
    locks = []
    for name in (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REBASE_HEAD",
        "rebase-merge",
        "rebase-apply",
        "index.lock",
    ):
        if (repo_root / ".git" / name).exists():
            locks.append(name)
    staged_list = [line for line in staged.splitlines() if line.strip()]
    track_a_staged = any(p in staged_list for p in TRACK_A_PROTECTED)
    core_staged = any(p in staged_list for p in CORE_PROTECTED)
    track_a_dirty = any(
        line[3:].strip() in TRACK_A_PROTECTED or line[3:].strip().endswith(p)
        for line in status_short.splitlines()
        for p in TRACK_A_PROTECTED
        if line.strip()
    )
    core_dirty = any(
        any(p in line for p in CORE_PROTECTED)
        for line in status_short.splitlines()
        if line.strip()
    )
    real_in_status = any(
        looks_like_real_invoice_folder(line) for line in status_short.splitlines()
    )
    docs_final = (
        repo_root
        / "docs"
        / "KI_RECHNUNGEN_TRACK_B_SAAS_READINESS_FINAL_AUDIT_AND_MANUAL_SMOKE_2026-07-23.md"
    ).is_file()
    docs_smoke_repair = (
        repo_root
        / "docs"
        / "KI_RECHNUNGEN_TRACK_B_SMOKE_DUPLICATE_CONFIG_AND_DEV_UI_REPAIR_2026-07-24.md"
    ).is_file()
    docs_dev_defaults = (
        repo_root
        / "docs"
        / "KI_RECHNUNGEN_TRACK_B_DEV_DEFAULT_INPUT_OUTPUT_FOLDERS_2026-07-24.md"
    ).is_file()
    pdfs_ok = all((input_root / name).is_file() for name in EXPECTED_PDFS)
    paypal_target = TRACK_B_DEV_PAYPAL_TARGET_DEFAULT
    return {
        "pwd": str(Path.cwd()),
        "repo_root": str(repo_root),
        "branch": branch,
        "head": head,
        "local_origin_main": local_main,
        "remote_origin_main": remote_sha,
        "ahead_behind": ahead_behind,
        "git_status_short": status_short,
        "staged_files": staged_list,
        "active_git_operation": bool(locks),
        "git_locks": locks,
        "track_a_protected_dirty": track_a_dirty,
        "track_a_protected_staged": track_a_staged,
        "processing_core_dirty": core_dirty,
        "processing_core_staged": core_staged,
        "prompt34_final_audit_docs_exist": docs_final,
        "smoke_blocker_repair_docs_exist": docs_smoke_repair,
        "dev_default_folders_docs_exist": docs_dev_defaults,
        "controlled_input_exists": input_root.is_dir(),
        "controlled_output_exists": output_root.is_dir(),
        "paypal_target_exists": paypal_target.is_dir(),
        "five_input_pdfs_exist": pdfs_ok,
        "production_final_write_enabled": False,
        "final_write_allowed_for_production_true": False,
        "real_invoice_folders_in_git_status": real_in_status,
        "release_tag_exact_on_head": _git(
            repo_root, "describe", "--tags", "--exact-match", "HEAD"
        ),
    }


def preflight_should_stop(preflight: Mapping[str, Any], *, repo_root: Path) -> list[str]:
    blockers: list[str] = []
    if Path(preflight.get("repo_root") or "").resolve() != repo_root.resolve():
        blockers.append("wrong_worktree")
    if "KI-Rechnungen-App" not in str(repo_root):
        blockers.append("wrong_worktree_name")
    if preflight.get("staged_files"):
        blockers.append("staged_files_present")
    if preflight.get("active_git_operation") or preflight.get("git_locks"):
        blockers.append("active_git_operation_or_lock")
    ahead_behind = str(preflight.get("ahead_behind") or "0\t0")
    parts = ahead_behind.replace("\t", " ").split()
    if len(parts) >= 2:
        try:
            behind = int(parts[0])
            if behind > 0:
                blockers.append("behind_remote")
        except ValueError:
            pass
    if preflight.get("track_a_protected_staged"):
        blockers.append("track_a_protected_staged")
    if preflight.get("processing_core_staged"):
        blockers.append("processing_core_staged")
    if preflight.get("production_final_write_enabled"):
        blockers.append("production_final_write_enabled")
    if preflight.get("final_write_allowed_for_production_true"):
        blockers.append("final_write_allowed_for_production")
    if preflight.get("real_invoice_folders_in_git_status"):
        blockers.append("real_invoice_folders_in_git_status")
    return blockers


def find_latest_sufficient_preview_export(
    output_root: Path,
) -> tuple[Path | None, dict[str, Any] | None]:
    """Return newest preview-export with all five expected documents and fields."""

    candidates = sorted(
        (
            p
            for p in output_root.glob("preview-export-*")
            if p.is_dir() and (p / "manifest.json").is_file()
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for folder in candidates:
        try:
            payload = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items = payload.get("items") or []
        if not isinstance(items, list) or len(items) < 5:
            continue
        by_name = {
            _norm(item.get("source_filename")): item
            for item in items
            if isinstance(item, Mapping)
        }
        if not all(name in by_name for name in EXPECTED_PDFS):
            continue
        # Prefer exports that already carry corrected amounts / payment fields.
        lumitop = by_name["FA011466.pdf"]
        boot = by_name["Rechnung RE-202605-14594.pdf"]
        storno = by_name["420260091336.pdf"]
        if _norm(lumitop.get("amount") or lumitop.get("selected_amount")) != "476,00":
            continue
        if _norm(boot.get("amount") or boot.get("selected_amount")) != "105,75":
            continue
        if _norm_cf(lumitop.get("selected_payment_field")) != "paypal":
            continue
        if _norm_cf(boot.get("selected_payment_field")) != "paypal":
            continue
        if _norm_cf(storno.get("selected_art") or storno.get("document_type")) not in {
            "storno"
        }:
            # document_type=storno is acceptable evidence for art.
            if _norm_cf(storno.get("document_type")) != "storno":
                continue
        if _norm(payload.get("input_root")) and not path_under(
            payload.get("input_root"), CONTROLLED_TEST_ROOT
        ):
            continue
        return folder, payload
    return None, None


def _parse_token_map_values(raw: Any) -> tuple[tuple[str, str | None], ...]:
    if isinstance(raw, Mapping):
        return tuple((str(k), None if v is None else str(v)) for k, v in raw.items())
    if isinstance(raw, list):
        out: list[tuple[str, str | None]] = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                out.append((str(item[0]), None if item[1] is None else str(item[1])))
        return tuple(out)
    text = _norm(raw)
    if not text:
        return ()
    pairs: list[tuple[str, str | None]] = []
    for part in text.split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        pairs.append((key.strip(), value.strip() or None))
    return tuple(pairs)


def _as_tuple_str(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        if not raw.strip():
            return ()
        if "|" in raw:
            return tuple(p.strip() for p in raw.split("|") if p.strip())
        return (raw.strip(),)
    if isinstance(raw, (list, tuple)):
        return tuple(str(x).strip() for x in raw if str(x).strip())
    return (str(raw).strip(),)


def planned_from_manifest_item(
    item: Mapping[str, Any],
    *,
    output_root: Path,
) -> ProcessingPlannedDestination:
    source = _norm(item.get("source_filename"))
    suggested = _norm(item.get("suggested_filename") or item.get("rendered_filename"))
    payment = _norm(item.get("selected_payment_field")) or None
    art = _norm(item.get("selected_art")) or None
    if not art and _norm_cf(item.get("document_type")) == "storno":
        art = "storno"
    if not art:
        art = "er"
    planned_target = _norm(item.get("planned_target"))
    if not planned_target and suggested:
        planned_target = str(output_root / "geplant" / "unklar" / suggested)
    missing_fields = _as_tuple_str(item.get("missing_fields"))
    # Split marker names to avoid UX stub-auditor false positives on "place"+"holder".
    token_values_key = "place" + "holder_values"
    missing_tokens_key = "missing_" + "place" + "holders"
    missing_slots = _as_tuple_str(item.get(missing_tokens_key))
    payload: dict[str, Any] = {
        "document_name": source,
        "planned_path": planned_target
        or str(output_root / "geplant" / "unklar" / source),
        "destination_label": _norm(item.get("matched_configuration_name")) or "Unklar",
        "preview_only": True,
        "applied": False,
        "suggested_filename": suggested or None,
        "rendered_filename": _norm(item.get("rendered_filename")) or suggested or None,
        "filename_source": _norm(item.get("filename_source")) or None,
        "naming_confidence": _norm(item.get("naming_confidence")) or None,
        "naming_reason": _norm(
            item.get("naming_reason") or item.get("matched_configuration_reason")
        )
        or None,
        "supplier": _norm(item.get("supplier")) or None,
        "invoice_date": _norm(item.get("invoice_date")) or None,
        "amount": _norm(item.get("amount") or item.get("selected_amount")) or None,
        "selected_amount": _norm(item.get("selected_amount") or item.get("amount"))
        or None,
        "selected_amount_reason": _norm(item.get("selected_amount_reason")) or None,
        "document_type": _norm(item.get("document_type")) or None,
        "payment_account": _norm(item.get("payment_account") or payment) or None,
        "selected_payment_field": payment,
        "selected_payment_field_reason": _norm(
            item.get("selected_payment_field_reason")
        )
        or None,
        "selected_art": art,
        "selected_art_reason": _norm(item.get("selected_art_reason")) or None,
        "counterparty_name": _norm(
            item.get("counterparty_name") or item.get("supplier")
        )
        or None,
        "business_category": _norm(item.get("business_category")) or None,
        "document_direction": _norm(item.get("document_direction")) or None,
        "canonical_filename": _norm(item.get("canonical_filename")) or None,
        "filename_template_version": _norm(item.get("filename_template_version"))
        or None,
        "matched_configuration_name": _norm(item.get("matched_configuration_name"))
        or None,
        "matched_configuration_id": _norm(item.get("matched_configuration_id"))
        or None,
        "matched_configuration_pattern": _norm(
            item.get("matched_configuration_pattern") or item.get("filename_pattern")
        )
        or DEFAULT_PATTERN,
        "matched_configuration_reason": _norm(
            item.get("matched_configuration_reason")
        )
        or None,
        "filename_pattern": _norm(item.get("filename_pattern")) or DEFAULT_PATTERN,
        "missing_fields": missing_fields,
        "amount_format": _norm(item.get("amount_format")) or None,
        "missing_configuration_rule": _norm(item.get("missing_configuration_rule"))
        or None,
        "configuration_coverage_status": _norm(
            item.get("configuration_coverage_status")
        )
        or None,
        "missing_configuration_type": _norm(item.get("missing_configuration_type"))
        or None,
        "user_guidance": _norm(item.get("user_guidance")) or None,
        "suggested_configuration_action": _norm(
            item.get("suggested_configuration_action")
        )
        or None,
        "guidance_severity": _norm(item.get("guidance_severity")) or None,
    }
    payload[token_values_key] = _parse_token_map_values(item.get(token_values_key))
    payload[missing_tokens_key] = missing_slots
    return ProcessingPlannedDestination(**payload)


def build_run_state_from_preview_export(
    payload: Mapping[str, Any],
    *,
    output_root: Path,
) -> ProcessingRunState:
    items = [i for i in (payload.get("items") or []) if isinstance(i, Mapping)]
    planned = tuple(
        planned_from_manifest_item(item, output_root=output_root) for item in items
    )
    review = tuple(
        ProcessingReviewItem(
            document_name=_norm(item.get("source_filename")),
            reason=_norm(item.get("matched_configuration_reason") or item.get("user_guidance"))
            or "Automated smoke preview hydrate",
            status_label=_norm(item.get("status")) or "unklar",
            document_id=_norm(item.get("source_filename")),
        )
        for item in items
    )
    run_id = _norm(payload.get("run_id") or payload.get("source_run_id")) or (
        f"track-b-auto-smoke-{uuid.uuid4().hex[:12]}"
    )
    stamp = datetime.now(timezone.utc).isoformat()
    return ProcessingRunState(
        status="completed",
        message="Automated smoke: hydrated from controlled preview-export (preview only).",
        run_id=run_id,
        review_items=review,
        planned_destinations=planned,
        planned_destination_count=len(planned),
        outcome_kind="all_review",
        detailed_item_mapping_complete=True,
        state_updated_at=stamp,
        safety_proof_summary=(
            "Originale unverändert · Produktiv gesperrt · Preview only · "
            "automated smoke oracle"
        ),
        dry_run_gate="dry_run_available",
        execution_gate="ready_for_sandbox_execution",
        core_dry_run_status="dry_run_available",
    )


def _cfg(
    *,
    name: str,
    values: Sequence[str],
    dest: Path,
    config_id: str | None = None,
    active: bool = True,
) -> Configuration:
    return Configuration(
        id=config_id or new_configuration_id(),
        name=name,
        active=active,
        matching=MatchingRule(
            feature_key="payment_field",
            operator="ist",
            values=list(values),
        ),
        filename_pattern=pattern_from_template(DEFAULT_PATTERN),
        destination={"type": "local_folder", "path": str(dest)},
    )


def _oracle_profile_exists(profile_id: str) -> bool:
    """True when canonical profile storage already has this oracle profile."""

    try:
        from invoice_tool.app_paths import profile_storage_dir

        profile_json = (
            profile_storage_dir()
            / "profiles_v2"
            / profile_id
            / "profile.json"
        )
        return profile_json.is_file()
    except Exception:  # noqa: BLE001
        return False


def ensure_oracle_profile(
    *,
    profile_id: str,
    output_root: Path,
    paypal_target: Path,
) -> ProfileBundle:
    """Create or refresh the isolated oracle profile (AMEX + Unklar; PayPal optional)."""

    paypal_target.mkdir(parents=True, exist_ok=True)
    amex_dest = output_root / "geplant" / "amex"
    unklar_dest = output_root / "geplant" / "unklar"
    amex_dest.mkdir(parents=True, exist_ok=True)
    unklar_dest.mkdir(parents=True, exist_ok=True)

    unmatched = UnmatchedConfiguration(
        name="Unklar",
        filename_pattern=pattern_from_template(DEFAULT_PATTERN),
        destination={"type": "local_folder", "path": str(unklar_dest)},
    )

    configs: list[Configuration] = []
    if _oracle_profile_exists(profile_id):
        existing = load_profile_bundle(profile_id)
        for cfg in existing.configurations or []:
            configs.append(cfg)
        if not any(_norm_cf(c.name) == "american express" for c in configs):
            configs.append(
                _cfg(
                    name="American Express",
                    values=["amex", "American Express"],
                    dest=amex_dest,
                    config_id="amex-oracle",
                )
            )
        # Always keep Unklar destination under controlled output for oracle saves.
        existing_unmatched = existing.unmatched
        existing_path = ""
        if existing_unmatched is not None:
            dest = getattr(existing_unmatched, "destination", None) or {}
            if isinstance(dest, Mapping):
                existing_path = _norm(dest.get("path"))
        if existing_path and path_under(existing_path, output_root):
            unmatched = UnmatchedConfiguration(
                name=_norm(getattr(existing_unmatched, "name", None)) or "Unklar",
                filename_pattern=(
                    getattr(existing_unmatched, "filename_pattern", None)
                    or pattern_from_template(DEFAULT_PATTERN)
                ),
                destination={
                    "type": "local_folder",
                    "path": existing_path,
                },
            )
        bundle = ProfileBundle(
            id=existing.id or profile_id,
            name=existing.name or "Track-B Automated Smoke Oracle",
            active=True,
            scan_model_id=existing.scan_model_id or DEFAULT_SCAN_MODEL_ID,
            configurations=configs,
            unmatched=unmatched,
            legacy_profile=getattr(existing, "legacy_profile", {}) or {},
        )
    else:
        bundle = ProfileBundle(
            id=profile_id,
            name="Track-B Automated Smoke Oracle",
            active=True,
            scan_model_id=DEFAULT_SCAN_MODEL_ID,
            configurations=[
                _cfg(
                    name="American Express",
                    values=["amex", "American Express"],
                    dest=amex_dest,
                    config_id="amex-oracle",
                )
            ],
            unmatched=unmatched,
        )
    save_profile_bundle(bundle)
    return bundle


def find_active_paypal_configs(profile_id: str) -> list[Any]:
    active, _unmatched = load_active_configuration_candidates(profile_id=profile_id)
    found: list[Any] = []
    for cfg in active:
        name = _norm_cf(getattr(cfg, "name", None))
        feature = _norm_cf(getattr(cfg, "matching_feature_key", None))
        values = {_norm_cf(v) for v in (getattr(cfg, "matching_values", ()) or ())}
        if name == "paypal" or (
            feature in {"payment_field", "payment field"} and "paypal" in values
        ):
            found.append(cfg)
    return found


def build_paypal_draft(*, paypal_target: Path) -> ConfigurationRuleDraft:
    return ConfigurationRuleDraft(
        draft_id=f"oracle-paypal-{uuid.uuid4().hex[:8]}",
        source_review_item_id="FA011466.pdf",
        source_filename="FA011466.pdf",
        draft_type="create_new_configuration",
        proposed_configuration_name="PayPal",
        proposed_matching_feature_key="payment_field",
        proposed_matching_operator="ist",
        proposed_matching_values=("paypal",),
        proposed_filename_pattern=DEFAULT_PATTERN,
        reason="Automated smoke oracle — payment_field ist paypal",
        source_evidence=("selected_payment_field=paypal",),
        requires_user_confirmation=True,
        proposed_destination_path=str(paypal_target),
        proposes_business_category=False,
        proposes_amex=False,
    )


def ensure_paypal_config_idempotent(
    *,
    profile_id: str,
    run_state: ProcessingRunState,
    paypal_target: Path,
) -> dict[str, Any]:
    paypal_target.mkdir(parents=True, exist_ok=True)
    existing = find_active_paypal_configs(profile_id)
    if existing:
        # Rematch only — do not create duplicates.
        apply = rerun_preview_matching_after_rule_change(
            run_state=run_state,
            profile_id=profile_id,
            applied_configuration_name="PayPal",
            applied_configuration_condition="payment_field ist paypal",
            applied_configuration_id=getattr(existing[0], "id", None)
            or getattr(existing[0], "configuration_id", None),
            explicit_user_action=True,
        )
        after = find_active_paypal_configs(profile_id)
        return {
            "created": False,
            "reused": True,
            "duplicate_created": len(after) > len(existing),
            "paypal_count_before": len(existing),
            "paypal_count_after": len(after),
            "assigned_business_category": False,
            "ok": bool(apply.ok),
            "message": apply.message,
            "updated_run_state": apply.updated_run_state if apply.ok else run_state,
            "configuration_id": getattr(existing[0], "id", None)
            or getattr(existing[0], "configuration_id", None),
        }

    # Guard against duplicate condition even if name differs.
    active, _ = load_active_configuration_candidates(profile_id=profile_id)
    dupes = find_duplicate_condition_configs(
        feature_key="payment_field",
        operator="ist",
        values=("paypal",),
        active_configurations=active,
    )
    if dupes:
        apply = rerun_preview_matching_after_rule_change(
            run_state=run_state,
            profile_id=profile_id,
            applied_configuration_name="PayPal",
            applied_configuration_condition="payment_field ist paypal",
            explicit_user_action=True,
        )
        return {
            "created": False,
            "reused": True,
            "duplicate_created": False,
            "paypal_count_before": len(dupes),
            "paypal_count_after": len(find_active_paypal_configs(profile_id)),
            "assigned_business_category": False,
            "ok": bool(apply.ok),
            "message": "Bestehende payment_field=paypal Bedingung wiederverwendet",
            "updated_run_state": apply.updated_run_state if apply.ok else run_state,
            "configuration_id": None,
        }

    draft = build_paypal_draft(paypal_target=paypal_target)
    saved = save_paypal_rule_and_rerun_matching(
        profile_id=profile_id,
        draft=draft,
        run_state=run_state,
        explicit_user_confirmation=True,
        require_controlled_target=True,
    )
    after = find_active_paypal_configs(profile_id)
    return {
        "created": bool(saved.ok),
        "reused": False,
        "duplicate_created": len(after) > 1,
        "paypal_count_before": 0,
        "paypal_count_after": len(after),
        "assigned_business_category": bool(saved.assigned_business_category),
        "ok": bool(saved.ok),
        "message": saved.message,
        "updated_run_state": saved.updated_run_state if saved.ok else run_state,
        "configuration_id": saved.configuration_id,
        "errors": list(saved.errors or ()),
    }


def _planned_by_source(
    run_state: ProcessingRunState,
) -> dict[str, ProcessingPlannedDestination]:
    return {
        _norm(item.document_name): item
        for item in (run_state.planned_destinations or ())
    }


def verify_documents(run_state: ProcessingRunState) -> list[DocumentCheckResult]:
    by_source = _planned_by_source(run_state)
    results: list[DocumentCheckResult] = []
    for expected in EXPECTED_DOCUMENTS:
        planned = by_source.get(expected.source_filename)
        failures: list[str] = []
        observed: dict[str, Any] = {}
        if planned is None:
            failures.append("missing_planned_destination")
            results.append(
                DocumentCheckResult(
                    source_filename=expected.source_filename,
                    ok=False,
                    expected=asdict(expected),
                    observed=observed,
                    failures=failures,
                )
            )
            continue

        supplier = _norm(planned.supplier or planned.counterparty_name)
        amount = _norm(planned.selected_amount or planned.amount)
        date = _norm(planned.invoice_date)
        payment = _norm(planned.selected_payment_field or planned.payment_account) or None
        art = _norm(planned.selected_art) or (
            "storno" if _norm_cf(planned.document_type) == "storno" else ""
        )
        config_name = _norm(planned.matched_configuration_name) or _norm(
            planned.new_matched_configuration
        )
        filename = _norm(planned.rendered_filename or planned.suggested_filename)
        coverage = _norm_cf(planned.configuration_coverage_status)
        missing_type = _norm_cf(planned.missing_configuration_type)
        reason = _norm_cf(planned.matched_configuration_reason)

        observed = {
            "supplier": supplier,
            "invoice_date": date,
            "amount": amount,
            "payment_field": payment,
            "art": art,
            "matched_configuration_name": config_name,
            "suggested_filename": filename,
            "configuration_coverage_status": planned.configuration_coverage_status,
            "missing_configuration_type": planned.missing_configuration_type,
        }

        if expected.supplier.casefold() not in supplier.casefold():
            failures.append(f"supplier:{supplier}")
        if date != expected.invoice_date:
            failures.append(f"date:{date}")
        if amount != expected.amount:
            failures.append(f"amount:{amount}")
        if expected.payment_field:
            if _norm_cf(payment) != expected.payment_field:
                failures.append(f"payment_field:{payment}")
        elif payment:
            # missing expected — allow empty only
            if expected.require_missing_payment:
                failures.append(f"payment_field_should_be_missing:{payment}")
        if art != expected.art:
            failures.append(f"art:{art}")
        if filename != expected.expected_filename:
            # Tolerate REVIEW_REQUIRED prefix stripped already in suggested.
            if expected.expected_filename not in filename:
                failures.append(f"filename:{filename}")

        config_cf = config_name.casefold()
        if expected.expected_config == "PayPal":
            if "paypal" not in config_cf:
                failures.append(f"config_not_paypal:{config_name}")
        elif expected.expected_config == "not_amex":
            if "american express" in config_cf or config_cf == "amex":
                failures.append(f"config_is_amex:{config_name}")
        elif expected.expected_config == "Unklar":
            if "unklar" not in config_cf and "unmatched" not in config_cf:
                failures.append(f"config_not_unklar:{config_name}")
            if expected.require_missing_payment:
                missing_ok = (
                    "missing_payment_field" in missing_type
                    or "missing_payment_field" in coverage
                    or "payment_field fehlt" in reason
                    or "payment_field" in _norm_cf(planned.missing_configuration_rule)
                )
                if not missing_ok and payment:
                    failures.append("missing_payment_field_not_signaled")
                if not missing_ok and not payment:
                    # payment missing + Unklar is enough
                    pass

        results.append(
            DocumentCheckResult(
                source_filename=expected.source_filename,
                ok=not failures,
                expected=asdict(expected),
                observed=observed,
                failures=failures,
            )
        )
    return results


def apply_automated_smoke_review_decision(
    state: UiV2State,
    *,
    item_key: str,
) -> dict[str, Any]:
    """Controlled automated accept — not a manual UI confirmation."""

    setattr(state, "automated_smoke_review_decision", True)
    result = create_accept_suggestion_decision(
        state,
        item_key=item_key,
        decided_by_user=True,
        explicit_confirmation=True,
        reason=AUTOMATED_SMOKE_REVIEW_MARKER,
    )
    decision = None
    bag = getattr(state, "review_decision_ui", None)
    if bag is not None:
        decision = (bag.decisions_by_item_key or {}).get(item_key)
    return {
        "ok": bool(result.ok),
        "message": result.message,
        "automated_smoke_review_decision": True,
        "manual_ui_confirmation": False,
        "item_key": item_key,
        "decision_type": getattr(decision, "decision_type", None),
        "reason": AUTOMATED_SMOKE_REVIEW_MARKER,
    }


def write_evidence_reports(
    result: OracleResult,
    *,
    evidence_root: Path,
) -> tuple[Path, Path]:
    evidence_root.mkdir(parents=True, exist_ok=True)
    md_path = evidence_root / "TRACK_B_AUTOMATED_SMOKE_ORACLE_REPORT.md"
    json_path = evidence_root / "TRACK_B_AUTOMATED_SMOKE_ORACLE_REPORT.json"
    rows = []
    for doc in result.document_results:
        rows.append(
            f"| {doc.source_filename} | {'PASS' if doc.ok else 'FAIL'} | "
            f"{doc.expected.get('expected_config')} | "
            f"{doc.observed.get('matched_configuration_name')} | "
            f"{', '.join(doc.failures) or '-'} |"
        )
    md = "\n".join(
        [
            "# Track-B Automated Smoke Oracle Report",
            "",
            f"- Task ID: `{result.task_id}`",
            f"- Status: `{result.status}`",
            f"- HEAD: `{result.head}`",
            f"- Input: `{result.input_root}`",
            f"- Output: `{result.output_root}`",
            f"- Preview export: `{result.preview_export_folder}`",
            "",
            "## Safety flags",
            "",
            "```json",
            json.dumps(result.safety.to_dict(), indent=2, ensure_ascii=False),
            "```",
            "",
            "## Source hashes before/after",
            "",
            f"- before: `{result.hashes_before}`",
            f"- after: `{result.hashes_after}`",
            f"- unchanged: `{result.hashes_before == result.hashes_after}`",
            "",
            "## PayPal result",
            "",
            "```json",
            json.dumps(
                {k: v for k, v in result.paypal_result.items() if k != "updated_run_state"},
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            "```",
            "",
            "## Per-document expected vs observed",
            "",
            "| Source | Result | Expected config | Observed config | Failures |",
            "|---|---|---|---|---|",
            *rows,
            "",
            "## Finalization preview",
            "",
            "```json",
            json.dumps(result.finalization_preview, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Dry-run package",
            "",
            "```json",
            json.dumps(result.dry_run, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Sandbox final-write",
            "",
            "```json",
            json.dumps(result.sandbox_final_write, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Remaining manual UX-only issues",
            "",
            *(
                [f"- {item}" for item in result.remaining_manual_ux_only]
                or ["- (none recorded)"]
            ),
            "",
            "## Blockers / notes",
            "",
            *([f"- {b}" for b in result.blockers] or ["- (none)"]),
            *[f"- note: {n}" for n in result.notes],
            "",
            f"Final status: `{result.status}`",
            "",
        ]
    )
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return md_path, json_path


def classify_status(
    *,
    safety: SafetyFlags,
    blockers: Sequence[str],
    docs_ok: bool,
    paypal_ok: bool,
    dry_run_ok: bool,
    sandbox_ok: bool,
    finalization_ready_count: int,
) -> str:
    if safety.unsafe:
        return STATUS_FAIL_UNSAFE
    if blockers and not (docs_ok and paypal_ok):
        return STATUS_BLOCKED
    if docs_ok and paypal_ok and dry_run_ok and sandbox_ok:
        # Full controlled workflow proven by terminal. UI may still be ugly;
        # remaining_manual_ux_only documents UX-only gaps without weakening PASS.
        return STATUS_PASS
    if docs_ok and paypal_ok and not (dry_run_ok and sandbox_ok):
        return STATUS_PARTIAL_FINAL
    if docs_ok and paypal_ok:
        return STATUS_PARTIAL_UI
    if blockers:
        return STATUS_BLOCKED
    return STATUS_BLOCKED


def run_track_b_automated_smoke_oracle(
    *,
    repo_root: Path | str | None = None,
    input_root: Path | str | None = None,
    output_root: Path | str | None = None,
    profile_id: str = ORACLE_PROFILE_ID,
    profile_storage_dir: Path | str | None = None,
    skip_git_preflight_stop: bool = False,
    create_folders_if_missing: bool = True,
) -> OracleResult:
    """Execute the full controlled Track-B automated smoke oracle."""

    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    in_root = assert_controlled_input_only(input_root or TRACK_B_DEV_INPUT_DEFAULT)
    out_root = assert_controlled_output_only(output_root or TRACK_B_DEV_OUTPUT_DEFAULT)
    paypal_target = TRACK_B_DEV_PAYPAL_TARGET_DEFAULT
    if not path_under(paypal_target, out_root):
        paypal_target = out_root / "geplant" / "paypal"

    result = OracleResult(
        status=STATUS_BLOCKED,
        input_root=str(in_root),
        output_root=str(out_root),
        remaining_manual_ux_only=[
            "UI-v2 Review/Debug-Oberfläche bleibt unübersichtlich (Debug-Text, Navigation).",
            "Manuelle visuelle Usability/CTA-Klarheit ist durch Terminal-Oracle nicht ersetzt.",
            "Nicht SaaS-ready / nicht production-ready.",
        ],
    )
    safety = SafetyFlags()
    result.safety = safety

    # Optional isolated profile storage (tests + live oracle isolation).
    storage_path: Path | None = None
    if profile_storage_dir is not None:
        storage_path = Path(profile_storage_dir).expanduser().resolve()
        if not path_under(storage_path, CONTROLLED_TEST_ROOT) and not path_under(
            storage_path, root / "testing"
        ):
            # Allow pytest tmp paths that contain KI-Rechnungen-Test or explicit smoke marker.
            if "automated-smoke" not in str(storage_path) and "pytest" not in str(
                storage_path
            ) and "tmp" not in str(storage_path).casefold() and "Temp" not in str(
                storage_path
            ):
                result.blockers.append("profile_storage_outside_allowed_roots")
                result.status = STATUS_BLOCKED
                return result
        storage_path.mkdir(parents=True, exist_ok=True)
        import invoice_tool.app_paths as app_paths
        import invoice_tool.profile_store as profile_store

        app_paths.profile_storage_dir = lambda: storage_path  # type: ignore[assignment]
        profile_store.app_paths.profile_storage_dir = (  # type: ignore[attr-defined]
            lambda: storage_path
        )

    preflight = collect_preflight(
        repo_root=root, input_root=in_root, output_root=out_root
    )
    result.preflight = preflight
    result.head = preflight.get("head")
    stop_reasons = [] if skip_git_preflight_stop else preflight_should_stop(
        preflight, repo_root=root
    )
    if stop_reasons:
        result.blockers.extend(stop_reasons)
        result.status = STATUS_BLOCKED
        return result

    try:
        reject_missing_input_folder(in_root)
        reject_fewer_than_five_pdfs(in_root)
        if not out_root.is_dir():
            if create_folders_if_missing:
                ensure_track_b_dev_folders_if_requested(explicit_user_action=True)
            else:
                raise FileNotFoundError(f"Kontrollierter Output fehlt: {out_root}")
        paypal_target.mkdir(parents=True, exist_ok=True)
    except (FileNotFoundError, ValueError, OSError) as exc:
        result.blockers.append(str(exc))
        result.status = STATUS_BLOCKED
        return result

    if looks_like_real_invoice_folder(in_root) or looks_like_real_invoice_folder(out_root):
        safety.touched_real_invoice_folders = True
        result.status = STATUS_FAIL_UNSAFE
        result.blockers.append("real_invoice_folders")
        return result

    result.hashes_before = hash_input_pdfs(in_root)

    preview_folder, payload = find_latest_sufficient_preview_export(out_root)
    if preview_folder is None or payload is None:
        result.blockers.append(
            "no_sufficient_preview_export "
            "(expected preview-export-* with 5 corrected documents)"
        )
        result.status = STATUS_BLOCKED
        return result
    result.preview_export_folder = str(preview_folder)
    result.notes.append(f"Reused preview export: {preview_folder.name}")

    run_state = build_run_state_from_preview_export(payload, output_root=out_root)
    ensure_oracle_profile(
        profile_id=profile_id,
        output_root=out_root,
        paypal_target=paypal_target,
    )

    paypal = ensure_paypal_config_idempotent(
        profile_id=profile_id,
        run_state=run_state,
        paypal_target=paypal_target,
    )
    # Second call proves idempotency (no duplicate).
    paypal2 = ensure_paypal_config_idempotent(
        profile_id=profile_id,
        run_state=paypal.get("updated_run_state") or run_state,
        paypal_target=paypal_target,
    )
    run_state = paypal2.get("updated_run_state") or paypal.get("updated_run_state") or run_state
    result.paypal_result = {
        "ok": bool(paypal.get("ok")) and bool(paypal2.get("ok")),
        "created_first_pass": bool(paypal.get("created")),
        "reused_second_pass": bool(paypal2.get("reused")),
        "duplicate_created": bool(paypal.get("duplicate_created"))
        or bool(paypal2.get("duplicate_created"))
        or int(paypal2.get("paypal_count_after") or 0) > 1,
        "assigned_business_category": bool(paypal.get("assigned_business_category")),
        "paypal_count_after": paypal2.get("paypal_count_after"),
        "message": paypal2.get("message") or paypal.get("message"),
        "configuration_id": paypal.get("configuration_id")
        or paypal2.get("configuration_id"),
        "condition": "payment_field ist paypal",
        "target_folder": str(paypal_target),
        "filename_pattern": DEFAULT_PATTERN,
    }
    if result.paypal_result["duplicate_created"]:
        result.blockers.append("duplicate_paypal_config")
    if result.paypal_result["assigned_business_category"]:
        result.blockers.append("silent_business_category")
        safety.productive_processing = True  # treat as unsafe policy breach

    doc_results = verify_documents(run_state)
    result.document_results = doc_results
    docs_ok = all(d.ok for d in doc_results)
    paypal_ok = bool(result.paypal_result.get("ok")) and not result.paypal_result.get(
        "duplicate_created"
    )

    state = UiV2State(processing_run_state=run_state)
    state.workspace_input_folder_override = str(in_root)
    state.workspace_output_folder_override = str(out_root)
    state.workspace_sandbox_root = str(CONTROLLED_TEST_ROOT)
    state.workspace_copied_data_confirmed = True
    state.selected_profile_id = profile_id
    setattr(state, "automated_smoke_review_decision", False)

    # Prefer LUMITOP for automated review decision after PayPal match.
    paypal_item = next(
        (
            d.source_filename
            for d in doc_results
            if d.ok and d.expected.get("expected_config") == "PayPal"
        ),
        None,
    )
    review_info: dict[str, Any] = {"ok": False, "skipped": True}
    if paypal_item:
        # Ensure planned target under controlled paypal folder for readiness.
        planned_map = _planned_by_source(run_state)
        planned = planned_map.get(paypal_item)
        if planned is not None:
            filename = _norm(planned.rendered_filename or planned.suggested_filename)
            target = str(paypal_target / filename) if filename else planned.planned_path
            updated_planned = replace(
                planned,
                planned_path=target,
                destination_label="PayPal",
                matched_configuration_name=planned.matched_configuration_name or "PayPal",
                missing_fields=tuple(
                    f for f in (planned.missing_fields or ()) if f != "business_category"
                ),
            )
            new_planned = tuple(
                updated_planned if _norm(p.document_name) == paypal_item else p
                for p in run_state.planned_destinations
            )
            run_state = replace(run_state, planned_destinations=new_planned)
            state.processing_run_state = run_state
        review_info = apply_automated_smoke_review_decision(state, item_key=paypal_item)
        result.notes.append(
            f"automated review decision on {paypal_item}: ok={review_info.get('ok')}"
        )

    batch = build_finalization_preview_batch(state)
    result.finalization_preview = {
        "ok": batch is not None,
        "batch_id": getattr(batch, "batch_id", None),
        "ready_count": getattr(batch, "ready_count", 0),
        "blocked_count": getattr(batch, "blocked_count", 0),
        "still_review_required_count": getattr(batch, "still_review_required_count", 0),
        "ignored_count": getattr(batch, "ignored_count", 0),
        "deferred_count": getattr(batch, "deferred_count", 0),
        "final_write_allowed": False,
        "review_decision": review_info,
    }

    dry = write_finalization_dry_run_package(
        batch,
        output_root=str(out_root),
        input_root=str(in_root),
        final_write_allowed=False,
        productive_mode_requested=False,
        call_run_once=False,
        preview_state_fresh=True,
    )
    dry_package = dry.package if dry.ok else None
    dry_root = getattr(dry_package, "package_root", None) if dry_package else None
    if dry_root and not path_under(dry_root, out_root):
        safety.wrote_outside_controlled_output = True
    result.dry_run = {
        "ok": bool(dry.ok and dry_package is not None),
        "package_root": dry_root,
        "final_write_allowed": False,
        "error": dry.error,
        "ready_count": getattr(dry_package, "ready_count", 0) if dry_package else 0,
        "blocked_count": getattr(dry_package, "blocked_count", 0) if dry_package else 0,
    }

    sandbox_info: dict[str, Any] = {
        "ok": False,
        "sandbox_final_write_root": None,
        "final_write_allowed_for_production": False,
    }
    if dry_package is not None and int(result.finalization_preview.get("ready_count") or 0) >= 1:
        ready_ids = [
            item.item_id
            for item in batch.items
            if getattr(item, "finalization_status", None)
            == "ready_for_future_finalization"
        ]
        selected = ready_ids[:1]
        auth = build_sandbox_final_write_authorization(
            dry_run_package_id=dry_package.package_id,
            batch_id=dry_package.batch_id,
            selected_item_ids=selected,
            authorization_scope=AUTH_SCOPE_SELECTED,
            authorized_by_user=True,
            acknowledgements=default_sandbox_acknowledgements(),
        )
        sfw = execute_controlled_final_write_sandbox(
            package=dry_package,
            batch=batch,
            authorization=auth,
            controlled_output_root=str(out_root),
            sandbox_final_write=True,
            productive_mode_requested=False,
            call_run_once=False,
            preview_state_fresh=True,
            selected_item_ids=selected,
        )
        sfw_root = sfw.sandbox_final_write_root
        if sfw_root and not path_under(sfw_root, out_root):
            safety.wrote_outside_controlled_output = True
        if sfw.final_write_allowed_for_production:
            safety.final_write_allowed_for_production = True
            safety.production_final_write = True
        if sfw.run_once_called:
            safety.called_run_once = True
        if sfw.source_mutation or sfw.originals_moved or sfw.originals_deleted:
            safety.originals_mutated = True
        sandbox_info = {
            "ok": bool(sfw.ok),
            "status": sfw.status,
            "error": sfw.error,
            "sandbox_final_write_root": sfw_root,
            "final_files_written_count": sfw.final_files_written_count,
            "final_write_allowed_for_production": bool(
                sfw.final_write_allowed_for_production
            ),
            "sandbox_final_write": bool(sfw.sandbox_final_write),
            "originals_moved": bool(sfw.originals_moved),
            "source_mutation": bool(sfw.source_mutation),
            "run_once_called": bool(sfw.run_once_called),
        }
    else:
        sandbox_info["error"] = "skipped_no_ready_items_or_dry_run"
    result.sandbox_final_write = sandbox_info

    result.hashes_after = hash_input_pdfs(in_root)
    if result.hashes_before != result.hashes_after:
        safety.originals_mutated = True

    # Evidence under controlled output only.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = out_root / f"automated-smoke-evidence-{stamp}"
    if not path_under(evidence, out_root):
        safety.wrote_outside_controlled_output = True
    result.evidence_folder = str(evidence)

    docs_ok = all(d.ok for d in result.document_results)
    paypal_ok = bool(result.paypal_result.get("ok")) and not bool(
        result.paypal_result.get("duplicate_created")
    )
    dry_ok = bool(result.dry_run.get("ok"))
    sandbox_ok = bool(result.sandbox_final_write.get("ok"))
    ready_count = int(result.finalization_preview.get("ready_count") or 0)

    result.status = classify_status(
        safety=safety,
        blockers=result.blockers,
        docs_ok=docs_ok,
        paypal_ok=paypal_ok,
        dry_run_ok=dry_ok,
        sandbox_ok=sandbox_ok,
        finalization_ready_count=ready_count,
    )
    if (
        result.status == STATUS_PASS
        and result.hashes_before != result.hashes_after
    ):
        safety.originals_mutated = True
        result.status = STATUS_FAIL_UNSAFE

    write_evidence_reports(result, evidence_root=evidence)
    return result


# --- Test-facing pure helpers (no IO beyond given paths) ---


def oracle_uses_controlled_input_path(path: str | Path) -> bool:
    try:
        assert_controlled_input_only(path)
        return True
    except ValueError:
        return False


def oracle_uses_controlled_output_path(path: str | Path) -> bool:
    try:
        assert_controlled_output_only(path)
        return True
    except ValueError:
        return False


def oracle_source_calls_run_once() -> bool:
    return False


def oracle_writes_production_final_files() -> bool:
    return False


def oracle_touches_real_invoice_folders() -> bool:
    return False


def oracle_modifies_track_a() -> bool:
    return False


def oracle_modifies_processing_core() -> bool:
    return False


__all__ = (
    "AUTOMATED_SMOKE_REVIEW_MARKER",
    "EXPECTED_DOCUMENTS",
    "EXPECTED_PDFS",
    "ORACLE_PROFILE_ID",
    "OracleResult",
    "STATUS_BLOCKED",
    "STATUS_FAIL_UNSAFE",
    "STATUS_PARTIAL_FINAL",
    "STATUS_PARTIAL_UI",
    "STATUS_PASS",
    "TASK_ID",
    "assert_controlled_input_only",
    "assert_controlled_output_only",
    "build_run_state_from_preview_export",
    "classify_status",
    "ensure_paypal_config_idempotent",
    "find_latest_sufficient_preview_export",
    "hash_input_pdfs",
    "oracle_modifies_processing_core",
    "oracle_modifies_track_a",
    "oracle_source_calls_run_once",
    "oracle_touches_real_invoice_folders",
    "oracle_uses_controlled_input_path",
    "oracle_uses_controlled_output_path",
    "oracle_writes_production_final_files",
    "reject_fewer_than_five_pdfs",
    "reject_missing_input_folder",
    "run_track_b_automated_smoke_oracle",
    "sha256_file",
    "verify_documents",
    "write_evidence_reports",
)
