"""Transaction-safe lifecycle and output-routing tests for RUN-001.

Uses synthetic PDFs under tmp_path only. No real user documents.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from invoice_tool.extraction import ExtractedData
from invoice_tool.models import DocumentProfileRule
from invoice_tool.processing import InvoiceProcessor
from invoice_tool.run import (
    build_run_config,
    create_run_snapshot,
    discover_source_pdfs,
    run_once,
)


def _make_pdf(path: Path, content: str = "Synthetic test PDF") -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    doc.save(str(path))
    doc.close()
    return path


class StubExtractor:
    def __init__(self, extracted: ExtractedData) -> None:
        self.extracted = extracted

    def extract(self, pdf_path: Path, *, log):
        return self.extracted


class FailingExtractor:
    def extract(self, pdf_path: Path, *, log):
        raise RuntimeError("simulated extraction failure")


def _make_run_config_path(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "output"
    documents_dir = tmp_path / "documents"
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"

    rules_data = json.loads(Path("office_rules.json").read_text(encoding="utf-8"))
    rules_data["presets"]["office_default"]["dokumente"]["basis_pfad"] = str(documents_dir)
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "eingangsordner": str(input_dir),
                "ausgangsordner": str(output_dir),
                "api_key_pfad": str(tmp_path / ".env"),
                "archiv_aktiv": True,
                "regeln_datei": str(rules_path),
                "aktives_preset": "office_default",
                "runtime_ordner": str(runtime_dir),
                "log_ordner": str(logs_dir),
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("OPENAI_API_KEY=test-key\n")
    return config_path


def _patch_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    support = tmp_path / "Application Support" / "KI-Rechnungen"
    support.mkdir(parents=True)
    monkeypatch.setattr("invoice_tool.app_paths.user_support_dir", lambda: support)
    return support


def _invoice_extractor() -> StubExtractor:
    return StubExtractor(
        ExtractedData(
            invoice_date_raw="20.03.2026",
            supplier_raw="Acme Ltd",
            amount_raw="10,00",
            invoice_number_raw="INV-1",
            raw_text="Invoice",
            source_method="openai",
        )
    )


def test_discover_source_pdfs_ignores_archive_subtree(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "active.pdf")
    archive_dir = source / "archiv"
    archive_dir.mkdir()
    _make_pdf(archive_dir / "archived.pdf")

    discovered = discover_source_pdfs(source)
    assert [p.name for p in discovered] == ["active.pdf"]


def test_build_run_config_writes_final_output_to_user_root(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config

    config_path = _make_run_config_path(tmp_path)
    base_config = load_app_config(config_path)
    run_dir = tmp_path / "technical" / "run-001"
    run_dir.mkdir(parents=True)
    snapshot_dir = run_dir / "input_snapshot"
    snapshot_dir.mkdir()
    user_output = tmp_path / "user-output"

    run_config = build_run_config(base_config, run_dir, snapshot_dir, user_output)

    assert run_config.eingangsordner == snapshot_dir
    assert run_config.ausgangsordner == user_output.resolve()
    assert run_config.runtime_ordner == run_dir / "runtime"
    assert run_config.log_ordner == run_dir / "logs"


def test_run_once_writes_final_copy_and_archives_original_after_verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support = _patch_support(tmp_path, monkeypatch)
    config_path = _make_run_config_path(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    original = _make_pdf(source / "invoice.pdf", "Invoice Acme")

    user_output = tmp_path / "user-output"

    with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
        with patch("invoice_tool.run.OpenAIVisionExtractor"):
            with patch("invoice_tool.run.ExtractionCoordinator") as mock_coord:
                mock_coord.return_value.extract.side_effect = (
                    lambda pdf_path, log: _invoice_extractor().extract(pdf_path, log=log)
                )
                run_dir = run_once(
                    source=source,
                    output=user_output,
                    config_path=config_path,
                )

    assert run_dir.parent == support / "runs"
    assert (run_dir / "input_snapshot" / "invoice.pdf").exists()
    assert original.exists() is False

    archive_dirs = list((source / "archiv").iterdir())
    assert len(archive_dirs) == 1
    archived = archive_dirs[0] / "invoice.pdf"
    assert archived.exists()
    assert archived.read_bytes() == (run_dir / "input_snapshot" / "invoice.pdf").read_bytes()

    final_files = list(user_output.rglob("*.pdf"))
    assert len(final_files) == 1
    assert final_files[0].parent != run_dir
    assert "input_snapshot" not in str(final_files[0])
    assert "archiv" not in str(final_files[0])

    mapping = json.loads((run_dir / "output_mapping.json").read_text(encoding="utf-8"))
    entry = mapping["mappings"][0]
    assert entry["original_path"].endswith("source/invoice.pdf")
    assert entry["verified"] is True
    assert entry["final_output_path"] is not None
    assert entry["status"] == "success"


def test_failed_output_leaves_original_in_active_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_support(tmp_path, monkeypatch)
    config_path = _make_run_config_path(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    original = _make_pdf(source / "broken.pdf")

    user_output = tmp_path / "user-output"

    with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
        with patch("invoice_tool.run.OpenAIVisionExtractor"):
            with patch("invoice_tool.run.ExtractionCoordinator") as mock_coord:
                mock_coord.return_value.extract.side_effect = FailingExtractor().extract
                run_dir = run_once(
                    source=source,
                    output=user_output,
                    config_path=config_path,
                )

    assert original.exists()
    archive_matches = list((source / "archiv").rglob("broken.pdf")) if (source / "archiv").exists() else []
    assert not archive_matches
    assert list(user_output.rglob("*.pdf")) == []

    mapping = json.loads((run_dir / "output_mapping.json").read_text(encoding="utf-8"))
    assert mapping["mappings"] == []


def test_final_files_never_remain_only_in_snapshot_or_archive(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config, load_office_rules

    config_path, rules_path, _input_dir, output_dir, _documents_dir = _make_direct_setup(tmp_path)
    source = tmp_path / "active-source"
    source.mkdir()
    snapshot_dir = tmp_path / "technical" / "input_snapshot"
    snapshot_dir.mkdir(parents=True)
    original = _make_pdf(source / "invoice.pdf")
    snapshot_copy = snapshot_dir / "invoice.pdf"
    snapshot_copy.write_bytes(original.read_bytes())

    config = build_run_config(
        load_app_config(config_path),
        tmp_path / "technical" / "run",
        snapshot_dir,
        output_dir,
    )
    rules = load_office_rules(rules_path)

    processor = InvoiceProcessor(
        config,
        _invoice_extractor(),
        office_rules=rules,
        original_source_dir=source,
        snapshot_to_original={snapshot_copy.resolve(): original.resolve()},
        technical_run_dir=tmp_path / "technical" / "run",
    )
    results = processor.process_all()

    assert len(results) == 1
    assert results[0].verified_output is True
    assert not original.exists()
    assert snapshot_copy.exists()
    assert list(output_dir.rglob("*.pdf"))
    for final in output_dir.rglob("*.pdf"):
        assert "input_snapshot" not in str(final)


def test_duplicate_does_not_report_verified_final_output(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config, load_office_rules

    config_path, rules_path, input_dir, _output_dir, _documents_dir = _make_direct_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)

    pdf_bytes = _make_pdf(input_dir / "first.pdf").read_bytes()
    (input_dir / "second.pdf").write_bytes(pdf_bytes)

    processor = InvoiceProcessor(config, _invoice_extractor(), office_rules=rules)
    results = processor.process_all()

    assert len(results) == 2
    duplicate = next(result for result in results if result.status == "duplicate")
    assert duplicate.verified_output is False


def test_profile_naming_schema_applied_to_real_output_file(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config, load_office_rules

    config_path, rules_path, input_dir, output_dir, _documents_dir = _make_direct_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)

    _make_pdf(input_dir / "contract.pdf", "Mietvertrag rental contract")

    profile = DocumentProfileRule(
        id="rental",
        label="Rental",
        document_type="document",
        classification_hints=("mietvertrag", "rental contract"),
        negative_hints=(),
        target_folder="contracts",
        fallback_folder="unklar",
        confidence_threshold=0.5,
        duplicate_policy="keep",
        naming_template="{date}_{type_literal}",
        type_literal="mietvertrag",
        fallback_values={},
    )

    processor = InvoiceProcessor(
        config,
        StubExtractor(
            ExtractedData(
                invoice_date_raw="01.01.2026",
                supplier_raw="Landlord GmbH",
                amount_raw=None,
                document_name_raw="Mietvertrag",
                raw_text="Mietvertrag rental contract",
                source_method="openai",
            )
        ),
        office_rules=rules,
        document_profiles=[profile],
    )
    results = processor.process_all()
    assert len(results) == 1
    final = results[0].storage_file
    assert final.exists()
    assert final.name.startswith("260101_mietvertrag")
    assert final.parent == output_dir / "contracts"


def test_technical_run_data_stored_separately_from_user_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support = _patch_support(tmp_path, monkeypatch)
    config_path = _make_run_config_path(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    _make_pdf(source / "invoice.pdf")
    user_output = tmp_path / "user-output"

    with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
        with patch("invoice_tool.run.OpenAIVisionExtractor"):
            with patch("invoice_tool.run.ExtractionCoordinator") as mock_coord:
                mock_coord.return_value.extract.side_effect = (
                    lambda pdf_path, log: _invoice_extractor().extract(pdf_path, log=log)
                )
                run_dir = run_once(
                    source=source,
                    output=user_output,
                    config_path=config_path,
                )

    assert run_dir.is_relative_to(support / "runs")
    assert (run_dir / "runtime").exists()
    assert (run_dir / "logs").exists()
    assert (run_dir / "input_snapshot").exists()
    assert not (user_output / "runtime").exists()
    assert not (user_output / "logs").exists()
    assert not (user_output / "input_snapshot").exists()
    report_root = run_dir / "_runs"
    assert report_root.exists()


def test_no_source_file_overwritten_or_lost_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_support(tmp_path, monkeypatch)
    config_path = _make_run_config_path(tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    original = _make_pdf(source / "invoice.pdf")
    original_bytes = original.read_bytes()

    user_output = tmp_path / "user-output"

    with patch("invoice_tool.run.TesseractExtractor", side_effect=Exception("no tesseract")):
        with patch("invoice_tool.run.OpenAIVisionExtractor"):
            with patch("invoice_tool.run.ExtractionCoordinator") as mock_coord:
                mock_coord.return_value.extract.side_effect = (
                    lambda pdf_path, log: _invoice_extractor().extract(pdf_path, log=log)
                )
                run_once(source=source, output=user_output, config_path=config_path)

    archived = next((source / "archiv").rglob("invoice.pdf"))
    assert archived.read_bytes() == original_bytes
    final = next(user_output.rglob("*.pdf"))
    assert final.read_bytes() == original_bytes
    assert not original.exists()


def _make_direct_setup(tmp_path: Path):
    config_path = _make_run_config_path(tmp_path)
    rules_path = tmp_path / "rules.json"
    input_dir = tmp_path / "input"
    input_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "output"
    documents_dir = tmp_path / "documents"
    return config_path, rules_path, input_dir, output_dir, documents_dir


def test_create_run_snapshot_returns_original_mapping(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    original = _make_pdf(source / "invoice.pdf")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    snapshot_dir, mapping = create_run_snapshot(source, run_dir)

    snapshot_file = snapshot_dir / "invoice.pdf"
    assert mapping[snapshot_file.resolve()] == original.resolve()
    assert snapshot_file.exists()
    assert original.exists()


def test_same_run_duplicate_preserves_second_source(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.file_lifecycle import STATUS_DUPLICATE

    config_path, rules_path, input_dir, output_dir, _documents_dir = _make_direct_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)

    pdf_bytes = _make_pdf(input_dir / "first.pdf").read_bytes()
    (input_dir / "second.pdf").write_bytes(pdf_bytes)

    processor = InvoiceProcessor(config, _invoice_extractor(), office_rules=rules)
    results = processor.process_all()

    assert len(results) == 2
    success = [r for r in results if r.lifecycle_status == "success"]
    duplicate = [r for r in results if r.lifecycle_status == STATUS_DUPLICATE]
    assert len(success) == 1
    assert len(duplicate) == 1
    assert duplicate[0].verified_output is False
    assert not (input_dir / "second.pdf").exists()
    run_id = processor.run_logger.run_id
    assert (input_dir / "archiv" / run_id / "duplikate" / "second.pdf").exists()


def test_output_path_same_content_duplicate_preserves_source(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.file_lifecycle import STATUS_DUPLICATE

    config_path, rules_path, input_dir, output_dir, _documents_dir = _make_direct_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)

    pdf_bytes = _make_pdf(input_dir / "only.pdf", "Invoice Acme duplicate path").read_bytes()

    processor = InvoiceProcessor(config, _invoice_extractor(), office_rules=rules)
    first = processor.process_all()
    assert first[0].lifecycle_status == "success"
    final_path = first[0].storage_file

    (input_dir / "only2.pdf").write_bytes(pdf_bytes)
    processor2 = InvoiceProcessor(config, _invoice_extractor(), office_rules=rules)
    second = processor2.process_all()
    dup_results = [r for r in second if r.lifecycle_status == STATUS_DUPLICATE]
    assert dup_results
    assert final_path.read_bytes() == pdf_bytes
    assert (input_dir / "only2.pdf").exists()


def test_collision_renamed_uses_double_underscore_suffix(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.file_lifecycle import STATUS_COLLISION_RENAMED

    config_path, rules_path, input_dir, output_dir, _documents_dir = _make_direct_setup(tmp_path)
    config = load_app_config(config_path)
    rules = load_office_rules(rules_path)

    _make_pdf(input_dir / "invoice.pdf", "Invoice Acme collision")
    blocker = output_dir / "private"
    blocker.mkdir(parents=True)
    _make_pdf(blocker / "260320_er_private_acme-ltd_10.00_unklar.pdf", "Different content")

    processor = InvoiceProcessor(config, _invoice_extractor(), office_rules=rules)
    results = processor.process_all()

    assert len(results) == 1
    assert results[0].lifecycle_status == STATUS_COLLISION_RENAMED
    assert results[0].storage_file.name.endswith("__2.pdf")
    assert blocker.joinpath("260320_er_private_acme-ltd_10.00_unklar.pdf").read_bytes() != results[0].storage_file.read_bytes()


def test_path_traversal_in_target_folder_is_rejected(tmp_path: Path) -> None:
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.file_lifecycle import resolve_safe_target_directory, PathSafetyError

    output_root = tmp_path / "output"
    output_root.mkdir()
    with pytest.raises(PathSafetyError):
        resolve_safe_target_directory(output_root, "../escape")


def test_sanitize_final_filename_rejects_unsafe_names() -> None:
    from invoice_tool.file_lifecycle import sanitize_final_filename

    assert sanitize_final_filename("../evil.pdf").endswith(".pdf")
    assert "/" not in sanitize_final_filename("bad/name.pdf")
    assert sanitize_final_filename("").endswith(".pdf")


def test_atomic_mapping_written_via_temp_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.file_lifecycle import OutputMappingStore, LifecycleRecord

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    store = OutputMappingStore(run_dir, "run-001")
    store.add_or_replace(
        LifecycleRecord(
            run_id="run-001",
            item_id="item-0001",
            original_path=str(tmp_path / "in.pdf"),
            original_filename="in.pdf",
            original_sha256="abc",
            original_size=10,
            configured_output_root=str(tmp_path / "out"),
            resolved_target_directory=str(tmp_path / "out"),
            status="success",
            verified=True,
        )
    )
    path = store.flush()
    assert path.exists()
    assert not (run_dir / ".output_mapping.json.tmp").exists()


def test_create_run_support_dir_same_second_unique(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invoice_tool.app_paths as app_paths

    support = tmp_path / "support"
    monkeypatch.setattr(app_paths, "user_support_dir", lambda: support)

    first, first_id = app_paths.create_run_support_dir(run_id="20260708_999999")
    second, second_id = app_paths.create_run_support_dir(run_id="20260708_999999")
    assert first != second
    assert second_id == "20260708_999999_2"


def test_archive_failure_keeps_output_and_active_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.file_lifecycle import STATUS_ARCHIVE_FAILED, OutputMappingStore

    config_path, rules_path, input_dir, output_dir, _documents_dir = _make_direct_setup(tmp_path)
    source = tmp_path / "active-source"
    source.mkdir()
    original = _make_pdf(source / "invoice.pdf")
    snapshot_dir = tmp_path / "snap"
    snapshot_dir.mkdir()
    snapshot_copy = snapshot_dir / "invoice.pdf"
    snapshot_copy.write_bytes(original.read_bytes())

    config = load_app_config(config_path)
    config = __import__("dataclasses").replace(
        config,
        eingangsordner=snapshot_dir,
        ausgangsordner=output_dir,
    )
    rules = load_office_rules(rules_path)

    run_dir = tmp_path / "technical-run"
    run_dir.mkdir(parents=True)

    processor = InvoiceProcessor(
        config,
        _invoice_extractor(),
        office_rules=rules,
        original_source_dir=source,
        snapshot_to_original={snapshot_copy.resolve(): original.resolve()},
        technical_run_dir=run_dir,
        mapping_store=OutputMappingStore(run_dir, "run-archive"),
    )

    def fail_archive(*args, **kwargs):
        raise __import__("invoice_tool.file_lifecycle", fromlist=["LifecycleError"]).LifecycleError(
            "simulated archive failure",
            code="archive_simulated",
            status=STATUS_ARCHIVE_FAILED,
        )

    monkeypatch.setattr(
        "invoice_tool.processing.archive_original_safely",
        fail_archive,
    )

    results = processor.process_all()
    assert len(results) == 1
    assert results[0].lifecycle_status == STATUS_ARCHIVE_FAILED
    assert results[0].verified_output is True
    assert original.exists()
    assert list(output_dir.rglob("*.pdf"))


def test_retry_after_archive_failure_reuses_verified_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.file_lifecycle import (
        LifecycleRecord,
        OutputMappingStore,
        STATUS_ARCHIVE_FAILED,
        STATUS_SUCCESS,
    )

    config_path, rules_path, input_dir, output_dir, _documents_dir = _make_direct_setup(tmp_path)
    source = tmp_path / "active-source"
    source.mkdir()
    original = _make_pdf(source / "invoice.pdf")
    snapshot_dir = tmp_path / "snap"
    snapshot_dir.mkdir()
    snapshot_copy = snapshot_dir / "invoice.pdf"
    snapshot_copy.write_bytes(original.read_bytes())

    config = load_app_config(config_path)
    config = __import__("dataclasses").replace(
        config,
        eingangsordner=snapshot_dir,
        ausgangsordner=output_dir,
    )
    rules = load_office_rules(rules_path)
    run_dir = tmp_path / "technical-run"
    run_dir.mkdir(parents=True)
    mapping_store = OutputMappingStore(run_dir, "run-retry")

    processor = InvoiceProcessor(
        config,
        _invoice_extractor(),
        office_rules=rules,
        original_source_dir=source,
        snapshot_to_original={snapshot_copy.resolve(): original.resolve()},
        technical_run_dir=run_dir,
        mapping_store=mapping_store,
    )

    call_count = {"n": 0}

    def flaky_archive(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise __import__("invoice_tool.file_lifecycle", fromlist=["LifecycleError"]).LifecycleError(
                "first archive fails",
                code="archive_simulated",
                status=STATUS_ARCHIVE_FAILED,
            )
        return __import__("invoice_tool.file_lifecycle", fromlist=["archive_original_safely"]).archive_original_safely(
            *args, **kwargs
        )

    monkeypatch.setattr("invoice_tool.processing.archive_original_safely", flaky_archive)

    first = processor.process_all()
    assert first[0].lifecycle_status == STATUS_ARCHIVE_FAILED
    outputs_after_first = list(output_dir.rglob("*.pdf"))
    assert len(outputs_after_first) == 1

    second = processor.process_all()
    assert second[0].lifecycle_status == STATUS_SUCCESS
    assert len(list(output_dir.rglob("*.pdf"))) == 1
