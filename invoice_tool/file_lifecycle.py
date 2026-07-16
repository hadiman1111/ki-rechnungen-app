"""RUN-001 file lifecycle: atomic output, mapping, path safety, recovery."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invoice_tool.state import fingerprint_file

# ---------------------------------------------------------------------------
# Lifecycle statuses
# ---------------------------------------------------------------------------

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_OUTPUT_WRITTEN = "output_written"
STATUS_OUTPUT_VERIFIED = "output_verified"
STATUS_SUCCESS = "success"
STATUS_DUPLICATE = "duplicate"
STATUS_COLLISION_RENAMED = "collision_renamed"
STATUS_OUTPUT_FAILED = "output_failed"
STATUS_VERIFICATION_FAILED = "verification_failed"
STATUS_ARCHIVE_FAILED = "archive_failed"
STATUS_INTERRUPTED = "interrupted"
STATUS_RECOVERY_REQUIRED = "recovery_required"

SUCCESS_STATUSES = frozenset({STATUS_SUCCESS, STATUS_COLLISION_RENAMED})
FAILURE_STATUSES = frozenset({
    STATUS_OUTPUT_FAILED,
    STATUS_VERIFICATION_FAILED,
    STATUS_ARCHIVE_FAILED,
    STATUS_INTERRUPTED,
    STATUS_RECOVERY_REQUIRED,
})

APP_TEMP_PREFIX = "."
APP_TEMP_SUFFIX = ".tmp"
RECOVERY_FILENAME = "recovery_records.json"
MAPPING_FILENAME = "output_mapping.json"
MAPPING_TEMP_FILENAME = ".output_mapping.json.tmp"

_MAX_FILENAME_BYTES = 200
_UNSAFE_FILENAME_CHARS = re.compile(r"[/\x00-\x1f]")
_COLLISION_SUFFIX_RE = re.compile(r"__(\d+)$")

# Optional test hook: set to a lifecycle phase name to simulate interruption.
INTERRUPT_AFTER: str | None = None


class LifecycleError(RuntimeError):
    def __init__(self, message: str, *, code: str, status: str) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class PathSafetyError(LifecycleError):
    pass


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_meta(path: Path) -> tuple[str, int]:
    digest = fingerprint_file(path)
    return digest, path.stat().st_size


# ---------------------------------------------------------------------------
# Path and filename safety
# ---------------------------------------------------------------------------

def path_is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def validate_input_output_roots(source: Path, output: Path) -> None:
    """Reject overlapping input/output roots before processing."""
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise PathSafetyError(
            f"source und output dürfen nicht identisch sein: {source}",
            code="input_output_equal",
            status=STATUS_OUTPUT_FAILED,
        )
    if path_is_within(source, output):
        raise PathSafetyError(
            f"source darf nicht innerhalb von output liegen: source={source}, output={output}",
            code="source_inside_output",
            status=STATUS_OUTPUT_FAILED,
        )
    if path_is_within(output, source):
        raise PathSafetyError(
            f"output darf nicht innerhalb von source liegen: source={source}, output={output}",
            code="output_inside_source",
            status=STATUS_OUTPUT_FAILED,
        )


def resolve_safe_target_directory(output_root: Path, relative_folder: str) -> Path:
    """Resolve a relative routing folder contained within output_root."""
    if not relative_folder or not str(relative_folder).strip():
        raise PathSafetyError(
            "Zielordner ist leer oder ungültig",
            code="invalid_target_directory",
            status=STATUS_OUTPUT_FAILED,
        )
    folder = str(relative_folder).strip().replace("\\", "/")
    if folder.startswith("/") or ":" in folder:
        raise PathSafetyError(
            f"Absoluter Zielordner nicht erlaubt: {relative_folder}",
            code="absolute_target_rejected",
            status=STATUS_OUTPUT_FAILED,
        )
    parts = Path(folder).parts
    for part in parts:
        if part in ("", ".", ".."):
            raise PathSafetyError(
                f"Pfad-Traversal im Zielordner abgelehnt: {relative_folder}",
                code="path_traversal",
                status=STATUS_OUTPUT_FAILED,
            )
    target = (output_root / Path(*parts)).resolve()
    if not path_is_within(target, output_root.resolve()):
        raise PathSafetyError(
            f"Zielordner liegt außerhalb des Output-Roots: {target}",
            code="path_escape",
            status=STATUS_OUTPUT_FAILED,
        )
    return target


def sanitize_final_filename(name: str, *, max_bytes: int = _MAX_FILENAME_BYTES) -> str:
    """Sanitize a final PDF filename for safe filesystem use."""
    raw = (name or "").strip()
    if not raw:
        raw = "dokument.pdf"
    if not raw.lower().endswith(".pdf"):
        raw = f"{raw}.pdf"

    stem, suffix = raw[:-4], ".pdf"
    stem = _UNSAFE_FILENAME_CHARS.sub("_", stem)
    stem = stem.replace("..", "_")
    stem = re.sub(r"_+", "_", stem).strip("._ ")
    if not stem or stem in {".", ".."}:
        stem = "dokument"

    encoded = stem.encode("utf-8")
    if len(encoded) > max_bytes:
        digest = hashlib.sha256(stem.encode("utf-8")).hexdigest()[:8]
        budget = max_bytes - len(digest) - 2
        truncated = encoded[:budget].decode("utf-8", errors="ignore").rstrip("._ ")
        stem = f"{truncated or 'dokument'}_{digest}"

    return f"{stem}{suffix}"


def validate_input_file_safety(path: Path, input_root: Path) -> None:
    """Reject input files that escape the configured input root via symlinks."""
    input_root = input_root.resolve()
    if path.is_symlink():
        target = path.resolve()
        if not path_is_within(target, input_root):
            raise PathSafetyError(
                f"Symlink-Eingabe zeigt außerhalb des Input-Roots: {path} -> {target}",
                code="symlink_escape_input",
                status=STATUS_OUTPUT_FAILED,
            )
        return
    resolved = path.resolve()
    if not path_is_within(resolved, input_root):
        raise PathSafetyError(
            f"Eingabedatei liegt außerhalb des Input-Roots: {resolved}",
            code="input_outside_root",
            status=STATUS_OUTPUT_FAILED,
        )


def validate_output_directory_safety(target_dir: Path, output_root: Path) -> None:
    """Ensure the resolved output directory remains inside output_root."""
    output_root = output_root.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    real_dir = target_dir.resolve()
    if not path_is_within(real_dir, output_root):
        raise PathSafetyError(
            f"Output-Ziel liegt außerhalb des Output-Roots: {real_dir}",
            code="symlink_escape_output",
            status=STATUS_OUTPUT_FAILED,
        )


def is_application_temp_file(path: Path) -> bool:
    name = path.name
    return name.startswith(APP_TEMP_PREFIX) and name.endswith(APP_TEMP_SUFFIX)


def should_ignore_input_path(path: Path, *, archive_dirname: str = "archiv") -> bool:
    parts = path.parts
    if archive_dirname in parts:
        return True
    if path.name == "input_snapshot":
        return True
    if is_application_temp_file(path):
        return True
    if path.name in {MAPPING_FILENAME, RECOVERY_FILENAME, MAPPING_TEMP_FILENAME}:
        return True
    return False


# ---------------------------------------------------------------------------
# Collision-safe destination resolution
# ---------------------------------------------------------------------------

def collision_safe_path(base_path: Path, *, start_index: int = 2) -> Path:
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    index = start_index
    while True:
        candidate = base_path.with_name(f"{stem}__{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def resolve_output_destination(
    target_dir: Path,
    desired_filename: str,
    *,
    content_hash: str,
) -> tuple[Path, str, str]:
    """Choose a non-conflicting final path based on existing file content.

    Returns:
        (final_path, lifecycle_status, output_action)
    """
    desired_path = target_dir / desired_filename
    if not desired_path.exists():
        return desired_path, STATUS_PROCESSING, "new"

    existing_hash, _ = _file_meta(desired_path)
    if existing_hash == content_hash:
        return desired_path, STATUS_DUPLICATE, "duplicate_existing"

    alternate = collision_safe_path(desired_path)
    return alternate, STATUS_COLLISION_RENAMED, "collision_renamed"


# ---------------------------------------------------------------------------
# Atomic output publication
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PublishResult:
    final_path: Path
    lifecycle_status: str
    output_action: str
    verified: bool
    final_sha256: str | None = None
    final_size: int | None = None
    duplicate_of: Path | None = None


def _temp_output_path(target_dir: Path, final_name: str, run_id: str, item_id: str) -> Path:
    return target_dir / f".{final_name}.{run_id}.{item_id}{APP_TEMP_SUFFIX}"


def verify_output_file(path: Path) -> tuple[str, int]:
    if not path.exists():
        raise LifecycleError(
            f"Output-Verifikation fehlgeschlagen: Datei existiert nicht: {path}",
            code="output_missing",
            status=STATUS_VERIFICATION_FAILED,
        )
    if not path.is_file():
        raise LifecycleError(
            f"Output-Verifikation fehlgeschlagen: kein reguläres File: {path}",
            code="output_not_file",
            status=STATUS_VERIFICATION_FAILED,
        )
    size = path.stat().st_size
    if size <= 0:
        raise LifecycleError(
            f"Output-Verifikation fehlgeschlagen: Dateigröße ist 0: {path}",
            code="output_zero_size",
            status=STATUS_VERIFICATION_FAILED,
        )
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        raise LifecycleError(
            f"Output-Verifikation fehlgeschlagen: Datei nicht lesbar: {path}",
            code="output_unreadable",
            status=STATUS_VERIFICATION_FAILED,
        ) from exc
    return _file_meta(path)


def publish_output_atomically(
    *,
    source_pdf: Path,
    target_dir: Path,
    desired_filename: str,
    content_hash: str,
    run_id: str,
    item_id: str,
    output_root: Path,
    forbid_under: tuple[Path, ...] = (),
    enforce_output_containment: bool = True,
) -> PublishResult:
    """Write processed output via temp file, verify, then publish without overwrite."""
    if enforce_output_containment:
        validate_output_directory_safety(target_dir, output_root)
    safe_name = sanitize_final_filename(desired_filename)
    final_path, lifecycle_status, output_action = resolve_output_destination(
        target_dir,
        safe_name,
        content_hash=content_hash,
    )

    if lifecycle_status == STATUS_DUPLICATE:
        return PublishResult(
            final_path=final_path,
            lifecycle_status=STATUS_DUPLICATE,
            output_action="duplicate_existing",
            verified=False,
            duplicate_of=final_path,
        )

    temp_path = _temp_output_path(target_dir, final_path.name, run_id, item_id)
    if temp_path.exists():
        temp_path.unlink()

    try:
        shutil.copy2(source_pdf, temp_path)
        temp_hash, temp_size = verify_output_file(temp_path)
        if temp_hash != content_hash:
            raise LifecycleError(
                "Output-Verifikation fehlgeschlagen: Hash stimmt nicht überein",
                code="output_hash_mismatch",
                status=STATUS_VERIFICATION_FAILED,
            )

        _maybe_interrupt("output_written")

        if final_path.exists():
            existing_hash, _ = _file_meta(final_path)
            if existing_hash == content_hash:
                temp_path.unlink(missing_ok=True)
                return PublishResult(
                    final_path=final_path,
                    lifecycle_status=STATUS_DUPLICATE,
                    output_action="duplicate_existing",
                    verified=False,
                    duplicate_of=final_path,
                )
            final_path = collision_safe_path(final_path)
            lifecycle_status = STATUS_COLLISION_RENAMED
            output_action = "collision_renamed"

        os.replace(temp_path, final_path)
        final_hash, final_size = verify_output_file(final_path)

        for forbidden in forbid_under:
            if path_is_within(final_path, forbidden.resolve()):
                final_path.unlink(missing_ok=True)
                raise LifecycleError(
                    f"Output-Verifikation fehlgeschlagen: finales Ergebnis liegt in verbotenem Bereich: {final_path}",
                    code="output_forbidden_location",
                    status=STATUS_VERIFICATION_FAILED,
                )

        _maybe_interrupt("output_verified")

        return PublishResult(
            final_path=final_path,
            lifecycle_status=lifecycle_status,
            output_action=output_action,
            verified=True,
            final_sha256=final_hash,
            final_size=final_size,
        )
    except LifecycleError:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise LifecycleError(
            f"Output-Schreiben fehlgeschlagen: {exc}",
            code="output_write_failed",
            status=STATUS_OUTPUT_FAILED,
        ) from exc


def _maybe_interrupt(phase: str) -> None:
    if INTERRUPT_AFTER == phase:
        raise LifecycleError(
            f"Verarbeitung unterbrochen nach {phase}",
            code="interrupted",
            status=STATUS_INTERRUPTED,
        )


# ---------------------------------------------------------------------------
# Archive safety
# ---------------------------------------------------------------------------

def unique_archive_path(archive_dir: Path, filename: str) -> Path:
    candidate = archive_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    index = 2
    while True:
        alt = archive_dir / f"{stem}__{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1


@dataclass(frozen=True)
class SameRunDuplicateArchiveResult:
    success: bool
    archive_path: Path | None
    lifecycle_status: str
    error: str | None = None


def _duplicate_archive_collision_path(archive_dir: Path, filename: str) -> Path:
    candidate = archive_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    index = 2
    while True:
        alt = archive_dir / f"{stem}__duplikat_{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1


def archive_same_run_duplicate(
    *,
    source_path: Path,
    source_root: Path,
    run_id: str,
    expected_hash: str | None = None,
) -> SameRunDuplicateArchiveResult:
    """Move a same-run duplicate under <source_root>/archiv/<run_id>/duplikate/."""
    source_root = source_root.resolve()
    source_path = source_path.resolve()

    if not source_path.exists():
        return SameRunDuplicateArchiveResult(
            success=False,
            archive_path=None,
            lifecycle_status="archive_failed",
            error=f"Quelldatei nicht gefunden: {source_path}",
        )
    if not source_path.is_file():
        return SameRunDuplicateArchiveResult(
            success=False,
            archive_path=None,
            lifecycle_status="archive_failed",
            error=f"Quelle ist keine Datei: {source_path}",
        )
    if not path_is_within(source_path, source_root):
        return SameRunDuplicateArchiveResult(
            success=False,
            archive_path=None,
            lifecycle_status="archive_failed",
            error=f"Quelle liegt ausserhalb des Input-Roots: {source_path}",
        )

    archive_dir = (source_root / "archiv" / run_id / "duplikate").resolve()
    if not path_is_within(archive_dir, source_root):
        return SameRunDuplicateArchiveResult(
            success=False,
            archive_path=None,
            lifecycle_status="archive_failed",
            error=f"Duplikat-Archivpfad liegt ausserhalb des Input-Roots: {archive_dir}",
        )

    if expected_hash is not None:
        source_hash, _ = _file_meta(source_path)
        if source_hash != expected_hash:
            return SameRunDuplicateArchiveResult(
                success=False,
                archive_path=None,
                lifecycle_status="archive_failed",
                error="Archivierung abgebrochen: Hash der Quelle hat sich geändert.",
            )

    try:
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_target = _duplicate_archive_collision_path(archive_dir, source_path.name)
        shutil.move(str(source_path), str(archive_target))
        if source_path.exists():
            return SameRunDuplicateArchiveResult(
                success=False,
                archive_path=None,
                lifecycle_status="archive_failed",
                error="Quelle existiert nach Verschieben noch.",
            )
        if not archive_target.exists():
            return SameRunDuplicateArchiveResult(
                success=False,
                archive_path=None,
                lifecycle_status="archive_failed",
                error="Duplikat-Ziel existiert nach Verschieben nicht.",
            )
        return SameRunDuplicateArchiveResult(
            success=True,
            archive_path=archive_target,
            lifecycle_status="archived_as_duplicate",
            error=None,
        )
    except OSError as exc:
        if source_path.exists():
            return SameRunDuplicateArchiveResult(
                success=False,
                archive_path=None,
                lifecycle_status="archive_failed",
                error=f"Verschieben fehlgeschlagen, Quelle unangetastet: {exc}",
            )
        return SameRunDuplicateArchiveResult(
            success=False,
            archive_path=None,
            lifecycle_status="archive_failed",
            error=f"Verschieben fehlgeschlagen: {exc}",
        )


def archive_original_safely(
    *,
    original_path: Path,
    archive_dir: Path,
    expected_hash: str,
) -> Path:
    if not original_path.exists():
        raise LifecycleError(
            f"Originaldatei für Archivierung nicht gefunden: {original_path}",
            code="archive_source_missing",
            status=STATUS_ARCHIVE_FAILED,
        )
    source_hash, _ = _file_meta(original_path)
    if source_hash != expected_hash:
        raise LifecycleError(
            "Archivierung abgebrochen: Original-Hash hat sich geändert",
            code="archive_hash_mismatch",
            status=STATUS_ARCHIVE_FAILED,
        )
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_target = unique_archive_path(archive_dir, original_path.name)
    shutil.move(str(original_path), str(archive_target))
    archived_hash, _ = _file_meta(archive_target)
    if archived_hash != expected_hash:
        raise LifecycleError(
            "Archiv-Verifikation fehlgeschlagen: Hash stimmt nicht",
            code="archive_verify_failed",
            status=STATUS_ARCHIVE_FAILED,
        )
    return archive_target


# ---------------------------------------------------------------------------
# Lifecycle mapping record
# ---------------------------------------------------------------------------

@dataclass
class LifecycleRecord:
    run_id: str
    item_id: str
    original_path: str
    original_filename: str
    original_sha256: str
    original_size: int
    configured_output_root: str
    resolved_target_directory: str
    status: str = STATUS_PENDING
    output_action: str | None = None
    verified: bool = False
    started_at: str = field(default_factory=_utc_now)
    output_verified_at: str | None = None
    archived_at: str | None = None
    completed_at: str | None = None
    archived_original_path: str | None = None
    archived_original_sha256: str | None = None
    final_output_path: str | None = None
    final_filename: str | None = None
    final_sha256: str | None = None
    final_size: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    duplicate_of: str | None = None
    profile_id: str | None = None
    rule_id: str | None = None
    routing_field: str | None = None
    raw_routing_value: str | None = None
    normalized_routing_value: str | None = None
    target_id: str | None = None
    target_display_name: str | None = None
    matched_routing_value: str | None = None
    destination_type: str | None = None
    destination_mode: str | None = None
    configured_destination_path: str | None = None
    overrides_used: bool = False
    fallback_used: bool = False

    def to_mapping_dict(self) -> dict[str, Any]:
        return asdict(self)

    def mark_processing(self) -> None:
        self.status = STATUS_PROCESSING

    def apply_publish(self, result: PublishResult) -> None:
        self.status = result.lifecycle_status
        self.output_action = result.output_action
        self.verified = result.verified
        if result.verified:
            self.final_output_path = str(result.final_path)
            self.final_filename = result.final_path.name
            self.final_sha256 = result.final_sha256
            self.final_size = result.final_size
            self.output_verified_at = _utc_now()
        if result.duplicate_of is not None:
            self.duplicate_of = str(result.duplicate_of)
            self.final_output_path = str(result.duplicate_of)
            self.final_filename = result.duplicate_of.name

    def mark_success(self, archive_path: Path, archived_hash: str, archived_size: int) -> None:
        if self.status == STATUS_COLLISION_RENAMED:
            self.status = STATUS_COLLISION_RENAMED
        else:
            self.status = STATUS_SUCCESS
        self.archived_original_path = str(archive_path)
        self.archived_original_sha256 = archived_hash
        self.archived_at = _utc_now()
        self.completed_at = _utc_now()
        self.error_code = None
        self.error_message = None

    def mark_failure(self, *, code: str, message: str, status: str) -> None:
        self.status = status
        self.error_code = code
        self.error_message = message
        if status != STATUS_ARCHIVE_FAILED:
            self.verified = False
        self.completed_at = None


def make_item_id(index: int) -> str:
    return f"item-{index:04d}"


def make_recovery_item_id() -> str:
    return f"item-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Atomic mapping + recovery persistence
# ---------------------------------------------------------------------------

class OutputMappingStore:
    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        self.mapping_path = run_dir / MAPPING_FILENAME
        self.temp_path = run_dir / MAPPING_TEMP_FILENAME
        self.records: list[LifecycleRecord] = []

    def add_or_replace(self, record: LifecycleRecord) -> None:
        for index, existing in enumerate(self.records):
            if existing.item_id == record.item_id:
                self.records[index] = record
                return
        self.records.append(record)

    def flush(self) -> Path:
        payload = {
            "run_id": self.run_id,
            "mappings": [record.to_mapping_dict() for record in self.records],
        }
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        self.temp_path.write_text(serialized, encoding="utf-8")
        os.replace(self.temp_path, self.mapping_path)
        return self.mapping_path


class RecoveryRecordStore:
    def __init__(self, run_dir: Path) -> None:
        self.path = run_dir / RECOVERY_FILENAME
        self.records: list[dict[str, Any]] = []
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.records = list(data.get("records", []))
            except json.JSONDecodeError:
                self.records = []

    def add(self, record: dict[str, Any]) -> None:
        self.records.append(record)
        self.flush()

    def flush(self) -> None:
        temp = self.path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps({"records": self.records}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, self.path)


def find_recoverable_verified_output(
    *,
    original_hash: str,
    target_dir: Path,
    desired_filename: str,
    mapping_store: OutputMappingStore | None,
) -> Path | None:
    """Detect an already verified output from a prior incomplete lifecycle."""
    if mapping_store is None:
        return None

    for record in mapping_store.records:
        if record.original_sha256 != original_hash:
            continue
        if not record.verified or not record.final_output_path:
            continue
        if record.status in {STATUS_ARCHIVE_FAILED, STATUS_RECOVERY_REQUIRED, STATUS_INTERRUPTED}:
            candidate = Path(record.final_output_path)
            if candidate.exists():
                return candidate
    return None
