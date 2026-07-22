"""Track-B UI-v2 review navigation and honest empty review queue — non-GUI."""

from __future__ import annotations

import ast
from pathlib import Path

from invoice_tool.ui_v2.navigation import ALL_NAV_ITEMS, NAV_REVIEW
from invoice_tool.ui_v2.pages.review import (
    EMPTY_REVIEW_DETAIL,
    EMPTY_REVIEW_TITLE,
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
    assert "Noch keine Prüffälle vorhanden." in (vm.empty_title or "")
    assert "echten Verarbeitungslauf" in (vm.empty_detail or "")


def test_review_page_does_not_render_fake_review_items() -> None:
    vm = build_review_page_vm(UiV2State())
    assert vm.items == ()
    assert len(vm.items) == 0
    for marker in ("AMEX", "Privat", "SOMAA", "Hadi", "unklar-1", "preview"):
        blob = " ".join(
            filter(
                None,
                (
                    vm.empty_title,
                    vm.empty_detail,
                    *(item.document_name for item in vm.items),
                    *(item.reason for item in vm.items),
                ),
            )
        )
        assert marker not in blob, marker


def test_review_page_accepts_processing_run_state_items() -> None:
    state = UiV2State(
        processing_run_state=ProcessingRunState(
            status="completed",
            review_items=(
                ProcessingReviewItem(
                    document_name="beispiel.pdf",
                    reason="Zuordnung unklar",
                    status_label="unklar",
                ),
            ),
        )
    )
    vm = build_review_page_vm(state)
    assert vm.empty is False
    assert len(vm.items) == 1
    assert vm.items[0].document_name == "beispiel.pdf"


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
