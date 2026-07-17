"""SaaS product model: generic profile surface without private tenant defaults."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from invoice_tool.saas_product_model import (
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_SCAN_MODEL_ID,
    FORBIDDEN_PRIVATE_CATEGORY_DEFAULTS,
    FORBIDDEN_PRIVATE_DEFAULT_MARKERS,
    SaasConfigurationSurface,
    SaasMatchingCondition,
    SaasProfileSurface,
    assert_saas_defaults_are_generic,
    blank_saas_profile_as_dict,
    build_blank_saas_profile,
    editor_field_keys,
    find_private_saas_default_violations,
    list_generic_scan_models,
    product_stream_boundary,
    saas_profile_editor_fields,
)

ROOT = Path(__file__).resolve().parents[1]
INTERNAL_LAUNCHER = ROOT / "invoice_tool" / "internal_launcher"
SAAS_MODEL = ROOT / "invoice_tool" / "saas_product_model.py"


def test_blank_saas_profile_has_generic_defaults() -> None:
    surface = build_blank_saas_profile()
    assert surface.profile_name == DEFAULT_SAAS_PROFILE_NAME
    assert surface.scan_model_id == DEFAULT_SAAS_SCAN_MODEL_ID
    assert surface.configurations == ()
    assert surface.review_unclear_folder == "unklar"
    assert surface.default_filename_pattern == DEFAULT_SAAS_FILENAME_PATTERN
    assert_saas_defaults_are_generic(surface)


def test_blank_saas_profile_rejects_unknown_scan_model() -> None:
    with pytest.raises(ValueError, match="Unbekanntes Scanmodell"):
        build_blank_saas_profile(scan_model_id="somaa-only")


@pytest.mark.parametrize(
    "marker",
    [
        "SOMAA",
        "Hadi",
        "AMEX-1005",
        "amex-1005",
    ],
)
def test_blank_saas_defaults_contain_no_private_markers(marker: str) -> None:
    payload = blank_saas_profile_as_dict()
    serialized = str(payload)
    assert marker not in serialized
    assert marker.lower() not in serialized.lower()


def test_blank_saas_defaults_contain_no_private_category_ids() -> None:
    payload = blank_saas_profile_as_dict()
    assert payload["review_unclear_folder"] not in FORBIDDEN_PRIVATE_CATEGORY_DEFAULTS
    for category in FORBIDDEN_PRIVATE_CATEGORY_DEFAULTS:
        assert category not in (
            payload["profile_name"],
            payload["scan_model_id"],
            payload["document_type"],
            payload["default_filename_pattern"],
        )


def test_private_profile_payload_is_detected_as_non_saas_default() -> None:
    private_like = SaasProfileSurface(
        profile_name="SOMAA Profil",
        scan_model_id="rechnungen",
        document_type="Rechnungen",
        configurations=(
            SaasConfigurationSurface(
                name="AMEX-1005",
                destination_category="ep",
                destination_folder="amex",
                payment_hint="Hadi",
                matching_conditions=(
                    SaasMatchingCondition(feature_key="payment_field", values=("amex-1005",)),
                ),
            ),
        ),
    )
    violations = find_private_saas_default_violations(private_like)
    assert violations
    assert any("SOMAA" in item or "marker:SOMAA" in item for item in violations)


def test_editor_fields_cover_required_saas_surface() -> None:
    keys = set(editor_field_keys())
    required = {
        "profile_name",
        "scan_model_id",
        "document_type",
        "matching_conditions",
        "destination_category",
        "destination_folder",
        "filename_pattern",
        "review_rule",
        "payment_hint",
    }
    assert required <= keys
    fields = saas_profile_editor_fields()
    assert all(field.label for field in fields)


def test_generic_scan_models_are_neutral() -> None:
    models = list_generic_scan_models()
    assert {item["id"] for item in models} == {
        "rechnungen",
        "angebote",
        "freitext-dokumente",
    }
    blob = str(models)
    for marker in FORBIDDEN_PRIVATE_DEFAULT_MARKERS:
        assert marker not in blob


def test_product_stream_boundary_keeps_launcher_and_saas_separate() -> None:
    boundary = product_stream_boundary()
    assert boundary.internal_launcher_entry == "app_internal_launcher.py"
    assert boundary.saas_ui_entry == "app_ui_v2.py"
    assert boundary.internal_package == "invoice_tool.internal_launcher"
    assert boundary.saas_ui_package == "invoice_tool.ui_v2"
    assert boundary.processing_core_entry == "invoice_tool.run"
    assert "local" in boundary.private_profile_role


def test_saas_product_model_does_not_import_internal_launcher() -> None:
    tree = ast.parse(SAAS_MODEL.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("internal_launcher" in name for name in imported)
    assert INTERNAL_LAUNCHER.is_dir()


def test_assert_saas_defaults_raises_on_private_leak() -> None:
    with pytest.raises(AssertionError, match="private Tenant"):
        assert_saas_defaults_are_generic(
            {
                "profile_name": "Hadi Standardprofil",
                "scan_model_id": "rechnungen",
                "document_type": "Rechnungen",
                "configurations": [],
                "review_unclear_folder": "unklar",
                "default_filename_pattern": DEFAULT_SAAS_FILENAME_PATTERN,
                "notes": "",
            }
        )
