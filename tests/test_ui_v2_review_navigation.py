"""Track-B UI-v2 review navigation and honest review detail shell — non-GUI."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.navigation import ALL_NAV_ITEMS, NAV_REVIEW
from invoice_tool.ui_v2.pages.review import (
    EMPTY_REVIEW_DETAIL,
    EMPTY_REVIEW_TITLE,
    MSG_REVIEW_FROM_REAL_RUN,
    MSG_REVIEW_NO_FILE_MUTATION,
    build_review_page_vm,
)
from invoice_tool.ui_v2.processing_state import ProcessingReviewItem, ProcessingRunState
from invoice_tool.ui_v2.state import UiV2State

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PAGE = ROOT / "invoice_tool" / "ui_v2" / "pages" / "review.py"
PROCESSING_CORE = (
    "invoice_tool.processing",
    "invoice_tool.routing",
    "invoice_tool.routing_guards",
    "invoice_tool.classification",
    "invoice_tool.target_routing",
    "invoice_tool.run",
)
PRIVATE_MARKERS = (
    "Hadi",
    "SOMAA",
    "Bismarck",
    "AMEX",
    "voba",
    "/Users/",
    "Desktop/",
    "Privat",
    "Volksbank",
)


def test_review_navigation_item_exists() -> None:
    labels = {label for _, label, _ in ALL_NAV_ITEMS}
    ids = {nav_id for nav_id, _, _ in ALL_NAV_ITEMS}
    assert "Zur Prüfung" in labels
    assert NAV_REVIEW in ids
    assert NAV_REVIEW == "zur_pruefung"


def test_review_page_honest_empty_state() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.empty is True
    assert vm.empty_title == EMPTY_REVIEW_TITLE
    assert vm.empty_detail == EMPTY_REVIEW_DETAIL
    assert vm.items == ()
    assert vm.detail_items == ()
    assert "Noch keine Prüffälle vorhanden." in (vm.empty_title or "")
    assert "echten Verarbeitungslauf" in (vm.empty_detail or "")
    assert MSG_REVIEW_FROM_REAL_RUN in vm.honest_copy
    assert MSG_REVIEW_NO_FILE_MUTATION in vm.honest_copy


def test_review_page_does_not_render_fake_review_items() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.items == ()
    assert len(vm.items) == 0
    assert vm.detail_items == ()
    for marker in ("AMEX", "Privat", "SOMAA", "Hadi", "unklar-1", "preview"):
        blob = " ".join(
            filter(
                None,
                (
                    vm.empty_title,
                    vm.empty_detail,
                    *(item.document_name for item in vm.items),
                    *(item.reason for item in vm.items),
                    *(detail.document_label for detail in vm.detail_items),
                ),
            )
        )
        assert marker not in blob, marker


def test_review_page_displays_only_injected_review_items() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="completed",
            review_items=(
                ProcessingReviewItem(
                    document_name="beispiel.pdf",
                    reason="Zuordnung unklar",
                    status_label="unklar",
                    document_id="doc-1",
                    evidence_summary="Kein eindeutiger Zahlernachweis",
                    next_action_hint="Profilregel prüfen",
                ),
            ),
            errors=("Separater Fehler",),
        )
    )
    vm = build_review_page_vm(state)
    assert vm.empty is False
    assert len(vm.items) == 1
    assert len(vm.detail_items) == 1
    assert vm.items[0].document_name == "beispiel.pdf"
    detail = vm.detail_items[0]
    assert detail.document_label == "beispiel.pdf"
    assert detail.document_id == "doc-1"
    assert detail.reason == "Zuordnung unklar"
    assert detail.suggested_status == "unklar"
    assert detail.evidence_summary == "Kein eindeutiger Zahlernachweis"
    assert detail.next_action_hint == "Profilregel prüfen"
    assert vm.error_count == 1
    assert all("Separater Fehler" not in item.reason for item in vm.items)


def test_review_page_does_not_mutate_files() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.mutates_files is False
    assert MSG_REVIEW_NO_FILE_MUTATION in vm.honest_copy
    src = REVIEW_PAGE.read_text(encoding="utf-8")
    for token in ("unlink(", "rename(", "shutil.", "Path.write", "open(", "mkdir("):
        assert token not in src, token


def test_review_page_contains_no_fake_invoice_private_rows() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.items == ()
    src = REVIEW_PAGE.read_text(encoding="utf-8")
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker


def test_review_page_has_no_processing_core_import() -> None:
    src = REVIEW_PAGE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    for forbidden in PROCESSING_CORE:
        assert forbidden not in imported_modules
        assert forbidden not in src
    for marker in PRIVATE_MARKERS:
        assert marker not in src, marker
