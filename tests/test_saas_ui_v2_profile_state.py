"""UI-v2 in-memory SaaS profile/configuration draft state."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from invoice_tool.saas_product_model import (
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_SCAN_MODEL_ID,
)
from invoice_tool.ui_v2.saas_profile_state import (
    REQUIRED_CONFIGURATION_FIELDS,
    REQUIRED_PROFILE_FIELDS,
    SaasProfileStateStore,
    new_saas_profile_state_store,
)
from invoice_tool.ui_v2.saas_profile_surface import GENERIC_CONFIG_NAME_HINT

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_state.py"
CONFIGS_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"
PROFILES_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py"

INTERNAL_LAUNCHER_PATHS = (
    ROOT / "app_internal_launcher.py",
    ROOT / "invoice_tool" / "internal_launcher",
    ROOT / "scripts" / "macos_dock_launcher.c",
    ROOT / "scripts" / "macos_fletview_bootstrap.c",
    ROOT / "scripts" / "build_macos_dock_app.sh",
)

PRIVATE_MARKERS = (
    "SOMAA",
    "Hadi",
    "AMEX-1005",
    "EP",
    "Bismarck",
    "97368",
    "DE189",
)


def test_draft_starts_generic() -> None:
    store = new_saas_profile_state_store()
    draft = store.begin_blank_profile()
    assert draft.profile_name == DEFAULT_SAAS_PROFILE_NAME
    assert draft.scan_model_id == DEFAULT_SAAS_SCAN_MODEL_ID
    assert draft.document_type == "Rechnungen"
    assert draft.destination_category == ""
    assert draft.destination_folder == ""
    assert draft.payment_hint == ""
    assert draft.matching_conditions_text == ""
    assert draft.filename_pattern == DEFAULT_SAAS_FILENAME_PATTERN
    assert store.private_default_violations() == []


def test_fields_can_be_updated_generically() -> None:
    store = SaasProfileStateStore()
    store.begin_blank_profile()
    store.update_profile_field("profile_name", "Mandant Alpha")
    store.update_profile_field("scan_model_id", "angebote")
    store.update_profile_field("document_type", "Angebote")
    store.update_profile_field("matching_conditions", "lieferant ist Muster GmbH")
    store.update_profile_field("destination_category", "einkauf")
    store.update_profile_field("destination_folder", "/tmp/belege-ziel")
    store.update_profile_field("filename_pattern", "{invoice_date}_{supplier}.pdf")
    store.update_profile_field("review_rule", "unclear_on_no_match")
    store.update_profile_field("payment_hint", "Konto 4400")

    draft = store.profile_draft
    assert draft is not None
    assert draft.profile_name == "Mandant Alpha"
    assert draft.scan_model_id == "angebote"
    assert draft.document_type == "Angebote"
    assert "Muster GmbH" in draft.matching_conditions_text
    assert draft.destination_category == "einkauf"
    assert draft.destination_folder == "/tmp/belege-ziel"
    assert draft.filename_pattern == "{invoice_date}_{supplier}.pdf"
    assert draft.payment_hint == "Konto 4400"


def test_validation_detects_missing_required_fields() -> None:
    store = SaasProfileStateStore()
    store.begin_blank_profile()
    store.update_profile_field("profile_name", "")
    store.update_profile_field("document_type", "")
    result = store.validate_profile_draft()
    assert result.ok is False
    assert "profile_name" in result.field_errors
    assert "document_type" in result.field_errors
    assert set(REQUIRED_PROFILE_FIELDS) & set(result.field_errors)

    store.begin_blank_configuration()
    config_result = store.validate_configuration_draft()
    assert config_result.ok is False
    assert "name" in config_result.field_errors
    assert "destination_folder" in config_result.field_errors
    assert set(REQUIRED_CONFIGURATION_FIELDS) & set(config_result.field_errors)


def test_no_private_defaults_in_state_module_or_drafts() -> None:
    store = SaasProfileStateStore()
    store.begin_blank_profile()
    store.begin_blank_configuration()
    blob = str(store.profile_draft.to_dict()) + str(store.configuration_draft.to_dict())
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    assert store.private_default_violations() == []

    state_src = STATE.read_text(encoding="utf-8")
    # Documentation may mention forbidden markers; value-bearing defaults must not.
    assert 'profile_name="SOMAA"' not in state_src
    assert 'destination_category="ep"' not in state_src
    assert "AMEX-1005" not in state_src
    assert "97368" not in state_src


def test_configuration_editor_uses_generic_fields() -> None:
    store = SaasProfileStateStore()
    store.begin_blank_configuration()
    fields = store.generic_editor_fields()
    keys = {item["key"] for item in fields}
    for required in (
        "document_type",
        "matching_conditions",
        "destination_category",
        "destination_folder",
        "filename_pattern",
        "review_rule",
        "payment_hint",
    ):
        assert required in keys
    assert store.config_name_hint() == GENERIC_CONFIG_NAME_HINT

    configs_src = CONFIGS_PAGE.read_text(encoding="utf-8")
    assert "GENERIC_CONFIG_NAME_HINT" in configs_src
    assert "saas_draft_store" in configs_src
    assert "begin_blank_configuration" in configs_src
    assert "generic_editor_fields" in configs_src
    assert "reorder_configurations" in configs_src
    assert '"Aktivieren"' in configs_src or "'Aktivieren'" in configs_src
    assert '"Deaktivieren"' in configs_src or "'Deaktivieren'" in configs_src
    assert "Speichern" in configs_src
    assert "American Express" not in configs_src

    profiles_src = PROFILES_PAGE.read_text(encoding="utf-8")
    assert "saas_draft_store" in profiles_src
    assert "begin_blank_profile" in profiles_src


def test_internal_launcher_files_not_in_changeset() -> None:
    for path in INTERNAL_LAUNCHER_PATHS:
        assert path.exists(), path

    result = subprocess.run(
        ["git", "status", "--short", "--"]
        + [str(path.relative_to(ROOT)) for path in INTERNAL_LAUNCHER_PATHS],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "", result.stdout

    tree = ast.parse(STATE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("internal_launcher" in name for name in imported)


def test_ui_v2_ux_gate_status_reported() -> None:
    """UX gate must pass after Altfehler repair; otherwise fail this focused suite."""

    gate = ROOT / "scripts" / "run_ui_v2_ux_interaction_gate.py"
    flet085 = ROOT / ".venv-flet085" / "bin" / "python"
    python = str(flet085) if flet085.is_file() else "python3"
    result = subprocess.run(
        [python, str(gate)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
