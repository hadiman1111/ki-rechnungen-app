"""UI-v2 profile surface wired to generic SaaS product model."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from invoice_tool.saas_product_model import (
    DEFAULT_SAAS_FILENAME_PATTERN,
    DEFAULT_SAAS_PROFILE_NAME,
    DEFAULT_SAAS_SCAN_MODEL_ID,
    build_blank_saas_profile,
)
from invoice_tool.ui_v2.saas_profile_surface import (
    GENERIC_CONFIG_NAME_PLACEHOLDER,
    SAAS_SURFACE_UI_LABELS,
    assert_ui_surface_defaults_are_generic,
    blank_configuration_create_defaults,
    blank_profile_draft,
    build_saas_profile_surface_vm,
    expected_surface_field_keys,
    find_private_ui_surface_violations,
    load_blank_saas_profile,
    surface_payload_as_dict,
)

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "invoice_tool" / "ui_v2" / "saas_profile_surface.py"
PROFILES_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "profiles.py"
CONFIGS_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "configurations.py"

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
    "USt-IdNr",
)


def test_profile_surface_uses_build_blank_saas_profile() -> None:
    surface_src = SURFACE.read_text(encoding="utf-8")
    assert "build_blank_saas_profile" in surface_src
    assert "from invoice_tool.saas_product_model import" in surface_src

    blank = load_blank_saas_profile()
    model_blank = build_blank_saas_profile()
    assert blank == model_blank

    draft = blank_profile_draft()
    assert draft.is_new is True
    assert draft.name == DEFAULT_SAAS_PROFILE_NAME
    assert draft.scan_model_id == DEFAULT_SAAS_SCAN_MODEL_ID


def test_ui_v2_pages_import_saas_profile_surface() -> None:
    profiles_src = PROFILES_PAGE.read_text(encoding="utf-8")
    configs_src = CONFIGS_PAGE.read_text(encoding="utf-8")
    assert "blank_profile_draft" in profiles_src
    assert "build_saas_profile_surface_vm" in profiles_src
    assert "saas_profile_surface" in profiles_src
    assert "blank_configuration_create_defaults" in configs_src
    assert "GENERIC_CONFIG_NAME_PLACEHOLDER" in configs_src
    assert "American Express" not in configs_src


def test_surface_defaults_contain_no_private_markers() -> None:
    vm = build_saas_profile_surface_vm()
    payload = surface_payload_as_dict(vm)
    blob = str(payload)
    for marker in PRIVATE_MARKERS:
        assert marker not in blob, marker
    assert_ui_surface_defaults_are_generic(vm)
    assert find_private_ui_surface_violations(vm) == []

    config_defaults = blank_configuration_create_defaults()
    config_blob = str(config_defaults)
    for marker in PRIVATE_MARKERS:
        assert marker not in config_blob, marker
    assert "American Express" not in config_defaults.name_placeholder
    assert config_defaults.name_placeholder == GENERIC_CONFIG_NAME_PLACEHOLDER
    assert config_defaults.filename_pattern == DEFAULT_SAAS_FILENAME_PATTERN
    assert config_defaults.destination_category == ""
    assert config_defaults.destination_folder == ""
    assert config_defaults.payment_hint == ""


def test_surface_exposes_expected_generic_fields() -> None:
    vm = build_saas_profile_surface_vm()
    keys = {field.key for field in vm.fields}
    assert set(expected_surface_field_keys()) <= keys
    labels = {field.label for field in vm.fields}
    for required_label in (
        SAAS_SURFACE_UI_LABELS["scan_model"],
        SAAS_SURFACE_UI_LABELS["document_type"],
        SAAS_SURFACE_UI_LABELS["matching_conditions"],
        SAAS_SURFACE_UI_LABELS["destination"],
        SAAS_SURFACE_UI_LABELS["filename_pattern"],
        SAAS_SURFACE_UI_LABELS["review_rule"],
        SAAS_SURFACE_UI_LABELS["payment_hint"],
    ):
        assert required_label in labels
    assert vm.profile_name == DEFAULT_SAAS_PROFILE_NAME
    assert vm.ui_labels["new_profile"] == "Neues Profil"


def test_internal_launcher_files_not_in_saas_surface_changeset() -> None:
    """Surface wiring must not touch internal launcher paths in this worktree change."""

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

    tree = ast.parse(SURFACE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("internal_launcher" in name for name in imported)
