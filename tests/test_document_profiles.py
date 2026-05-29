"""Tests for document_profiles step 8b.

Covers:
- Compiler: _compile_document_profiles() and compile_profile_to_rules() extension
- Renderer: render_document_filename()
- Matcher: _match_document_profile()
- Runtime integration: _process_one() document branch with and without profiles
- Regression: invoice path unchanged, no-profile path unchanged
"""
from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from invoice_tool.config import load_document_profiles_from_runtime_rules
from invoice_tool.filename_schema import (
    DocumentFilenameResult,
    render_document_filename,
)
from invoice_tool.models import DocumentProfileRule, ExtractedData
from invoice_tool.profile_compiler import (
    _compile_document_profiles,
    compile_profile_to_rules,
)


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_folders(*entries: tuple[str, str]) -> list[dict]:
    """Build a minimal folders list from (id, folder_name) tuples."""
    return [{"id": fid, "folder_name": fname} for fid, fname in entries]


def _make_doc_profile(**kwargs) -> dict:
    """Return a minimal document_profile dict with sensible defaults."""
    base = {
        "id": "dp-test",
        "label": "Test Profile",
        "document_type": "document",
        "enabled": True,
        "target_folder_id": "folder-target",
        "classification_hints": ["hinweis1", "hinweis2"],
        "negative_hints": [],
        "confidence_threshold": 0.5,
        "duplicate_policy": "keep",
        "naming_template": None,
        "type_literal": None,
        "fallback_values": {},
    }
    base.update(kwargs)
    return base


def _make_full_profile(**doc_profile_kwargs) -> dict:
    """Return a full profile_config dict containing one document_profile."""
    folders = [
        {"id": "folder-target", "folder_name": "contracts"},
        {"id": "folder-fallback", "folder_name": "unklar"},
    ]
    return {
        "schema_version": "1.0",
        "profile_name": "Test",
        "folders": folders,
        "document_profiles": [_make_doc_profile(**doc_profile_kwargs)],
        "address_profiles": [],
        "account_card_profiles": [],
        "naming_profile": {
            "separator": "_",
            "max_length": 50,
            "fields": [],
            "fallback_values": {},
        },
        "review_policy": {"unclear_folder": "unklar"},
    }


def _make_rule(
    profile_id: str = "dp-test",
    target_folder: str = "contracts",
    fallback_folder: str = "unklar",
    classification_hints: tuple[str, ...] = ("vertrag", "laufzeit"),
    negative_hints: tuple[str, ...] = (),
    confidence_threshold: float = 0.5,
    naming_template: str | None = None,
    type_literal: str | None = None,
    fallback_values: dict | None = None,
) -> DocumentProfileRule:
    return DocumentProfileRule(
        id=profile_id,
        label=profile_id,
        document_type="document",
        classification_hints=classification_hints,
        negative_hints=negative_hints,
        target_folder=target_folder,
        fallback_folder=fallback_folder,
        confidence_threshold=confidence_threshold,
        duplicate_policy="keep",
        naming_template=naming_template,
        type_literal=type_literal,
        fallback_values=fallback_values or {},
    )


def _make_extracted(raw_text: str = "") -> ExtractedData:
    return ExtractedData(
        invoice_date_raw=None,
        supplier_raw=None,
        amount_raw=None,
        raw_text=raw_text,
        source_method="test",
    )


# ---------------------------------------------------------------------------
# Compiler tests
# ---------------------------------------------------------------------------

