from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from invoice_tool.classification import classify_document_type
from invoice_tool.config import load_office_rules
from invoice_tool.extraction import ExtractionCoordinator
from invoice_tool.folder_destination import (
    resolve_configured_target_directory,
    resolve_routing_folder_key,
)
from invoice_tool.file_lifecycle import (
    LifecycleError,
    LifecycleRecord,
    OutputMappingStore,
    RecoveryRecordStore,
    STATUS_ARCHIVE_FAILED,
    STATUS_COLLISION_RENAMED,
    STATUS_DUPLICATE,
    STATUS_OUTPUT_FAILED,
    STATUS_RECOVERY_REQUIRED,
    STATUS_SUCCESS,
    archive_original_safely,
    archive_same_run_duplicate,
    find_recoverable_verified_output,
    make_item_id,
    publish_output_atomically,
    resolve_safe_target_directory,
    sanitize_final_filename,
    validate_input_file_safety,
    validate_output_directory_safety,
    verify_output_file,
)
from invoice_tool.filename_schema import build_filename
from invoice_tool.logging_utils import RunLogger
from invoice_tool.models import (
    AppConfig,
    ClassificationDecision,
    DocumentProfileRule,
    NormalizedInvoice,
    OfficeRules,
    ProcessResult,
    RoutingDecision,
)
from invoice_tool.normalization import (
    NormalizationError,
    normalize_invoice_date,
    normalize_invoice_with_fallbacks,
    sanitize_document_name,
)
from invoice_tool.recipient_guard import (
    apply_recipient_guard_to_routing,
    evaluate_recipient_guard,
)
from invoice_tool.routing_guards import (
    apply_classification_guards,
    apply_routing_guards,
    evaluate_business_non_invoice_document,
)
from invoice_tool.routing import (
    apply_final_assignment,
    determine_business_context,
    detect_street,
    detect_payment_method,
    resolve_account,
    resolve_priority_routing,
)
from invoice_tool.software_ai_tools import refine_routing_for_software_ai_tool
from invoice_tool.supplier_routing import resolve_supplier_profile_routing
from invoice_tool.state import (
    DirectoryLock,
    ensure_runtime_dirs,
    fingerprint_file,
    load_processed_state,
    path_token,
    save_processed_state,
)
from invoice_tool.target_routing import (
    TargetRoutingError,
    build_routing_metadata,
    build_runtime_filename,
    extract_routing_field_value,
    load_target_routing_config,
    profile_uses_cfg001_runtime_routing,
    resolve_runtime_target_directory,
)
from invoice_tool.trace import DecisionTrace, TraceWriter, mask_sensitive


class ProcessorError(RuntimeError):
    pass


def unique_target_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


