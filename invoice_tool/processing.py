from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from invoice_tool.classification import classify_document_type
from invoice_tool.config import load_office_rules
from invoice_tool.extraction import ExtractionCoordinator
from invoice_tool.filename_schema import build_filename
from invoice_tool.logging_utils import RunLogger
from invoice_tool.models import (
    AppConfig,
    ClassificationDecision,
    NormalizedInvoice,
    OfficeRules,
    ProcessResult,
)
from invoice_tool.normalization import (
    NormalizationError,
    normalize_invoice_date,
    normalize_invoice_with_fallbacks,
    sanitize_document_name,
)
from invoice_tool.routing import (
    apply_final_assignment,
    determine_business_context,
    detect_street,
    detect_payment_method,
    resolve_account,
)
from invoice_tool.state import (
    DirectoryLock,
    ensure_runtime_dirs,
    fingerprint_file,
    load_processed_state,
    path_token,
    save_processed_state,
)


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
    ) -> None:
        self.config = config
        self.office_rules = office_rules or load_office_rules(
            config.regeln_datei,
            active_preset_override=config.aktives_preset,
        )
        self.preset = self.office_rules.preset
        self.extractor = extractor
        self.run_logger = logger or RunLogger(self.config.log_ordner)

        self.config.ausgangsordner.mkdir(parents=True, exist_ok=True)
        self.preset.dokumente.basis_pfad.mkdir(parents=True, exist_ok=True)
        self.config.runtime_ordner.mkdir(parents=True, exist_ok=True)
        self.config.log_ordner.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.config.runtime_ordner / "state"
        ensure_runtime_dirs(self.state_dir)
        self.state_file = self.state_dir / "processed_state.json"
        self.run_archive_dir: Path | None = None
        self.run_seen_fingerprints: dict[str, Path] = {}

    def process_all(self) -> list[ProcessResult]:
        self.run_archive_dir = None
        self.run_seen_fingerprints = {}
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
            self.config.ausgangsordner,
            preset=self.office_rules.active_preset,
            input_count=len(pdf_files),
        )
        self.log(f"Run-Report geschrieben: {report_path}")
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
                if classification.dokumenttyp == "invoice":
                    result = self._process_invoice(
                        pdf_path=pdf_path,
                        fingerprint=fingerprint,
                        extracted=extracted,
                        classification=classification,
                        historical_match=historical_match,
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
        art, art_reason = determine_business_context(extracted, account_decision, self.preset)
        payment_decision = detect_payment_method(extracted, self.preset)
        routing = apply_final_assignment(
            art=art,
            payment_decision=payment_decision,
            account_decision=account_decision,
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

        target_folder = self.config.ausgangsordner / routing.zielordner
        target_folder.mkdir(parents=True, exist_ok=True)
        output_target, output_action = self._write_active_output(
            pdf_path,
            target_folder / filename,
            historical_match=historical_match,
        )

        archive_target = self._archive_original(pdf_path)
        self._remember_processed(
            fingerprint=fingerprint,
            dokumenttyp="invoice",
            status=routing.status,
            normalized=normalized,
            output_target=output_target,
            archive_target=archive_target,
            used_extractor=extracted.source_method,
            fallback_used=bool(extracted.fallback_used),
            konto=routing.konto,
            payment_field=routing.payment_field,
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
        self._log_file_event(
            filename=pdf_path.name,
            dokumenttyp="invoice",
            supplier=normalized.supplier,
            date=normalized.invoice_date,
            amount=normalized.amount,
            account=routing.konto,
            payment_field=routing.payment_field,
            street=street_key,
            routing_decision=(
                f"{routing.zielordner} ({routing.begruendung}); Klassifikation={classification.begruendung}; "
                f"Art={routing.art} ({art_reason}); Payment={routing.payment_field} ({payment_decision.begruendung}); "
                f"Normalisierung={'; '.join(normalization_warnings) if normalization_warnings else 'ok'}"
                + (
                    f"; Historischer Treffer erneut verarbeitet, Report={historical_report}"
                    if historical_report is not None
                    else ""
                )
            ),
            storage_path=output_target,
            archive_path=archive_target,
            fallback_used=bool(extracted.fallback_used),
            preset_used=self.office_rules.active_preset,
            status=routing.status,
            output_action=output_action,
            error=None,
        )
        return ProcessResult(
            input_file=pdf_path,
            dokumenttyp="invoice",
            status=routing.status,
            storage_file=output_target,
            archive_file=archive_target,
            used_extractor=extracted.source_method,
            fallback_used=bool(extracted.fallback_used),
            fingerprint=fingerprint,
            supplier=normalized.supplier,
            date=normalized.invoice_date,
            amount=normalized.amount,
            art=routing.art,
            konto=routing.konto,
            payment_field=routing.payment_field,
            street=street_key,
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
        output_target, output_action = self._write_active_output(
            pdf_path,
            self.preset.dokumente.basis_pfad / filename,
            historical_match=historical_match,
        )

        archive_target = self._archive_original(pdf_path)
        self._remember_processed(
            fingerprint=fingerprint,
            dokumenttyp="document",
            status="document",
            normalized=None,
            output_target=output_target,
            archive_target=archive_target,
            used_extractor=extracted.source_method,
            fallback_used=bool(extracted.fallback_used),
            konto=None,
            payment_field=None,
            street=None,
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
        self._log_file_event(
            filename=pdf_path.name,
            dokumenttyp="document",
            supplier=extracted.supplier_raw,
            date=document_date,
            amount=extracted.amount_raw,
            account=None,
            payment_field=None,
            street=None,
            routing_decision=classification.begruendung
            + (
                f"; Historischer Treffer erneut verarbeitet, Report={historical_report}"
                if historical_report is not None
                else ""
            ),
            storage_path=output_target,
            archive_path=archive_target,
            fallback_used=bool(extracted.fallback_used),
            preset_used=self.office_rules.active_preset,
            status="document",
            output_action=output_action,
            error=None,
        )
        return ProcessResult(
            input_file=pdf_path,
            dokumenttyp="document",
            status="document",
            storage_file=output_target,
            archive_file=archive_target,
            used_extractor=extracted.source_method,
            fallback_used=bool(extracted.fallback_used),
            fingerprint=fingerprint,
            supplier=extracted.supplier_raw,
            date=document_date,
            amount=extracted.amount_raw,
            art=None,
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
        report_dir = self.config.ausgangsordner / self.preset.duplicate_handling.report_folder
        report_dir.mkdir(parents=True, exist_ok=True)
        report_name = f"{pdf_path.stem}{self.preset.duplicate_handling.report_extension}"
        report_path = unique_target_path(report_dir / report_name)
        historical = self._lookup_processed_fingerprint(fingerprint)
        original_filename = None
        historical_storage = None
        historical_archive = None
        if historical:
            original_filename = historical.get("source_filename")
            historical_storage = historical.get("storage_file")
            historical_archive = historical.get("archive_file")
        report_path.write_text(
            "\n".join(
                [
                    f"duplicate_reason: {reason}",
                    f"input_file: {pdf_path}",
                    f"fingerprint: {fingerprint}",
                    f"duplicate_reference_type: {'historical' if 'historisch' in reason.lower() else 'same-run'}",
                    "warning: referenced result may originate from an earlier rule version and is not auto-validated by this run.",
                    f"historical_source_filename: {original_filename}",
                    f"original_reference: {original_reference}",
                    f"historical_storage_path: {historical_storage}",
                    f"historical_archive_path: {historical_archive}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        archive_target = self._archive_original(pdf_path)
        self.run_seen_fingerprints[fingerprint] = original_reference
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
            storage_path=report_path,
            archive_path=archive_target,
            fallback_used=False,
            preset_used=self.office_rules.active_preset,
            status="duplicate",
            output_action="new",
            error=None,
        )
        return ProcessResult(
            input_file=pdf_path,
            dokumenttyp="duplicate",
            status="duplicate",
            storage_file=report_path,
            archive_file=archive_target,
            used_extractor="duplicate-check",
            fallback_used=False,
            fingerprint=fingerprint,
            art=None,
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
        archive_dir = self._ensure_run_archive_dir()
        archive_target = unique_target_path(archive_dir / pdf_path.name)
        archive_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf_path), str(archive_target))
        return archive_target

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
        return self._path_is_within(path, self.config.ausgangsordner) or self._path_is_within(
            path, self.preset.dokumente.basis_pfad
        )

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
        archive_root = self.config.eingangsordner / self.preset.archivierung.basis_ordnername
        archive_root.mkdir(parents=True, exist_ok=True)
        run_base = f"{datetime.now().strftime('%y%m%d')}_{self.preset.archivierung.lauf_ordner_suffix}"
        candidate = archive_root / run_base
        if not candidate.exists():
            candidate.mkdir()
            self.run_archive_dir = candidate
            self.log(f"Archivordner fuer diesen Lauf: {self.run_archive_dir}")
            return candidate

        index = 2
        while True:
            suffixed = archive_root / f"{run_base}{index}"
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