class TestCompileDocumentProfiles:
    """Unit tests for _compile_document_profiles()."""

    def test_valid_profile_compiled_correctly(self) -> None:
        folders = _make_folders(("f1", "contracts"), ("f2", "unklar"))
        profiles = [
            _make_doc_profile(
                id="dp-contracts",
                target_folder_id="f1",
                fallback_folder_id="f2",
                classification_hints=["vertrag", "laufzeit"],
                naming_template="{date}_{type_literal}",
                confidence_threshold=0.6,
            )
        ]
        compiled, warnings = _compile_document_profiles(profiles, folders)
        assert len(compiled) == 1
        assert len(warnings) == 0
        rule = compiled[0]
        assert rule["id"] == "dp-contracts"
        assert rule["target_folder"] == "contracts"
        assert rule["fallback_folder"] == "unklar"
        assert rule["classification_hints"] == ["vertrag", "laufzeit"]
        assert rule["naming_template"] == "{date}_{type_literal}"
        assert rule["confidence_threshold"] == pytest.approx(0.6)

    def test_disabled_profile_is_silently_skipped(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [_make_doc_profile(id="dp-disabled", enabled=False, target_folder_id="f1")]
        compiled, warnings = _compile_document_profiles(profiles, folders)
        assert compiled == []
        assert warnings == []

    def test_invoice_profile_blocked_with_warning(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [
            _make_doc_profile(id="dp-inv", document_type="invoice", target_folder_id="f1")
        ]
        compiled, warnings = _compile_document_profiles(profiles, folders)
        assert compiled == []
        assert len(warnings) == 1
        assert "invoice" in warnings[0].lower()
        assert "dp-inv" in warnings[0]

    def test_duplicate_id_raises_value_error(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [
            _make_doc_profile(id="dp-dup", target_folder_id="f1"),
            _make_doc_profile(id="dp-dup", target_folder_id="f1"),
        ]
        with pytest.raises(ValueError, match="doppelte id"):
            _compile_document_profiles(profiles, folders)

    def test_missing_id_raises_value_error(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [{"document_type": "document", "target_folder_id": "f1"}]
        with pytest.raises(ValueError, match="id"):
            _compile_document_profiles(profiles, folders)

    def test_missing_target_folder_id_raises(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [{"id": "dp-x", "document_type": "document"}]
        with pytest.raises(ValueError, match="target_folder_id"):
            _compile_document_profiles(profiles, folders)

    def test_unknown_target_folder_id_raises(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [_make_doc_profile(id="dp-x", target_folder_id="nonexistent")]
        with pytest.raises(ValueError, match="target_folder_id"):
            _compile_document_profiles(profiles, folders)

    def test_invalid_fallback_folder_id_raises(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [
            _make_doc_profile(
                id="dp-x", target_folder_id="f1", fallback_folder_id="bad-id"
            )
        ]
        with pytest.raises(ValueError, match="fallback_folder_id"):
            _compile_document_profiles(profiles, folders)

    def test_missing_fallback_folder_uses_unklar_and_warns(self) -> None:
        folders = _make_folders(("f1", "contracts"))
        profiles = [_make_doc_profile(id="dp-x", target_folder_id="f1")]
        compiled, warnings = _compile_document_profiles(profiles, folders)
        assert compiled[0]["fallback_folder"] == "unklar"
        assert any("fallback" in w.lower() for w in warnings)

    def test_missing_fallback_uses_unclear_role_folder(self) -> None:
        folders = [
            {"id": "f1", "folder_name": "contracts"},
            {"id": "f2", "folder_name": "review-pile", "role": "unclear"},
        ]
        profiles = [_make_doc_profile(id="dp-x", target_folder_id="f1")]
        compiled, warnings = _compile_document_profiles(profiles, folders)
        assert compiled[0]["fallback_folder"] == "review-pile"
        assert any("review-pile" in w for w in warnings)


class TestCompileProfileToRulesDocumentProfiles:
    """Integration test: compile_profile_to_rules() top-level document_profiles output."""

    def test_document_profiles_at_top_level(self) -> None:
        profile = _make_full_profile(
            id="dp-test",
            target_folder_id="folder-target",
            fallback_folder_id="folder-fallback",
        )
        result = compile_profile_to_rules(profile)
        assert "document_profiles" in result
        assert "presets" in result
        # document_profiles must NOT appear inside presets
        preset = result["presets"]["office_default"]
        assert "document_profiles" not in preset

    def test_document_profiles_warnings_in_meta(self) -> None:
        profile = _make_full_profile(
            id="dp-test",
            target_folder_id="folder-target",
            # No fallback_folder_id → warning expected
        )
        result = compile_profile_to_rules(profile)
        assert "_meta" in result
        assert "document_profiles_warnings" in result["_meta"]
        assert isinstance(result["_meta"]["document_profiles_warnings"], list)

    def test_no_document_profiles_in_profile_emits_empty_list(self) -> None:
        profile = {
            "schema_version": "1.0",
            "profile_name": "Empty",
            "folders": [],
            "address_profiles": [],
            "account_card_profiles": [],
            "naming_profile": {
                "separator": "_",
                "max_length": 50,
                "fields": [],
                "fallback_values": {},
            },
        }
        result = compile_profile_to_rules(profile)
        assert result["document_profiles"] == []

    def test_existing_preset_routing_not_altered(self) -> None:
        profile = _make_full_profile(
            id="dp-test",
            target_folder_id="folder-target",
            fallback_folder_id="folder-fallback",
        )
        result = compile_profile_to_rules(profile)
        preset = result["presets"]["office_default"]
        # Routing must still have strassen/prioritaetsregeln keys
        assert "routing" in preset
        routing = preset["routing"]
        assert "strassen" in routing
        assert "prioritaetsregeln" in routing


class TestLoadDocumentProfilesFromRuntimeRules:
    """Tests for config.load_document_profiles_from_runtime_rules()."""

    def test_returns_empty_when_key_missing(self) -> None:
        rules_dict = {"active_preset": "x", "presets": {}}
        result = load_document_profiles_from_runtime_rules(rules_dict)
        assert result == []

    def test_returns_empty_when_not_list(self) -> None:
        result = load_document_profiles_from_runtime_rules(
            {"document_profiles": "not-a-list"}
        )
        assert result == []

    def test_parses_valid_document_profile(self) -> None:
        rules_dict = {
            "document_profiles": [
                {
                    "id": "dp-1",
                    "label": "Contracts",
                    "document_type": "document",
                    "classification_hints": ["vertrag"],
                    "negative_hints": ["rechnung"],
                    "target_folder": "contracts",
                    "fallback_folder": "unklar",
                    "confidence_threshold": 0.6,
                    "duplicate_policy": "keep",
                    "naming_template": "{date}_{supplier}",
                    "type_literal": "vertrag",
                    "fallback_values": {"supplier": "unbekannt"},
                }
            ]
        }
        profiles = load_document_profiles_from_runtime_rules(rules_dict)
        assert len(profiles) == 1
        p = profiles[0]
        assert isinstance(p, DocumentProfileRule)
        assert p.id == "dp-1"
        assert p.classification_hints == ("vertrag",)
        assert p.negative_hints == ("rechnung",)
        assert p.target_folder == "contracts"
        assert p.naming_template == "{date}_{supplier}"
        assert p.fallback_values == {"supplier": "unbekannt"}

    def test_malformed_entry_skipped(self) -> None:
        rules_dict = {"document_profiles": ["not-a-dict", {"id": "ok", "target_folder": "x"}]}
        result = load_document_profiles_from_runtime_rules(rules_dict)
        # "not-a-dict" is skipped; the dict entry is parsed
        assert len(result) == 1
        assert result[0].id == "ok"


# ---------------------------------------------------------------------------
# Renderer tests
# ---------------------------------------------------------------------------

class TestRenderDocumentFilename:
    """Unit tests for render_document_filename()."""

    def test_known_placeholders_resolved(self) -> None:
        result = render_document_filename(
            "{date}_{supplier}",
            {"date": "260101", "supplier": "acme"},
        )
        assert result.filename == "260101_acme"
        assert result.missing_placeholders == []
        assert result.fallback_placeholder_used == []
        assert result.unknown_placeholders == []

    def test_all_four_known_sources(self) -> None:
        result = render_document_filename(
            "{date}_{supplier}_{amount}_{type_literal}",
            {
                "date": "260101",
                "supplier": "firma",
                "amount": "100",
                "type_literal": "vertrag",
            },
        )
        assert result.filename == "260101_firma_100_vertrag"

    def test_unknown_placeholder_uses_fallback_value(self) -> None:
        result = render_document_filename(
            "{date}_{kategorie}",
            {"date": "260101"},
            fallback_values={"kategorie": "allgemein"},
        )
        assert result.filename == "260101_allgemein"
        assert "kategorie" in result.fallback_placeholder_used
        assert result.unknown_placeholders == []

    def test_unknown_placeholder_without_fallback_becomes_unbekannt(self) -> None:
        result = render_document_filename(
            "{date}_{phantom}",
            {"date": "260101"},
        )
        assert "unbekannt" in result.filename
        assert "phantom" in result.unknown_placeholders
        assert result.fallback_placeholder_used == []

    def test_known_missing_placeholder_reported(self) -> None:
        result = render_document_filename(
            "{date}_{supplier}",
            {"date": "260101"},
        )
        assert "unbekannt" in result.filename
        assert "supplier" in result.missing_placeholders

    def test_unsafe_filename_characters_sanitized(self) -> None:
        result = render_document_filename(
            "{date}",
            {"date": "260101/foo:bar"},
        )
        assert "/" not in result.filename
        assert ":" not in result.filename

    def test_repeated_underscores_collapsed(self) -> None:
        result = render_document_filename(
            "{date}___{supplier}",
            {"date": "260101", "supplier": "acme"},
        )
        assert "__" not in result.filename

    def test_leading_trailing_underscores_stripped(self) -> None:
        result = render_document_filename(
            "_{date}_",
            {"date": "260101"},
        )
        assert not result.filename.startswith("_")
        assert not result.filename.endswith("_")

    def test_empty_result_gets_safe_fallback(self) -> None:
        result = render_document_filename("{}", {})
        assert result.filename
        assert result.filename == "dokument-unbekannt"

    def test_no_placeholders_returns_template_sanitized(self) -> None:
        result = render_document_filename("mein-dokument", {})
        assert result.filename == "mein-dokument"
        assert result.missing_placeholders == []

    def test_known_placeholder_with_fallback_value_uses_fallback(self) -> None:
        result = render_document_filename(
            "{supplier}",
            {"supplier": ""},
            fallback_values={"supplier": "fallback-firma"},
        )
        assert result.filename == "fallback-firma"
        assert "supplier" in result.fallback_placeholder_used

    def test_pdf_extension_not_added(self) -> None:
        result = render_document_filename("{date}", {"date": "260101"})
        assert not result.filename.endswith(".pdf")


# ---------------------------------------------------------------------------
# Matcher tests (unit tests against _match_document_profile)
# ---------------------------------------------------------------------------

def _make_processor_for_matching(
    tmp_path: Path,
    document_profiles: list[DocumentProfileRule],
):
    """Build a minimal InvoiceProcessor with given profiles."""
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.processing import InvoiceProcessor

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    documents_dir = tmp_path / "documents"
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"
    input_dir.mkdir(parents=True)

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
                "api_key_pfad": "$HOME/.env",
                "archiv_aktiv": True,
                "regeln_datei": str(rules_path),
                "aktives_preset": "office_default",
                "runtime_ordner": str(runtime_dir),
                "log_ordner": str(logs_dir),
            }
        ),
        encoding="utf-8",
    )

    class _Stub:
        def extract(self, pdf_path, *, log):
            raise RuntimeError("should not extract in matcher tests")

    app_config = load_app_config(config_path)
    office_rules = load_office_rules(rules_path)

    return InvoiceProcessor(
        app_config,
        _Stub(),
        office_rules=office_rules,
        document_profiles=document_profiles,
    )


class TestMatchDocumentProfile:
    """Unit tests for InvoiceProcessor._match_document_profile()."""

    def test_positive_match_above_threshold(self, tmp_path: Path) -> None:
        rule = _make_rule(
            classification_hints=("vertrag", "laufzeit"),
            confidence_threshold=0.5,
        )
        processor = _make_processor_for_matching(tmp_path, [rule])
        extracted = _make_extracted("dieses dokument ist ein vertrag mit laufzeit")
        matched, score, meta = processor._match_document_profile(extracted)
        assert matched is not None
        assert matched.id == "dp-test"
        assert score is not None
        assert score >= 0.5

    def test_negative_hint_blocks_profile(self, tmp_path: Path) -> None:
        rule = _make_rule(
            classification_hints=("vertrag",),
            negative_hints=("rechnung",),
            confidence_threshold=0.1,
        )
        processor = _make_processor_for_matching(tmp_path, [rule])
        extracted = _make_extracted("vertrag mit rechnung anhang")
        matched, _, _ = processor._match_document_profile(extracted)
        assert matched is None

    def test_score_below_threshold_returns_no_match(self, tmp_path: Path) -> None:
        rule = _make_rule(
            classification_hints=("vertrag", "laufzeit", "konditionen"),
            confidence_threshold=0.9,
        )
        processor = _make_processor_for_matching(tmp_path, [rule])
        extracted = _make_extracted("vertrag")  # only 1/3 hints → score ≈ 0.33
        matched, score, _ = processor._match_document_profile(extracted)
        assert matched is None
        # score should be returned even on threshold miss for reporting
        assert score is not None

    def test_no_profiles_returns_no_match(self, tmp_path: Path) -> None:
        processor = _make_processor_for_matching(tmp_path, [])
        extracted = _make_extracted("vertrag laufzeit konditionen")
        matched, score, meta = processor._match_document_profile(extracted)
        assert matched is None
        assert score is None
        assert meta == {}

    def test_tie_resolved_by_list_order_first_wins(self, tmp_path: Path) -> None:
        rule_a = _make_rule(
            profile_id="dp-a",
            classification_hints=("schlagwort",),
            confidence_threshold=0.1,
        )
        rule_b = _make_rule(
            profile_id="dp-b",
            classification_hints=("schlagwort",),
            confidence_threshold=0.1,
        )
        processor = _make_processor_for_matching(tmp_path, [rule_a, rule_b])
        extracted = _make_extracted("ein schlagwort im text")
        matched, _, _ = processor._match_document_profile(extracted)
        assert matched is not None
        assert matched.id == "dp-a"


# ---------------------------------------------------------------------------
# Runtime integration tests
# ---------------------------------------------------------------------------

def _create_minimal_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Testdokument")
    doc.save(path)
    doc.close()


def _make_full_processor(
    tmp_path: Path,
    extracted_data: ExtractedData,
    document_profiles: list[DocumentProfileRule] | None = None,
):
    from invoice_tool.config import load_app_config, load_office_rules
    from invoice_tool.processing import InvoiceProcessor

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    documents_dir = tmp_path / "documents"
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"
    input_dir.mkdir(parents=True)

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
                "api_key_pfad": "$HOME/.env",
                "archiv_aktiv": True,
                "regeln_datei": str(rules_path),
                "aktives_preset": "office_default",
                "runtime_ordner": str(runtime_dir),
                "log_ordner": str(logs_dir),
            }
        ),
        encoding="utf-8",
    )

    class _StubExtractor:
        def __init__(self, data: ExtractedData) -> None:
            self._data = data

        def extract(self, pdf_path: Path, *, log):
            return self._data

    app_config = load_app_config(config_path)
    office_rules = load_office_rules(rules_path)

    return (
        InvoiceProcessor(
            app_config,
            _StubExtractor(extracted_data),
            office_rules=office_rules,
            document_profiles=document_profiles,
        ),
        input_dir,
        output_dir,
    )


class TestDocumentProfileRuntimeIntegration:
    """End-to-end integration of document_profiles in _process_one()."""

    def test_profile_match_routes_to_target_folder(self, tmp_path: Path) -> None:
        rule = _make_rule(
            classification_hints=("vertrag", "laufzeit"),
            target_folder="profile-contracts",
            fallback_folder="unklar",
            confidence_threshold=0.5,
        )
        extracted = ExtractedData(
            invoice_date_raw=None,
            supplier_raw="Testfirma",
            amount_raw=None,
            raw_text="dieser vertrag enthält eine laufzeit",
            source_method="test",
        )
        processor, input_dir, output_dir = _make_full_processor(
            tmp_path, extracted, document_profiles=[rule]
        )
        pdf = input_dir / "doc.pdf"
        _create_minimal_pdf(pdf)

        results = processor.process_all()
        assert len(results) == 1
        result = results[0]
        assert result.dokumenttyp == "document"
        assert "profile-contracts" in str(result.storage_file)

    def test_no_match_falls_back_to_process_document(self, tmp_path: Path) -> None:
        rule = _make_rule(
            classification_hints=("nicht-vorhanden",),
            target_folder="profile-contracts",
            fallback_folder="unklar",
            confidence_threshold=0.9,
        )
        extracted = ExtractedData(
            invoice_date_raw=None,
            supplier_raw=None,
            amount_raw=None,
            raw_text="irgendein dokument ohne passendes schlagwort",
            source_method="test",
        )
        processor, input_dir, output_dir = _make_full_processor(
            tmp_path, extracted, document_profiles=[rule]
        )
        pdf = input_dir / "doc.pdf"
        _create_minimal_pdf(pdf)

        results = processor.process_all()
        assert len(results) == 1
        result = results[0]
        assert result.dokumenttyp == "document"
        # Should NOT go to profile-contracts since no match
        assert "profile-contracts" not in str(result.storage_file)

    def test_missing_placeholder_routes_to_fallback_folder(self, tmp_path: Path) -> None:
        rule = _make_rule(
            classification_hints=("vertrag",),
            target_folder="profile-contracts",
            fallback_folder="unklar-fallback",
            confidence_threshold=0.1,
            naming_template="{date}_{supplier}_{amount}",
        )
        extracted = ExtractedData(
            invoice_date_raw=None,
            supplier_raw=None,   # supplier missing → placeholder missing
            amount_raw=None,     # amount missing
            raw_text="vertrag",
            source_method="test",
        )
        processor, input_dir, output_dir = _make_full_processor(
            tmp_path, extracted, document_profiles=[rule]
        )
        pdf = input_dir / "doc.pdf"
        _create_minimal_pdf(pdf)

        results = processor.process_all()
        assert len(results) == 1
        result = results[0]
        assert result.dokumenttyp == "document"
        assert "unklar-fallback" in str(result.storage_file)

    def test_no_profiles_keeps_old_process_document_path(self, tmp_path: Path) -> None:
        extracted = ExtractedData(
            invoice_date_raw=None,
            supplier_raw=None,
            amount_raw=None,
            raw_text="irgendein dokument",
            source_method="test",
        )
        processor, input_dir, output_dir = _make_full_processor(
            tmp_path, extracted, document_profiles=None
        )
        pdf = input_dir / "doc.pdf"
        _create_minimal_pdf(pdf)

        results = processor.process_all()
        assert len(results) == 1
        result = results[0]
        assert result.dokumenttyp == "document"
        # No profile folder names in path – processed via original _process_document
        assert result.storage_file.exists()


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

class TestRegressionInvoicePathUnchanged:
    """Confirm that invoice classification still follows _process_invoice()."""

    def test_invoice_not_routed_via_document_profile(self, tmp_path: Path) -> None:
        rule = _make_rule(
            classification_hints=("rechnung",),
            target_folder="should-never-be-used",
            confidence_threshold=0.1,
        )
        # raw_text that would match the profile hint AND triggers invoice classification
        extracted = ExtractedData(
            invoice_date_raw="01.01.2026",
            supplier_raw="TestLieferant GmbH",
            amount_raw="100,00 EUR",
            raw_text="rechnung nummer 2026-001",
            source_method="test",
        )
        processor, input_dir, output_dir = _make_full_processor(
            tmp_path, extracted, document_profiles=[rule]
        )
        pdf = input_dir / "invoice.pdf"
        _create_minimal_pdf(pdf)

        results = processor.process_all()
        assert len(results) == 1
        result = results[0]
        # Invoice classification must win – document profile must never apply
        assert result.dokumenttyp == "invoice"
        assert "should-never-be-used" not in str(result.storage_file)

    def test_no_document_profiles_key_in_rules_means_no_profiles(self) -> None:
        """load_document_profiles_from_runtime_rules returns [] when key absent."""
        rules = {"active_preset": "x", "presets": {"x": {}}}
        result = load_document_profiles_from_runtime_rules(rules)
        assert result == []
        assert isinstance(result, list)