class InvoiceProcessor:
    def __init__(
        self,
        config: AppConfig,
        extractor: ExtractionCoordinator,
        *,
        office_rules: OfficeRules | None = None,
        logger: RunLogger | None = None,
        document_profiles: list[DocumentProfileRule] | None = None,
        folder_destinations: dict[str, dict[str, str]] | None = None,
        original_source_dir: Path | None = None,
        snapshot_to_original: dict[Path, Path] | None = None,
        technical_run_dir: Path | None = None,
        mapping_store: OutputMappingStore | None = None,
        active_profile_id: str | None = None,
        target_routing_config: dict | None = None,
        profile_data: dict | None = None,
    ) -> None:
        self.config = config
        self.office_rules = office_rules or load_office_rules(
            config.regeln_datei,
            active_preset_override=config.aktives_preset,
        )
        self.preset = self.office_rules.preset
        self.extractor = extractor
        self.run_logger = logger or RunLogger(self.config.log_ordner)
        self.document_profiles: list[DocumentProfileRule] = document_profiles or []
        self.folder_destinations: dict[str, dict[str, str]] = dict(
            folder_destinations or {}
        )
        self.original_source_dir = (original_source_dir or config.eingangsordner).resolve()
        self.snapshot_to_original = {
            snapshot.resolve(): original.resolve()
            for snapshot, original in (snapshot_to_original or {}).items()
        }
        self.technical_run_dir = technical_run_dir.resolve() if technical_run_dir else None
        self.mapping_store = mapping_store
        self.active_profile_id = active_profile_id
        self.profile_data = profile_data
        if target_routing_config is not None:
            self.target_routing_config = target_routing_config
        elif profile_data is not None and profile_uses_cfg001_runtime_routing(profile_data):
            self.target_routing_config = load_target_routing_config(profile_data)
        else:
            self.target_routing_config = None
        self.recovery_store = (
            RecoveryRecordStore(self.technical_run_dir)
            if self.technical_run_dir is not None
            else None
        )
        self._item_counter = 0

        self.config.ausgangsordner.mkdir(parents=True, exist_ok=True)
        self.preset.dokumente.basis_pfad.mkdir(parents=True, exist_ok=True)
        self.config.runtime_ordner.mkdir(parents=True, exist_ok=True)
        self.config.log_ordner.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.config.runtime_ordner / "state"
        ensure_runtime_dirs(self.state_dir)
        self.state_file = self.state_dir / "processed_state.json"
        self.run_archive_dir: Path | None = None
        self.run_seen_fingerprints: dict[str, Path] = {}
        self._trace_writer = TraceWriter()

    def _next_item_id(self) -> str:
        self._item_counter += 1
        return make_item_id(self._item_counter)

    def _begin_lifecycle_record(
        self,
        *,
        pdf_path: Path,
        item_id: str,
        target_folder: Path,
        routing_metadata: dict | None = None,
    ) -> LifecycleRecord:
        routing_meta = routing_metadata or {}
        original_path = self._resolve_original_path(pdf_path)
        original_hash, original_size = fingerprint_file(pdf_path), pdf_path.stat().st_size
        record = LifecycleRecord(
            run_id=self.run_logger.run_id,
            item_id=item_id,
            original_path=str(original_path),
            original_filename=original_path.name,
            original_sha256=original_hash,
            original_size=original_size,
            configured_output_root=str(self.config.ausgangsordner.resolve()),
            resolved_target_directory=str(target_folder.resolve()),
            profile_id=self.active_profile_id,
            rule_id=routing_meta.get("rule_id"),
            routing_field=routing_meta.get("routing_field"),
            raw_routing_value=routing_meta.get("raw_routing_value"),
            normalized_routing_value=routing_meta.get("normalized_routing_value"),
            target_id=routing_meta.get("target_id"),
            target_display_name=routing_meta.get("target_display_name"),
            matched_routing_value=routing_meta.get("matched_routing_value"),
            destination_type=routing_meta.get("destination_type"),
            destination_mode=routing_meta.get("destination_mode"),
            configured_destination_path=routing_meta.get("configured_destination_path"),
            overrides_used=bool(routing_meta.get("overrides_used", False)),
            fallback_used=bool(routing_meta.get("fallback_used", False)),
        )
        record.mark_processing()
        if self.mapping_store is not None:
            self.mapping_store.add_or_replace(record)
            self.mapping_store.flush()
        return record

    def _persist_lifecycle_record(self, record: LifecycleRecord) -> None:
        if self.mapping_store is not None:
            self.mapping_store.add_or_replace(record)
            self.mapping_store.flush()

    def _forbidden_output_roots(self) -> tuple[Path, ...]:
        return (
            self.config.eingangsordner.resolve(),
            (self.original_source_dir / self.preset.archivierung.basis_ordnername).resolve(),
        )

    def _publish_and_archive(
        self,
        *,
        pdf_path: Path,
        fingerprint: str,
        target_folder: Path,
        filename: str,
        routing_status: str,
        dokumenttyp: str,
        extracted,
        normalized: NormalizedInvoice | None = None,
        routing=None,
        street_key: str | None = None,
        normalization_warnings: list[str] | None = None,
        historical_match: dict | None = None,
        trace_kwargs: dict | None = None,
        routing_metadata: dict | None = None,
    ) -> ProcessResult:
        item_id = self._next_item_id()
        safe_folder = target_folder.resolve()
        routing_meta = routing_metadata or {}
        if self._path_is_within(safe_folder, self.config.ausgangsordner):
            validate_output_directory_safety(safe_folder, self.config.ausgangsordner.resolve())

        try:
            original_path = self._resolve_original_path(pdf_path)
            validate_input_file_safety(original_path, self.original_source_dir)
            if pdf_path.resolve() != original_path.resolve():
                validate_input_file_safety(pdf_path, self.config.eingangsordner)
        except LifecycleError as exc:
            record = self._begin_lifecycle_record(
                pdf_path=pdf_path,
                item_id=item_id,
                target_folder=safe_folder,
                routing_metadata=routing_meta,
            )
            record.mark_failure(code=exc.code, message=str(exc), status=exc.status)
            self._persist_lifecycle_record(record)
            raise ProcessorError(str(exc)) from exc

        record = self._begin_lifecycle_record(
            pdf_path=pdf_path,
            item_id=item_id,
            target_folder=safe_folder,
            routing_metadata=routing_meta,
        )
        content_hash = record.original_sha256
        safe_filename = sanitize_final_filename(filename)

        recovered = find_recoverable_verified_output(
            original_hash=content_hash,
            target_dir=safe_folder,
            desired_filename=safe_filename,
            mapping_store=self.mapping_store,
        )

        archive_target: Path | None = None
        output_target: Path
        output_action: str
        lifecycle_status: str
        verified_output = False
        error_code: str | None = None
        error_message: str | None = None

        try:
            if recovered is not None:
                publish = type(
                    "RecoveredPublish",
                    (),
                    {
                        "final_path": recovered,
                        "lifecycle_status": STATUS_SUCCESS,
                        "output_action": "recovered_existing",
                        "verified": True,
                        "final_sha256": content_hash,
                        "final_size": recovered.stat().st_size,
                        "duplicate_of": None,
                    },
                )()
            else:
                publish = publish_output_atomically(
                    source_pdf=pdf_path,
                    target_dir=safe_folder,
                    desired_filename=safe_filename,
                    content_hash=content_hash,
                    run_id=self.run_logger.run_id,
                    item_id=item_id,
                    output_root=self.config.ausgangsordner.resolve(),
                    forbid_under=self._forbidden_output_roots(),
                    enforce_output_containment=self._path_is_within(
                        safe_folder,
                        self.config.ausgangsordner,
                    ),
                )

            record.apply_publish(publish)
            self._persist_lifecycle_record(record)

            output_target = publish.final_path
            output_action = publish.output_action
            lifecycle_status = publish.lifecycle_status
            verified_output = publish.verified

            if lifecycle_status == STATUS_DUPLICATE:
                self._log_file_event(
                    filename=pdf_path.name,
                    dokumenttyp=dokumenttyp,
                    supplier=getattr(normalized, "supplier", None) if normalized else None,
                    date=getattr(normalized, "invoice_date", None) if normalized else None,
                    amount=getattr(normalized, "amount", None) if normalized else None,
                    account=getattr(routing, "konto", None) if routing else None,
                    payment_field=getattr(routing, "payment_field", None) if routing else None,
                    street=street_key,
                    routing_decision=f"duplicate: existing output {output_target}",
                    storage_path=output_target,
                    archive_path=None,
                    fallback_used=bool(extracted.fallback_used),
                    preset_used=self.office_rules.active_preset,
                    status=STATUS_DUPLICATE,
                    output_action=output_action,
                    error=None,
                )
                return ProcessResult(
                    input_file=pdf_path,
                    dokumenttyp=dokumenttyp,
                    status=STATUS_DUPLICATE,
                    storage_file=output_target,
                    archive_file=None,
                    used_extractor=extracted.source_method,
                    fallback_used=bool(extracted.fallback_used),
                    fingerprint=fingerprint,
                    supplier=getattr(normalized, "supplier", None) if normalized else None,
                    date=getattr(normalized, "invoice_date", None) if normalized else None,
                    amount=getattr(normalized, "amount", None) if normalized else None,
                    art=getattr(routing, "art", None) if routing else None,
                    konto=getattr(routing, "konto", None) if routing else None,
                    payment_field=getattr(routing, "payment_field", None) if routing else None,
                    street=street_key,
                    original_file=self._resolve_original_path(pdf_path),
                    verified_output=False,
                    item_id=item_id,
                    lifecycle_status=STATUS_DUPLICATE,
                    output_action=output_action,
                    routing_status=routing_status,
                    lifecycle_record=record.to_mapping_dict(),
                )

            if not verified_output:
                raise LifecycleError(
                    "Output wurde nicht verifiziert",
                    code="output_unverified",
                    status=STATUS_OUTPUT_FAILED,
                )

            try:
                archive_dir = self._ensure_run_archive_dir()
                original_path = self._resolve_original_path(pdf_path)
                archive_target = archive_original_safely(
                    original_path=original_path,
                    archive_dir=archive_dir,
                    expected_hash=content_hash,
                )
                archived_hash, archived_size = verify_output_file(archive_target)
                record.mark_success(archive_target, archived_hash, archived_size)
                lifecycle_status = (
                    STATUS_COLLISION_RENAMED
                    if record.status == STATUS_COLLISION_RENAMED
                    else STATUS_SUCCESS
                )
                record.status = lifecycle_status
                self._persist_lifecycle_record(record)
            except LifecycleError as exc:
                record.mark_failure(code=exc.code, message=str(exc), status=STATUS_ARCHIVE_FAILED)
                self._persist_lifecycle_record(record)
                if self.recovery_store is not None:
                    self.recovery_store.add(
                        {
                            "item_id": item_id,
                            "original_path": record.original_path,
                            "original_sha256": record.original_sha256,
                            "final_output_path": record.final_output_path,
                            "final_sha256": record.final_sha256,
                            "status": STATUS_RECOVERY_REQUIRED,
                            "error_code": exc.code,
                            "error_message": str(exc),
                        }
                    )
                error_code = exc.code
                error_message = str(exc)
                lifecycle_status = STATUS_ARCHIVE_FAILED
                verified_output = True

            if lifecycle_status in {STATUS_SUCCESS, STATUS_COLLISION_RENAMED}:
                self._remember_processed(
                    fingerprint=fingerprint,
                    dokumenttyp=dokumenttyp,
                    status=routing_status,
                    normalized=normalized,
                    output_target=output_target,
                    archive_target=archive_target,
                    used_extractor=extracted.source_method,
                    fallback_used=bool(extracted.fallback_used),
                    konto=getattr(routing, "konto", None) if routing else None,
                    payment_field=getattr(routing, "payment_field", None) if routing else None,
                    street=street_key,
                )
                self.run_seen_fingerprints[fingerprint] = output_target

            self._log_output_size(output_target)
            historical_report = None
            if historical_match is not None:
                historical_report = self._create_historical_reprocessing_report(
                    input_file=pdf_path,
                    fingerprint=fingerprint,
                    current_storage=output_target,
                    current_archive=archive_target,
                    historical=historical_match,
                )

            routing_decision = trace_kwargs.get("routing_decision") if trace_kwargs else None
            if historical_report is not None and routing_decision:
                routing_decision += f"; Historischer Treffer erneut verarbeitet, Report={historical_report}"

            self._log_file_event(
                filename=pdf_path.name,
                dokumenttyp=dokumenttyp,
                supplier=getattr(normalized, "supplier", None) if normalized else None,
                date=getattr(normalized, "invoice_date", None) if normalized else None,
                amount=getattr(normalized, "amount", None) if normalized else None,
                account=getattr(routing, "konto", None) if routing else None,
                payment_field=getattr(routing, "payment_field", None) if routing else None,
                street=street_key,
                routing_decision=routing_decision,
                storage_path=output_target,
                archive_path=archive_target,
                fallback_used=bool(extracted.fallback_used),
                preset_used=self.office_rules.active_preset,
                status=lifecycle_status,
                output_action=output_action,
                error=error_message,
            )

            if trace_kwargs:
                trace_payload = dict(trace_kwargs)
                trace_payload.pop("routing_decision", None)
                trace_payload["final_filename"] = output_target.name
                trace_payload["target_path"] = str(output_target)
                trace_payload["archive_path"] = str(archive_target) if archive_target else None
                self._trace_writer.record(DecisionTrace(**trace_payload))

            return ProcessResult(
                input_file=pdf_path,
                dokumenttyp=dokumenttyp,
                status=lifecycle_status,
                storage_file=output_target,
                archive_file=archive_target,
                used_extractor=extracted.source_method,
                fallback_used=bool(extracted.fallback_used),
                fingerprint=fingerprint,
                supplier=getattr(normalized, "supplier", None) if normalized else None,
                date=getattr(normalized, "invoice_date", None) if normalized else None,
                amount=getattr(normalized, "amount", None) if normalized else None,
                art=getattr(routing, "art", None) if routing else None,
                konto=getattr(routing, "konto", None) if routing else None,
                payment_field=getattr(routing, "payment_field", None) if routing else None,
                street=street_key,
                original_file=self._resolve_original_path(pdf_path),
                verified_output=verified_output,
                item_id=item_id,
                lifecycle_status=lifecycle_status,
                output_action=output_action,
                routing_status=routing_status,
                error_code=error_code,
                error_message=error_message,
                lifecycle_record=record.to_mapping_dict(),
            )
        except LifecycleError as exc:
            record.mark_failure(code=exc.code, message=str(exc), status=exc.status)
            self._persist_lifecycle_record(record)
            self._log_file_event(
                filename=pdf_path.name,
                dokumenttyp=dokumenttyp,
                supplier=None,
                date=None,
                amount=None,
                account=None,
                payment_field=None,
                street=None,
                routing_decision=str(exc),
                storage_path=None,
                archive_path=None,
                fallback_used=bool(extracted.fallback_used),
                preset_used=self.office_rules.active_preset,
                status=exc.status,
                output_action=None,
                error=str(exc),
            )
            raise ProcessorError(f"Fehler bei der Verarbeitung von {pdf_path.name}: {exc}") from exc

    def process_all(self) -> list[ProcessResult]:
        self.run_archive_dir = None
        self.run_seen_fingerprints = {}
        self._trace_writer = TraceWriter()
        pdf_files = sorted(
            path
            for path in self.config.eingangsordner.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        )
        self.log(
            f"{len(pdf_files)} PDF-Datei(en) im Eingangsordner gefunden: {self.config.eingangsordner}"
        )
        self.log(f"Aktives Preset: {self.office_rules.active_preset}")
        self.log("Archivordner wird bei der ersten erfolgreichen Datei im Eingangsordner angelegt.")

        results: list[ProcessResult] = []
        for pdf_path in pdf_files:
            try:
                result = self._process_one(pdf_path)
                if result is not None:
                    results.append(result)
            except ProcessorError as exc:
                self.log(str(exc))
        report_path = self.run_logger.write_run_report(
            self._report_root(),
            preset=self.office_rules.active_preset,
            input_count=len(pdf_files),
        )
        self.log(f"Run-Report geschrieben: {report_path}")
        trace_dir = self._report_root() / "_runs" / self.run_logger.run_id
        jsonl_path, csv_path = self._trace_writer.flush(trace_dir)
        self.log(f"Decision-Trace geschrieben: {jsonl_path}")
        self.log(f"Routing-Summary geschrieben: {csv_path}")
        return results

    def _process_one(self, pdf_path: Path) -> ProcessResult | None:
        file_lock_path = self.state_dir / "locks" / path_token(pdf_path)
        try:
            with DirectoryLock(file_lock_path, self.config.stale_lock_seconds):
                if not pdf_path.exists():
                    self.log(f"Datei wurde vor Verarbeitung entfernt, ueberspringe: {pdf_path.name}")
                    return None

                fingerprint = fingerprint_file(pdf_path)
                historical_match = self._lookup_processed_fingerprint(fingerprint)
                duplicate_result = self._handle_duplicate_if_needed(pdf_path, fingerprint)
                if duplicate_result is not None:
                    return duplicate_result

                if historical_match is not None:
                    previous_reference = historical_match.get("storage_file") or historical_match.get("archive_file")
                    self.log(
                        "Historischer Fingerprint-Treffer erkannt, Datei wird erneut verarbeitet: "
                        f"{pdf_path.name} -> {previous_reference}"
                    )

                extracted = self.extractor.extract(pdf_path, log=self.log)
                classification = classify_document_type(extracted, self.preset)
                classification = apply_classification_guards(
                    extracted,
                    classification,
                    profile_data=self.profile_data,
                )
                if self.target_routing_config is not None:
                    result = self._process_with_target_routing(
                        pdf_path=pdf_path,
                        fingerprint=fingerprint,
                        extracted=extracted,
                        classification=classification,
                        historical_match=historical_match,
                    )
                elif classification.dokumenttyp == "invoice":
                    result = self._process_invoice(
                        pdf_path=pdf_path,
                        fingerprint=fingerprint,
                        extracted=extracted,
                        classification=classification,
                        historical_match=historical_match,
                    )
                else:
                    # document branch: try profile matching first when profiles are loaded.
                    matched_profile, match_score, match_meta = (
                        self._match_document_profile(extracted)
                    )
                    if matched_profile is not None:
                        result = self._process_document_with_profile(
                            pdf_path=pdf_path,
                            fingerprint=fingerprint,
                            extracted=extracted,
                            classification=classification,
                            historical_match=historical_match,
                            matched_profile=matched_profile,
                            match_score=match_score,
                            match_meta=match_meta,
                        )
                    else:
                        business_doc = evaluate_business_non_invoice_document(
                            extracted, classification
                        )
                        if business_doc.is_business_non_invoice:
                            result = self._process_business_non_invoice_document(
                                pdf_path=pdf_path,
                                fingerprint=fingerprint,
                                extracted=extracted,
                                classification=classification,
                                historical_match=historical_match,
                                business_doc=business_doc,
                            )
                        else:
                            result = self._process_document(
                                pdf_path=pdf_path,
                                fingerprint=fingerprint,
                                extracted=extracted,
                                classification=classification,
                                historical_match=historical_match,
                            )
                return result
        except Exception as exc:  # noqa: BLE001
            self._log_file_event(
                filename=pdf_path.name,
                dokumenttyp="unknown",
                supplier=None,
                date=None,
                amount=None,
                account=None,
                payment_field=None,
                street=None,
                routing_decision=None,
                storage_path=None,
                archive_path=None,
                fallback_used=None,
                preset_used=self.office_rules.active_preset,
                status="failed",
                output_action=None,
                error=str(exc),
            )
            raise ProcessorError(f"Fehler bei der Verarbeitung von {pdf_path.name}: {exc}") from exc

    def _lookup_processed_fingerprint(self, fingerprint: str) -> dict | None:
        state_lock_path = self.state_dir / "state.lock"
        with DirectoryLock(state_lock_path, self.config.stale_lock_seconds):
            state = load_processed_state(self.state_file)
            return state.get(fingerprint)

    def _remember_processed(
        self,
        *,
        fingerprint: str,
        dokumenttyp: str,
        status: str,
        normalized: NormalizedInvoice | None,
        output_target: Path,
        archive_target: Path,
        used_extractor: str,
        fallback_used: bool,
        konto: str | None,
        payment_field: str | None,
        street: str | None,
    ) -> None:
        state_lock_path = self.state_dir / "state.lock"
        with DirectoryLock(state_lock_path, self.config.stale_lock_seconds):
            state = load_processed_state(self.state_file)
            state[fingerprint] = {
                "dokumenttyp": dokumenttyp,
                "status": status,
                "source_filename": output_target.name if archive_target is None else archive_target.name,
                "invoice_date": normalized.invoice_date if normalized else None,
                "supplier": normalized.supplier if normalized else None,
                "amount": normalized.amount if normalized else None,
                "storage_file": str(output_target),
                "archive_file": str(archive_target),
                "used_extractor": used_extractor,
                "fallback_used": fallback_used,
                "konto": konto,
                "payment_field": payment_field,
                "street": street,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
            }
            save_processed_state(self.state_file, state)

    def _process_invoice(
        self,
        *,
        pdf_path: Path,
        fingerprint: str,
        extracted,
        classification: ClassificationDecision,
        historical_match: dict | None,
    ) -> ProcessResult:
        normalized, normalization_warnings = normalize_invoice_with_fallbacks(
            extracted,
            self.preset.invoice_fallbacks,
            self.preset.supplier_cleaning,
        )
        account_decision = resolve_account(extracted, self.preset)
        street_key = detect_street(extracted, self.preset)
        art, art_reason = determine_business_context(extracted, account_decision, self.preset, street_key)
        payment_decision = detect_payment_method(extracted, self.preset)

        supplier_match = resolve_supplier_profile_routing(extracted, self.preset, self.profile_data)
        supplier_trace: dict | None = None
        priority_routing = None

        if supplier_match is not None and supplier_match.exclusive:
            routing = supplier_match.routing
            supplier_trace = {
                "source": supplier_match.source,
                "rule": supplier_match.trace_rule or supplier_match.rule_id,
                "economic_assignment": supplier_match.economic_assignment,
                "payment_method": routing.payment_field,
                "payment_reference": supplier_match.payment_reference,
                "target_folder": routing.zielordner,
                "value_not_extracted_from_document": supplier_match.value_not_extracted_from_document,
                "art_deferred": supplier_match.art_deferred,
            }
            if supplier_match.art_deferred or not supplier_match.economic_assignment:
                # Payment-only vendor rule (e.g. Cursor/Anysphere → amex without category):
                # keep payment/folder from profile; refine art via business context +
                # software-/AI-tool policy. Never apply blind default_art=private.
                routing = RoutingDecision(
                    art=art,
                    zielordner=routing.zielordner,
                    status=routing.status,
                    konto=routing.konto,
                    payment_field=routing.payment_field,
                    street_key=street_key,
                    begruendung=routing.begruendung,
                )
                routing, art, art_reason = refine_routing_for_software_ai_tool(
                    routing,
                    extracted,
                    art=art,
                    art_reason=art_reason,
                    street_key=street_key,
                    preset=self.preset,
                )
                supplier_trace["target_folder"] = routing.zielordner
                supplier_trace["refined_art"] = art
            else:
                art = routing.art
                art_reason = routing.begruendung

            # Exclusive vendor shortcuts must still pass mixed-address / payment-evidence
            # guards (e.g. Amazon private billing + business delivery → unklar).
            guards_result = apply_routing_guards(
                routing,
                extracted=extracted,
                account_decision=account_decision,
                payment_decision=payment_decision,
                preset=self.preset,
                street_key=street_key,
            )
            routing = guards_result.routing
            if guards_result.applied:
                art = routing.art
                art_reason = (
                    f"{art_reason}; Routing-Guards: {', '.join(guards_result.applied)}"
                )
                supplier_trace["routing_guards"] = list(guards_result.applied)
                supplier_trace["target_folder"] = routing.zielordner
                supplier_trace["payment_method"] = routing.payment_field
        else:
            priority_routing = resolve_priority_routing(extracted, account_decision, street_key, self.preset)
            if priority_routing is not None:
                routing = priority_routing
                art_reason = f"{art_reason}; Prioritaetsregel: {priority_routing.begruendung}"
            else:
                routing = apply_final_assignment(
                    art=art,
                    payment_decision=payment_decision,
                    account_decision=account_decision,
                    street_key=street_key,
                    preset=self.preset,
                    extracted=extracted,
                )

            guard = evaluate_recipient_guard(
                extracted,
                self.preset,
                profile_data=self.profile_data,
                proposed_art=routing.art,
                street_key=street_key,
                priority_routing=priority_routing,
                art_reason=art_reason,
            )
            routing = apply_recipient_guard_to_routing(
                routing,
                guard,
                self.preset,
                street_key=street_key,
            )
            if guard.outcome == "force_unklar":
                art = routing.art
                art_reason = f"{art_reason}; Recipient-Guard: {guard.reason}"

            if supplier_match is not None and not supplier_match.exclusive:
                if supplier_match.art_deferred or not supplier_match.economic_assignment:
                    routing = RoutingDecision(
                        art=art,
                        zielordner=supplier_match.routing.zielordner,
                        status=supplier_match.routing.status,
                        konto=supplier_match.routing.konto,
                        payment_field=supplier_match.routing.payment_field,
                        street_key=street_key,
                        begruendung=supplier_match.routing.begruendung,
                    )
                else:
                    routing = supplier_match.routing
                    art = routing.art
                    art_reason = routing.begruendung

            guards_result = apply_routing_guards(
                routing,
                extracted=extracted,
                account_decision=account_decision,
                payment_decision=payment_decision,
                preset=self.preset,
                street_key=street_key,
            )
            routing = guards_result.routing
            if guards_result.applied:
                art = routing.art
                art_reason = (
                    f"{art_reason}; Routing-Guards: {', '.join(guards_result.applied)}"
                )

            routing, art, art_reason = refine_routing_for_software_ai_tool(
                routing,
                extracted,
                art=art,
                art_reason=art_reason,
                street_key=street_key,
                preset=self.preset,
            )

        filename = build_filename(
            self.preset.filename_schema,
            {
                "invoice_date": normalized.invoice_date,
                "art": routing.art,
                "supplier": normalized.supplier,
                "amount": normalized.amount,
                "konto": routing.konto or "null",
                "payment_field": routing.payment_field,
            },
        )

        folder_name = routing.zielordner or routing.art or "unklar"
        target_folder = self._resolve_routing_target_folder(folder_name)

        output_route_rule_name: str | None = None
        for orr in self.preset.routing.output_route_rules:
            folder_match = not orr.art_any or routing.art in set(orr.art_any)
            pf_match = not orr.payment_field_any or routing.payment_field in set(orr.payment_field_any)
            if folder_match and pf_match and self.preset.routing.zielordner.get(orr.zielordner) == routing.zielordner:
                output_route_rule_name = orr.name
                break

        routing_decision = (
            f"{routing.zielordner} ({routing.begruendung}); Klassifikation={classification.begruendung}; "
            f"Art={routing.art} ({art_reason}); Payment={routing.payment_field} ({payment_decision.begruendung}); "
            f"Normalisierung={'; '.join(normalization_warnings) if normalization_warnings else 'ok'}"
        )
        if supplier_trace is not None:
            routing_decision += f"; SupplierProfileRule={supplier_trace}"

        return self._publish_and_archive(
            pdf_path=pdf_path,
            fingerprint=fingerprint,
            target_folder=target_folder,
            filename=filename,
            routing_status=routing.status,
            dokumenttyp="invoice",
            extracted=extracted,
            normalized=normalized,
            routing=routing,
            street_key=street_key,
            normalization_warnings=normalization_warnings,
            historical_match=historical_match,
            routing_metadata=self._routing_metadata_for_folder_key(
                folder_name,
                rule_id=(
                    _extract_rule_name(priority_routing.begruendung)
                    if priority_routing is not None
                    else _extract_rule_name(routing.begruendung)
                ),
            ),
            trace_kwargs={
                "run_id": self.run_logger.run_id,
                "original_filename": pdf_path.name,
                "final_filename": sanitize_final_filename(filename),
                "source_path": str(pdf_path),
                "target_path": str(target_folder / sanitize_final_filename(filename)),
                "archive_path": "",
                "document_type": "invoice",
                "classification_reason": mask_sensitive(classification.begruendung),
                "extracted_invoice_date": normalized.invoice_date,
                "extracted_supplier": mask_sensitive(normalized.supplier),
                "extracted_amount": normalized.amount,
                "extraction_method": extracted.source_method,
                "fallback_used": bool(extracted.fallback_used),
                "detected_street_key": street_key,
                "business_context_art": art,
                "business_context_reason": mask_sensitive(art_reason),
                "account_konto": account_decision.konto,
                "account_payment_field": account_decision.payment_field,
                "account_match_source": account_decision.begruendung.split(":")[0].strip()
                if ":" in account_decision.begruendung
                else None,
                "account_match_reason": mask_sensitive(account_decision.begruendung),
                "account_matched_rule": account_decision.matched_rule,
                "detected_payment_method": payment_decision.payment_method,
                "payment_rule_name": _extract_rule_name(payment_decision.begruendung),
                "payment_explicit": payment_decision.explicit,
                "payment_signals": _extract_signals(payment_decision.begruendung),
                "priority_rule_name": _extract_rule_name(priority_routing.begruendung)
                if priority_routing is not None
                else None,
                "final_assignment_rule_name": _extract_rule_name(routing.begruendung)
                if priority_routing is None
                else None,
                "final_art": routing.art,
                "final_konto": routing.konto,
                "final_payment_field": routing.payment_field,
                "final_status": routing.status,
                "output_route_rule_name": output_route_rule_name,
                "final_output_folder": routing.zielordner,
                "filename_fields_used": [
                    f.quelle or f.wert or ""
                    for f in self.preset.filename_schema.felder
                    if f.aktiv
                ],
                "normalization_warnings": normalization_warnings,
                "conflicts": [account_decision.begruendung]
                if account_decision.ist_widerspruechlich
                else [],
                "routing_decision": routing_decision,
            },
        )

    def _process_with_target_routing(
        self,
        *,
        pdf_path: Path,
        fingerprint: str,
        extracted,
        classification: ClassificationDecision,
        historical_match: dict | None,
    ) -> ProcessResult:
        """Route a document using the CFG-001 target_routing resolver."""
        config = self.target_routing_config
        if not isinstance(config, dict):
            raise ProcessorError("Zielordner-Konfiguration fehlt.")

        global_rules = config.get("global_document_rules") if isinstance(config.get("global_document_rules"), dict) else {}
        routing_field = str(global_rules.get("routing_field") or "payment_field")
        document_date = self._document_date(extracted.invoice_date_raw)

        normalized: NormalizedInvoice | None = None
        normalization_warnings: list[str] = []
        account_decision = None
        payment_decision = None
        art: str | None = None

        if classification.dokumenttyp == "invoice":
            normalized, normalization_warnings = normalize_invoice_with_fallbacks(
                extracted,
                self.preset.invoice_fallbacks,
                self.preset.supplier_cleaning,
            )
            account_decision = resolve_account(extracted, self.preset)
            street_key = detect_street(extracted, self.preset)
            art, _art_reason = determine_business_context(
                extracted, account_decision, self.preset, street_key
            )
            payment_decision = detect_payment_method(extracted, self.preset)
        else:
            try:
                normalized, normalization_warnings = normalize_invoice_with_fallbacks(
                    extracted,
                    self.preset.invoice_fallbacks,
                    self.preset.supplier_cleaning,
                )
            except Exception:  # noqa: BLE001
                normalized = None

        raw_routing_value = extract_routing_field_value(
            routing_field,
            extracted=extracted,
            normalized=normalized,
            classification=classification,
            account_decision=account_decision,
            art=art,
            payment_decision=payment_decision,
            document_date=document_date,
        )

        target_folder, assignment = resolve_runtime_target_directory(
            config,
            raw_routing_value,
            output_root=self.config.ausgangsordner.resolve(),
        )
        routing_metadata = build_routing_metadata(assignment)

        field_values = {
            "invoice_date": document_date,
            "supplier": (normalized.supplier if normalized else (extracted.supplier_raw or "unbekannt")).lower(),
            "amount": normalized.amount if normalized else (extracted.amount_raw or "unbekannt"),
            "payment_field": raw_routing_value or "unbekannt",
            "art": art or "d",
            "document_type": classification.dokumenttyp,
        }
        filename = build_runtime_filename(config, assignment, field_values=field_values)

        routing_decision = (
            f"target_routing:{assignment.matched_display_name or 'Fallback'} "
            f"({assignment.message}); Feld={routing_field}; Wert={raw_routing_value or '–'}"
        )
        if assignment.overrides_used:
            routing_decision += "; overrides=filename_template"

        return self._publish_and_archive(
            pdf_path=pdf_path,
            fingerprint=fingerprint,
            target_folder=target_folder,
            filename=filename,
            routing_status="target_routing",
            dokumenttyp=classification.dokumenttyp,
            extracted=extracted,
            normalized=normalized,
            historical_match=historical_match,
            normalization_warnings=normalization_warnings,
            routing_metadata=routing_metadata,
            trace_kwargs={
                "run_id": self.run_logger.run_id,
                "original_filename": pdf_path.name,
                "final_filename": sanitize_final_filename(filename),
                "source_path": str(pdf_path),
                "target_path": str(target_folder / sanitize_final_filename(filename)),
                "archive_path": None,
                "document_type": classification.dokumenttyp,
                "classification_reason": mask_sensitive(classification.begruendung),
                "extracted_invoice_date": document_date,
                "extracted_supplier": mask_sensitive(extracted.supplier_raw),
                "extracted_amount": mask_sensitive(extracted.amount_raw),
                "extraction_method": extracted.source_method,
                "fallback_used": assignment.is_fallback,
                "detected_street_key": None,
                "business_context_art": art,
                "business_context_reason": None,
                "account_konto": getattr(account_decision, "konto", None) if account_decision else None,
                "account_payment_field": raw_routing_value,
                "account_match_source": None,
                "account_match_reason": None,
                "account_matched_rule": None,
                "detected_payment_method": getattr(payment_decision, "payment_method", None)
                if payment_decision
                else None,
                "payment_rule_name": None,
                "payment_explicit": None,
                "payment_signals": None,
                "priority_rule_name": None,
                "final_assignment_rule_name": assignment.matched_target_id,
                "final_art": art,
                "final_konto": getattr(account_decision, "konto", None) if account_decision else None,
                "final_payment_field": raw_routing_value,
                "final_status": "target_routing",
                "output_route_rule_name": None,
                "final_output_folder": str(target_folder),
                "filename_fields_used": list(field_values.keys()),
                "normalization_warnings": normalization_warnings,
                "conflicts": [],
                "routing_decision": routing_decision,
            },
        )

    def _process_document(
        self,
        *,
        pdf_path: Path,
        fingerprint: str,
        extracted,
        classification: ClassificationDecision,
        historical_match: dict | None,
    ) -> ProcessResult:
        document_date = self._document_date(extracted.invoice_date_raw)
        descriptive_name = self._document_name(extracted)
        filename = (
            f"{document_date}_{self.preset.dokumente.prefix}_{descriptive_name}_"
            f"{self.preset.dokumente.suffix_placeholder}.pdf"
        )
        target_folder = self.preset.dokumente.basis_pfad
        return self._publish_and_archive(
            pdf_path=pdf_path,
            fingerprint=fingerprint,
            target_folder=target_folder,
            filename=filename,
            routing_status="document",
            dokumenttyp="document",
            extracted=extracted,
            historical_match=historical_match,
            trace_kwargs={
                "run_id": self.run_logger.run_id,
                "original_filename": pdf_path.name,
                "final_filename": sanitize_final_filename(filename),
                "source_path": str(pdf_path),
                "target_path": str(target_folder / sanitize_final_filename(filename)),
                "archive_path": None,
                "document_type": "document",
                "classification_reason": mask_sensitive(classification.begruendung),
                "extracted_invoice_date": document_date,
                "extracted_supplier": mask_sensitive(extracted.supplier_raw),
                "extracted_amount": mask_sensitive(extracted.amount_raw),
                "extraction_method": extracted.source_method,
                "fallback_used": bool(extracted.fallback_used),
                "detected_street_key": None,
                "business_context_art": None,
                "business_context_reason": None,
                "account_konto": None,
                "account_payment_field": None,
                "account_match_source": None,
                "account_match_reason": None,
                "account_matched_rule": None,
                "detected_payment_method": None,
                "payment_rule_name": None,
                "payment_explicit": None,
                "payment_signals": None,
                "priority_rule_name": None,
                "final_assignment_rule_name": None,
                "final_art": None,
                "final_konto": None,
                "final_payment_field": None,
                "final_status": "document",
                "output_route_rule_name": None,
                "final_output_folder": str(self.preset.dokumente.basis_pfad.name),
                "filename_fields_used": [],
                "normalization_warnings": [],
                "conflicts": [],
                "routing_decision": classification.begruendung,
            },
        )

    def _business_non_invoice_descriptive_name(
        self,
        extracted,
        *,
        subtype: str | None,
    ) -> str:
        if extracted.document_name_raw:
            try:
                return sanitize_document_name(
                    extracted.document_name_raw,
                    max_words=self.preset.dokumente.max_woerter,
                )
            except NormalizationError:
                pass

        supplier_slug = ""
        if extracted.supplier_raw:
            try:
                from invoice_tool.normalization import (
                    clean_supplier_text,
                    normalize_supplier_name,
                )

                cleaned = clean_supplier_text(
                    extracted.supplier_raw, self.preset.supplier_cleaning
                )
                supplier_slug = normalize_supplier_name(cleaned)
            except Exception:  # noqa: BLE001
                try:
                    supplier_slug = sanitize_document_name(
                        extracted.supplier_raw,
                        max_words=3,
                    )
                except NormalizationError:
                    supplier_slug = ""

        prefix = "bestellbestaetigung" if subtype == "order_confirmation" else "geschaeftsdokument"
        if supplier_slug:
            return f"{prefix}-{supplier_slug}"
        return prefix

    def _process_business_non_invoice_document(
        self,
        *,
        pdf_path: Path,
        fingerprint: str,
        extracted,
        classification: ClassificationDecision,
        historical_match: dict | None,
        business_doc,
    ) -> ProcessResult:
        """Order confirmations / purchase docs: keep non-invoice type, preserve art/payment."""

        normalized: NormalizedInvoice | None = None
        normalization_warnings: list[str] = []
        try:
            normalized, normalization_warnings = normalize_invoice_with_fallbacks(
                extracted,
                self.preset.invoice_fallbacks,
                self.preset.supplier_cleaning,
            )
        except Exception:  # noqa: BLE001
            normalized = None

        account_decision = resolve_account(extracted, self.preset)
        street_key = detect_street(extracted, self.preset)
        art, art_reason = determine_business_context(
            extracted, account_decision, self.preset, street_key
        )
        payment_decision = detect_payment_method(extracted, self.preset)

        # Business billing (SOMAA/Bismarck in Rechnungsadresse) may set art=ai.
        # Delivery-only business signals must not invent ai.
        if business_doc.has_business_billing_signal and art in {"ai", "ep"}:
            final_art = art
        elif business_doc.has_business_billing_signal:
            final_art = "ai"
            art_reason = f"{art_reason}; Business-Billing-Signal für Non-Invoice-Dokument."
        else:
            final_art = "unklar"
            art_reason = (
                f"{art_reason}; Kein berufliches Rechnungsadress-Signal "
                "für Non-Invoice-Dokument."
            )

        # Preserve explicit payment methods (e.g. PayPal) without booking as invoice.
        if payment_decision.explicit and payment_decision.payment_method not in {
            "",
            "unknown",
            "unbekannt",
        }:
            payment_field = payment_decision.payment_method
        else:
            payment_field = self.preset.routing.unklar_konto or "unklar"

        unklar_folder = self.preset.routing.zielordner.get("unklar", "unklar")
        target_folder = self._resolve_routing_target_folder(unklar_folder)
        document_date = self._document_date(
            getattr(normalized, "invoice_date", None) or extracted.invoice_date_raw
        )
        amount = (
            getattr(normalized, "amount", None)
            or extracted.amount_raw
            or self.preset.invoice_fallbacks.amount
            or "unknown-amount"
        )
        descriptive_name = self._business_non_invoice_descriptive_name(
            extracted, subtype=business_doc.subtype
        )
        prefix = self.preset.dokumente.prefix or "d"
        filename = (
            f"{document_date}_{prefix}_{final_art}_{descriptive_name}_"
            f"{amount}_{payment_field}.pdf"
        )

        subtype = business_doc.subtype or "business_purchase_document"
        routing = RoutingDecision(
            art=final_art,
            zielordner=unklar_folder,
            status="unklar",
            konto=None,
            payment_field=payment_field,
            street_key=street_key,
            begruendung=(
                f"{classification.begruendung}; Business-Non-Invoice-Guard: "
                f"{business_doc.reason}; Art={art_reason}; "
                f"Payment={payment_decision.begruendung}; "
                "booking_status=review (Bestellbestätigung nicht buchbar)."
            ),
        )
        routing_decision = routing.begruendung

        return self._publish_and_archive(
            pdf_path=pdf_path,
            fingerprint=fingerprint,
            target_folder=target_folder,
            filename=filename,
            routing_status="unklar",
            dokumenttyp=subtype,
            extracted=extracted,
            normalized=normalized,
            routing=routing,
            street_key=street_key,
            normalization_warnings=normalization_warnings,
            historical_match=historical_match,
            trace_kwargs={
                "run_id": self.run_logger.run_id,
                "original_filename": pdf_path.name,
                "final_filename": sanitize_final_filename(filename),
                "source_path": str(pdf_path),
                "target_path": str(target_folder / sanitize_final_filename(filename)),
                "archive_path": None,
                "document_type": subtype,
                "classification_reason": mask_sensitive(routing_decision),
                "extracted_invoice_date": document_date,
                "extracted_supplier": mask_sensitive(extracted.supplier_raw),
                "extracted_amount": mask_sensitive(extracted.amount_raw),
                "extraction_method": extracted.source_method,
                "fallback_used": bool(extracted.fallback_used),
                "detected_street_key": street_key,
                "business_context_art": final_art,
                "business_context_reason": mask_sensitive(art_reason),
                "account_konto": None,
                "account_payment_field": payment_field,
                "account_match_source": None,
                "account_match_reason": None,
                "account_matched_rule": None,
                "detected_payment_method": payment_decision.payment_method,
                "payment_rule_name": _extract_rule_name(payment_decision.begruendung),
                "payment_explicit": payment_decision.explicit,
                "payment_signals": _extract_signals(payment_decision.begruendung),
                "priority_rule_name": None,
                "final_assignment_rule_name": "business_non_invoice_document_guard",
                "final_art": final_art,
                "final_konto": None,
                "final_payment_field": payment_field,
                "final_status": "unklar",
                "output_route_rule_name": "non_invoice_business_to_unklar",
                "final_output_folder": unklar_folder,
                "filename_fields_used": [
                    "invoice_date",
                    "document_prefix",
                    "art",
                    "document_name",
                    "amount",
                    "payment_field",
                ],
                "normalization_warnings": normalization_warnings,
                "conflicts": [],
                "routing_decision": routing_decision,
            },
        )

    def _match_document_profile(
        self,
        extracted,
    ) -> tuple[DocumentProfileRule | None, float | None, dict]:
        """Match extracted data against loaded document_profiles.

        Returns (matched_profile, score, meta_dict).
        Returns (None, None, {}) when no profiles are loaded or no match
        exceeds the confidence threshold of the best candidate.

        Matching rules:
        - Search text is built from raw_text, supplier_raw, document_name_raw.
        - negative_hints disqualify the entire profile.
        - score = matched_hints / max(total_hints, 1).
        - Threshold = profile.confidence_threshold.
        - Highest score wins; ties resolved by list order (first wins).
        """
        if not self.document_profiles:
            return None, None, {}

        search_parts: list[str] = []
        if extracted.raw_text:
            search_parts.append(extracted.raw_text.lower())
        if extracted.supplier_raw:
            search_parts.append(extracted.supplier_raw.lower())
        if extracted.document_name_raw:
            search_parts.append(extracted.document_name_raw.lower())
        search_text = " ".join(search_parts)

        best_profile: DocumentProfileRule | None = None
        best_score: float = -1.0

        for profile in self.document_profiles:
            if any(hint.lower() in search_text for hint in profile.negative_hints):
                continue

            total_hints = len(profile.classification_hints)
            matched = sum(
                1
                for hint in profile.classification_hints
                if hint.lower() in search_text
            )
            score = matched / max(total_hints, 1)

            if score > best_score:
                best_score = score
                best_profile = profile

        if best_profile is None:
            return None, None, {}

        meta: dict = {
            "best_profile_id": best_profile.id,
            "best_score": best_score,
            "threshold": best_profile.confidence_threshold,
        }

        if best_score < best_profile.confidence_threshold:
            return None, best_score, meta

        return best_profile, best_score, meta

    def _process_document_with_profile(
        self,
        *,
        pdf_path: Path,
        fingerprint: str,
        extracted,
        classification: ClassificationDecision,
        historical_match: dict | None,
        matched_profile: DocumentProfileRule,
        match_score: float | None,
        match_meta: dict,
    ) -> ProcessResult:
        """Process a non-invoice document using a matched DocumentProfileRule.

        Only called when classify_document_type() == "document" and a profile
        matched above its confidence_threshold.  Never called for invoices.
        Never modifies _process_invoice() or _process_document() behavior.

        Folder selection:
        - target_folder: used when match is above threshold AND no serious
          template problems (missing required placeholders).
        - fallback_folder: used when serious missing placeholders are detected.

        Filename:
        - If naming_template is set: rendered via render_document_filename().
        - If no naming_template: uses the same derivation as _process_document().

        The .pdf extension is appended here if the rendered stem lacks it.
        """
        from invoice_tool.filename_schema import render_document_filename  # noqa: PLC0415

        document_date = self._document_date(extracted.invoice_date_raw)

        # Pass actual values (possibly empty) so render_document_filename can
        # correctly identify and report missing placeholders.
        values: dict[str, str] = {
            "date": document_date,
            "supplier": (extracted.supplier_raw or "").strip().lower(),
            "amount": (extracted.amount_raw or "").strip(),
            "type_literal": (
                matched_profile.type_literal or matched_profile.document_type
            ),
        }

        use_fallback_folder = False
        profile_missing_placeholders: list[str] = []
        profile_missing_required_fields: list[str] = []

        if matched_profile.naming_template:
            render_result = render_document_filename(
                matched_profile.naming_template,
                values,
                fallback_values=matched_profile.fallback_values,
            )
            filename_stem = render_result.filename
            profile_missing_placeholders = list(render_result.missing_placeholders)
            if render_result.missing_placeholders:
                use_fallback_folder = True
        else:
            descriptive_name = self._document_name(extracted)
            filename_stem = (
                f"{document_date}_{self.preset.dokumente.prefix}_"
                f"{descriptive_name}_{self.preset.dokumente.suffix_placeholder}"
            )

        if not filename_stem.lower().endswith(".pdf"):
            filename = filename_stem + ".pdf"
        else:
            filename = filename_stem

        destination = (
            matched_profile.fallback_destination if use_fallback_folder
            else matched_profile.target_destination
        )
        if destination is not None:
            folder_path = resolve_configured_target_directory(
                self.config.ausgangsordner.resolve(),
                destination,
            )
            folder_name = destination.get("path", "")
        else:
            folder_name = (
                matched_profile.fallback_folder if use_fallback_folder
                else matched_profile.target_folder
            )
            folder_path = self._resolve_routing_target_folder(folder_name)

        score_str = f"{match_score:.2f}" if match_score is not None else "n/a"
        routing_decision = (
            f"document_profile='{matched_profile.id}' score={score_str} "
            f"folder={'fallback' if use_fallback_folder else 'target'}='{folder_name}'"
        )
        if profile_missing_placeholders:
            routing_decision += f"; missing_placeholders={profile_missing_placeholders}"
        routing_decision += f"; {classification.begruendung}"

        return self._publish_and_archive(
            pdf_path=pdf_path,
            fingerprint=fingerprint,
            target_folder=folder_path,
            filename=filename,
            routing_status="document",
            dokumenttyp="document",
            extracted=extracted,
            historical_match=historical_match,
            routing_metadata=self._routing_metadata_for_destination(
                destination,
                rule_id=matched_profile.id,
                fallback_used=use_fallback_folder,
                folder_key=folder_name,
            ),
            trace_kwargs={
                "run_id": self.run_logger.run_id,
                "original_filename": pdf_path.name,
                "final_filename": sanitize_final_filename(filename),
                "source_path": str(pdf_path),
                "target_path": str(folder_path / sanitize_final_filename(filename)),
                "archive_path": None,
                "document_type": "document",
                "classification_reason": mask_sensitive(classification.begruendung),
                "extracted_invoice_date": document_date,
                "extracted_supplier": mask_sensitive(extracted.supplier_raw),
                "extracted_amount": mask_sensitive(extracted.amount_raw),
                "extraction_method": extracted.source_method,
                "fallback_used": bool(extracted.fallback_used),
                "detected_street_key": None,
                "business_context_art": None,
                "business_context_reason": None,
                "account_konto": None,
                "account_payment_field": None,
                "account_match_source": None,
                "account_match_reason": None,
                "account_matched_rule": None,
                "detected_payment_method": None,
                "payment_rule_name": None,
                "payment_explicit": None,
                "payment_signals": None,
                "priority_rule_name": None,
                "final_assignment_rule_name": None,
                "final_art": None,
                "final_konto": None,
                "final_payment_field": None,
                "final_status": "document",
                "output_route_rule_name": None,
                "final_output_folder": folder_name,
                "filename_fields_used": [],
                "normalization_warnings": [],
                "conflicts": [],
                "matched_document_profile_id": matched_profile.id,
                "matched_document_profile_score": match_score,
                "document_profile_used_fallback": use_fallback_folder,
                "document_profile_missing_placeholders": profile_missing_placeholders,
                "document_profile_missing_required_fields": profile_missing_required_fields,
                "routing_decision": routing_decision,
            },
        )

    def _handle_duplicate_if_needed(self, pdf_path: Path, fingerprint: str) -> ProcessResult | None:
        if fingerprint in self.run_seen_fingerprints:
            return self._create_duplicate_report(
                pdf_path,
                fingerprint,
                reason="Inhaltsgleiche Datei bereits in diesem Lauf verarbeitet.",
                original_reference=self.run_seen_fingerprints[fingerprint],
            )
        return None

    def _create_duplicate_report(
        self,
        pdf_path: Path,
        fingerprint: str,
        *,
        reason: str,
        original_reference: Path,
    ) -> ProcessResult:
        item_id = self._next_item_id()
        original_path = self._resolve_original_path(pdf_path)
        original_hash, original_size = fingerprint_file(pdf_path), pdf_path.stat().st_size
        record = LifecycleRecord(
            run_id=self.run_logger.run_id,
            item_id=item_id,
            original_path=str(original_path),
            original_filename=original_path.name,
            original_sha256=original_hash,
            original_size=original_size,
            configured_output_root=str(self.config.ausgangsordner.resolve()),
            resolved_target_directory=str(original_reference.parent.resolve()),
            status=STATUS_DUPLICATE,
            output_action="duplicate_same_run",
            verified=False,
            duplicate_of=str(original_reference),
            final_output_path=str(original_reference),
            final_filename=original_reference.name,
            error_code="duplicate_same_run",
            error_message=reason,
        )
        self._persist_lifecycle_record(record)

        archive_result = archive_same_run_duplicate(
            source_path=original_path,
            source_root=self.original_source_dir,
            run_id=self.run_logger.run_id,
            expected_hash=original_hash,
        )

        report_dir = self.config.ausgangsordner / self.preset.duplicate_handling.report_folder
        report_dir.mkdir(parents=True, exist_ok=True)
        report_name = f"{pdf_path.stem}{self.preset.duplicate_handling.report_extension}"
        report_path = unique_target_path(report_dir / report_name)
        historical = self._lookup_processed_fingerprint(fingerprint)
        report_lines = [
            f"duplicate_reason: {reason}",
            f"input_file: {pdf_path}",
            f"fingerprint: {fingerprint}",
            "duplicate_reference_type: same-run",
            f"original_reference: {original_reference}",
            f"historical_storage_path: {historical.get('storage_file') if historical else None}",
            f"source_lifecycle_status: {archive_result.lifecycle_status}",
            f"source_archive_path: {archive_result.archive_path or ''}",
            f"source_archive_result: {'success' if archive_result.success else 'failed'}",
            f"source_archive_error: {archive_result.error or ''}",
        ]
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        self._log_file_event(
            filename=pdf_path.name,
            dokumenttyp="duplicate",
            supplier=None,
            date=None,
            amount=None,
            account=None,
            payment_field=None,
            street=None,
            routing_decision=reason,
            storage_path=original_reference,
            archive_path=archive_result.archive_path,
            fallback_used=False,
            preset_used=self.office_rules.active_preset,
            status=STATUS_DUPLICATE,
            output_action="duplicate_same_run",
            error=reason if archive_result.success else archive_result.error or reason,
        )
        return ProcessResult(
            input_file=pdf_path,
            dokumenttyp="duplicate",
            status=STATUS_DUPLICATE,
            storage_file=original_reference,
            archive_file=archive_result.archive_path,
            used_extractor="duplicate-check",
            fallback_used=False,
            fingerprint=fingerprint,
            art=None,
            original_file=original_path,
            verified_output=False,
            item_id=item_id,
            lifecycle_status=STATUS_DUPLICATE,
            output_action="duplicate_same_run",
            error_code="duplicate_same_run",
            error_message=reason,
            lifecycle_record=record.to_mapping_dict(),
        )

    def _create_historical_reprocessing_report(
        self,
        *,
        input_file: Path,
        fingerprint: str,
        current_storage: Path,
        current_archive: Path,
        historical: dict,
    ) -> Path:
        report_dir = self.config.ausgangsordner / self.preset.duplicate_handling.report_folder
        report_dir.mkdir(parents=True, exist_ok=True)
        report_name = (
            f"{input_file.stem}_historical_reprocess{self.preset.duplicate_handling.report_extension}"
        )
        report_path = unique_target_path(report_dir / report_name)
        report_path.write_text(
            "\n".join(
                [
                    "historical_match_detected: true",
                    "action: current top-level input file was intentionally processed again",
                    f"input_file: {input_file}",
                    f"fingerprint: {fingerprint}",
                    "warning: referenced result may originate from an earlier rule version and is not auto-validated by this run.",
                    f"previous_source_filename: {historical.get('source_filename')}",
                    f"previous_storage_path: {historical.get('storage_file')}",
                    f"previous_archive_path: {historical.get('archive_file')}",
                    f"current_storage_path: {current_storage}",
                    f"current_archive_path: {current_archive}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return report_path

    def _archive_original(self, pdf_path: Path) -> Path:
        original_path = self._resolve_original_path(pdf_path)
        if not original_path.exists():
            raise ProcessorError(
                f"Originaldatei fuer Archivierung nicht gefunden: {original_path}"
            )
        archive_dir = self._ensure_run_archive_dir()
        archive_target = unique_target_path(archive_dir / original_path.name)
        archive_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(original_path), str(archive_target))
        return archive_target

    def _resolve_original_path(self, pdf_path: Path) -> Path:
        resolved = pdf_path.resolve()
        return self.snapshot_to_original.get(resolved, resolved)

    def _report_root(self) -> Path:
        return self.technical_run_dir or self.config.ausgangsordner

    def _verify_output_readable(self, output_path: Path) -> None:
        if not output_path.exists():
            raise ProcessorError(
                f"Output-Verifikation fehlgeschlagen: Datei existiert nicht: {output_path}"
            )
        if not output_path.is_file():
            raise ProcessorError(
                f"Output-Verifikation fehlgeschlagen: kein reguläres File: {output_path}"
            )
        try:
            with output_path.open("rb") as handle:
                handle.read(1)
        except OSError as exc:
            raise ProcessorError(
                f"Output-Verifikation fehlgeschlagen: Datei nicht lesbar: {output_path}"
            ) from exc
        if self._path_is_within(output_path, self.config.eingangsordner):
            raise ProcessorError(
                f"Output-Verifikation fehlgeschlagen: finales Ergebnis liegt im Snapshot: {output_path}"
            )
        archive_root = self.original_source_dir / self.preset.archivierung.basis_ordnername
        if self._path_is_within(output_path, archive_root):
            raise ProcessorError(
                f"Output-Verifikation fehlgeschlagen: finales Ergebnis liegt im Archiv: {output_path}"
            )

    def _write_active_output(
        self,
        source_pdf: Path,
        desired_path: Path,
        *,
        historical_match: dict | None,
    ) -> tuple[Path, str]:
        desired_path.parent.mkdir(parents=True, exist_ok=True)
        previous_active = self._existing_active_storage(historical_match)

        if previous_active is not None and previous_active.exists():
            if previous_active.resolve() == desired_path.resolve():
                self._move_related_variants_to_history(desired_path, keep_path=desired_path)
                return previous_active, "unchanged"
            self._move_to_history(previous_active)
            self._move_related_variants_to_history(desired_path)
            shutil.copy2(source_pdf, desired_path)
            return desired_path, "updated"

        if self._move_related_variants_to_history(desired_path):
            shutil.copy2(source_pdf, desired_path)
            return desired_path, "updated"

        shutil.copy2(source_pdf, desired_path)
        return desired_path, "new"

    def _existing_active_storage(self, historical_match: dict | None) -> Path | None:
        if historical_match is None:
            return None
        storage_file = historical_match.get("storage_file")
        if not isinstance(storage_file, str) or not storage_file:
            return None
        candidate = Path(storage_file)
        if self._is_active_output(candidate):
            return candidate
        return None

    def _is_active_output(self, path: Path) -> bool:
        resolved = path.resolve()
        if self._path_is_within(resolved, self.config.ausgangsordner):
            return True
        if self._path_is_within(resolved, self.preset.dokumente.basis_pfad):
            return True
        for configured in self._configured_destination_paths():
            if self._path_is_within(resolved, configured):
                return True
        return False

    def _routing_metadata_for_folder_key(
        self,
        folder_key: str,
        *,
        rule_id: str | None = None,
        fallback_used: bool = False,
    ) -> dict[str, str | bool | None]:
        destination = self.folder_destinations.get(folder_key)
        if destination is None:
            mapped = self.preset.routing.zielordner.get(folder_key, folder_key)
            return {
                "rule_id": rule_id or folder_key,
                "destination_mode": "relative_to_output_root",
                "configured_destination_path": str(mapped),
                "fallback_used": fallback_used,
            }
        return {
            "rule_id": rule_id or folder_key,
            "destination_mode": destination.get("mode"),
            "configured_destination_path": destination.get("path"),
            "fallback_used": fallback_used,
        }

    def _routing_metadata_for_destination(
        self,
        destination: dict[str, str] | None,
        *,
        rule_id: str | None = None,
        fallback_used: bool = False,
        folder_key: str | None = None,
    ) -> dict[str, str | bool | None]:
        if destination is not None:
            return {
                "rule_id": rule_id,
                "destination_mode": destination.get("mode"),
                "configured_destination_path": destination.get("path"),
                "fallback_used": fallback_used,
            }
        if folder_key is not None:
            return self._routing_metadata_for_folder_key(
                folder_key,
                rule_id=rule_id,
                fallback_used=fallback_used,
            )
        return {
            "rule_id": rule_id,
            "destination_mode": None,
            "configured_destination_path": None,
            "fallback_used": fallback_used,
        }

    def _resolve_routing_target_folder(self, folder_key: str) -> Path:
        return resolve_routing_folder_key(
            folder_key,
            output_root=self.config.ausgangsordner.resolve(),
            folder_destinations=self.folder_destinations,
            zielordner_map=self.preset.routing.zielordner,
        )

    def _configured_destination_paths(self) -> list[Path]:
        paths: list[Path] = []
        output_root = self.config.ausgangsordner.resolve()
        for destination in self.folder_destinations.values():
            try:
                paths.append(
                    resolve_configured_target_directory(output_root, destination)
                )
            except Exception:  # noqa: BLE001
                continue
        return paths

    def _path_is_within(self, path: Path, base: Path) -> bool:
        try:
            path.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

    def _move_to_history(self, active_path: Path) -> Path:
        history_root = self.config.ausgangsordner / "_history" / self.run_logger.run_id
        history_root.mkdir(parents=True, exist_ok=True)
        relative_path = self._history_relative_path(active_path)
        history_target = unique_target_path(history_root / relative_path)
        history_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(active_path), str(history_target))
        return history_target

    def _move_related_variants_to_history(
        self, desired_path: Path, *, keep_path: Path | None = None
    ) -> bool:
        moved_any = False
        pattern = f"{desired_path.stem}*{desired_path.suffix}"
        keep_resolved = keep_path.resolve() if keep_path is not None and keep_path.exists() else None
        for candidate in sorted(desired_path.parent.glob(pattern)):
            if not candidate.is_file():
                continue
            if keep_resolved is not None and candidate.resolve() == keep_resolved:
                continue
            self._move_to_history(candidate)
            moved_any = True
        return moved_any

    def _history_relative_path(self, active_path: Path) -> Path:
        resolved_active = active_path.resolve()
        output_root = self.config.ausgangsordner.resolve()
        documents_root = self.preset.dokumente.basis_pfad.resolve()
        try:
            return resolved_active.relative_to(output_root)
        except ValueError:
            try:
                return Path("documents") / resolved_active.relative_to(documents_root)
            except ValueError:
                return Path(active_path.name)

    def _ensure_run_archive_dir(self) -> Path:
        if self.run_archive_dir is not None:
            return self.run_archive_dir
        archive_root = self.original_source_dir / self.preset.archivierung.basis_ordnername
        archive_root.mkdir(parents=True, exist_ok=True)
        candidate = archive_root / self.run_logger.run_id
        if not candidate.exists():
            candidate.mkdir()
            self.run_archive_dir = candidate
            self.log(f"Archivordner fuer diesen Lauf: {self.run_archive_dir}")
            return candidate

        index = 2
        while True:
            suffixed = archive_root / f"{self.run_logger.run_id}_{index}"
            if not suffixed.exists():
                suffixed.mkdir()
                self.run_archive_dir = suffixed
                self.log(f"Archivordner fuer diesen Lauf: {self.run_archive_dir}")
                return suffixed
            index += 1

    def _document_date(self, raw_date: str | None) -> str:
        if raw_date:
            try:
                return normalize_invoice_date(raw_date)
            except NormalizationError:
                pass
        return datetime.now().strftime("%y%m%d")

    def _document_name(self, extracted) -> str:
        if extracted.document_name_raw:
            try:
                return sanitize_document_name(
                    extracted.document_name_raw,
                    max_words=self.preset.dokumente.max_woerter,
                )
            except NormalizationError:
                pass

        searchable_text = " ".join(
            part
            for part in [
                extracted.raw_text,
                extracted.supplier_raw or "",
                " ".join(extracted.provider_mentions),
                " ".join(extracted.address_fragments),
            ]
            if part
        ).lower()
        for rule in self.preset.dokumente.schlagwoerter:
            if any(hint.lower() in searchable_text for hint in rule.hinweise):
                return rule.name
        return self.preset.dokumente.fallback_name

    def _log_output_size(self, output_file: Path) -> None:
        size_kb = output_file.stat().st_size / 1024
        if size_kb > self.config.zielgroesse_kb:
            self.log(
                f"Hinweis: {output_file.name} ist {size_kb:.1f} kB gross und ueberschreitet das Ziel von {self.config.zielgroesse_kb} kB. "
                "Die vollstaendige Original-PDF wurde bewusst unveraendert beibehalten."
            )

    def _log_file_event(
        self,
        *,
        filename: str,
        dokumenttyp: str,
        supplier: str | None,
        date: str | None,
        amount: str | None,
        account: str | None,
        payment_field: str | None,
        street: str | None,
        routing_decision: str | None,
        storage_path: Path | None,
        archive_path: Path | None,
        fallback_used: bool | None,
        preset_used: str,
        status: str,
        output_action: str | None,
        error: str | None,
    ) -> None:
        self.run_logger.log_file_summary(
            {
                "filename": filename,
                "type": dokumenttyp,
                "supplier": supplier,
                "date": date,
                "amount": amount,
                "account": account,
                "payment_field": payment_field,
                "street": street,
                "routing_decision": routing_decision,
                "storage_path": str(storage_path) if storage_path else None,
                "archive_path": str(archive_path) if archive_path else None,
                "fallback_used": fallback_used,
                "preset_used": preset_used,
                "status": status,
                "output_action": output_action,
                "error": error,
            }
        )

    def log(self, message: str) -> None:
        self.run_logger.log(message)


# ---------------------------------------------------------------------------
# Module-level helpers for trace extraction (no side effects, pure string ops)
# ---------------------------------------------------------------------------

def _extract_rule_name(begruendung: str) -> str | None:
    """Extract rule name from begruendung strings like \"Regel 'foo' getroffen.\"."""
    import re
    match = re.search(r"'([^']+)'", begruendung)
    return match.group(1) if match else None


def _extract_signals(begruendung: str) -> str | None:
    """Extract signal list from payment begruendung strings like \"Signale: x, y.\"."""
    import re
    match = re.search(r"Signale:\s*(.+?)\.?\s*$", begruendung)
    return match.group(1).strip() if match else None
