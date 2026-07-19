"""UX presenter for the local SaaS UI-v2 profile draft list.

Shows multiple local SaaS drafts without claiming cloud sync or tenant backend.
Keeps SaaS drafts separate from the internal working profile.
No private Hadi/SOMAA/AMEX-1005/EP defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from invoice_tool.ui_v2.saas_profile_persistence_view import (
    NO_CLOUD_HELP,
    SEPARATION_HELP,
    find_forbidden_cloud_claim_violations,
    find_private_persistence_ux_violations,
)
from invoice_tool.ui_v2.saas_profile_store import (
    DRAFT_ITEM_CORRUPTED,
    DRAFT_ITEM_MISSING,
    DRAFT_ITEM_OK,
    SaasDraftListItem,
)

if TYPE_CHECKING:
    import flet as ft

DRAFT_LIST_TITLE = "Lokale SaaS-Entwürfe"
DRAFT_LIST_SCOPE = "SaaS-Profilentwürfe (lokal)"
LOCALITY_LABEL = "lokal / nicht Cloud"
EMPTY_LIST_HELP = "Noch keine lokalen SaaS-Entwürfe. Neuen generischen Entwurf anlegen."
SELECTED_NONE_LABEL = "Kein Entwurf gewählt"
ACTION_NEW = "Neuer Entwurf"
ACTION_LOAD = "Entwurf laden"
ACTION_SAVE = "Entwurf speichern"

_PRIVATE_UI_MARKERS: tuple[str, ...] = (
    "SOMAA",
    "Hadi",
    "AMEX-1005",
    "EP",
    "Bismarck",
    "97368",
    "DE189",
    "voba",
)


@dataclass(frozen=True)
class SaasDraftListRowVM:
    draft_id: str
    display_name: str
    status_label: str
    locality_label: str
    selected: bool
    is_usable: bool
    error_text: str
    updated_at: str


@dataclass(frozen=True)
class SaasDraftListVM:
    title: str
    scope_label: str
    separation_help: str
    no_cloud_help: str
    locality_label: str
    selected_draft_id: str | None
    selected_label: str
    empty_help: str
    rows: tuple[SaasDraftListRowVM, ...]
    action_new: str
    action_load: str
    action_save: str

    def all_ui_texts(self) -> tuple[str, ...]:
        texts = [
            self.title,
            self.scope_label,
            self.separation_help,
            self.no_cloud_help,
            self.locality_label,
            self.selected_label,
            self.empty_help,
            self.action_new,
            self.action_load,
            self.action_save,
        ]
        for row in self.rows:
            texts.extend(
                [
                    row.display_name,
                    row.status_label,
                    row.locality_label,
                    row.error_text,
                ]
            )
        return tuple(text for text in texts if text)


def build_saas_draft_list_vm(
    items: tuple[SaasDraftListItem, ...] | list[SaasDraftListItem],
    *,
    selected_draft_id: str | None = None,
) -> SaasDraftListVM:
    rows: list[SaasDraftListRowVM] = []
    selected_label = SELECTED_NONE_LABEL
    for item in items:
        selected = bool(selected_draft_id and item.draft_id == selected_draft_id)
        if selected:
            selected_label = f"Aktiver lokaler Entwurf: {item.display_name}"
        rows.append(
            SaasDraftListRowVM(
                draft_id=item.draft_id,
                display_name=item.display_name,
                status_label=_row_status_label(item),
                locality_label=LOCALITY_LABEL,
                selected=selected,
                is_usable=item.is_usable,
                error_text=item.error or "",
                updated_at=item.updated_at,
            )
        )
    vm = SaasDraftListVM(
        title=DRAFT_LIST_TITLE,
        scope_label=DRAFT_LIST_SCOPE,
        separation_help=SEPARATION_HELP,
        no_cloud_help=NO_CLOUD_HELP,
        locality_label=LOCALITY_LABEL,
        selected_draft_id=selected_draft_id,
        selected_label=selected_label,
        empty_help=EMPTY_LIST_HELP,
        rows=tuple(rows),
        action_new=ACTION_NEW,
        action_load=ACTION_LOAD,
        action_save=ACTION_SAVE,
    )
    _assert_draft_list_ux_safe(vm)
    return vm


def build_saas_draft_list_panel(
    vm: SaasDraftListVM,
    *,
    on_select: Callable[[str], None] | None = None,
    on_new: Callable[[], None] | None = None,
    on_load: Callable[[], None] | None = None,
    on_save: Callable[[], None] | None = None,
) -> Any:
    """Flet panel: local SaaS draft list with new/load/save actions."""

    import flet as ft

    from invoice_tool.ui_v2.components import compact_list_item, inline_error, status_badge
    from invoice_tool.ui_v2.edit_components import action_button, helper_text
    from invoice_tool.ui_v2.theme import COLOR_TEXT_PRIMARY, SPACE_SM, SPACE_XS

    header = ft.Row(
        [
            ft.Text(
                vm.title,
                size=14,
                weight=ft.FontWeight.W_700,
                color=COLOR_TEXT_PRIMARY,
            ),
            status_badge(vm.locality_label, tone="neutral"),
        ],
        spacing=SPACE_SM,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
    )
    rows: list[ft.Control] = [
        header,
        helper_text(vm.scope_label),
        helper_text(vm.separation_help),
        helper_text(vm.no_cloud_help),
        helper_text(vm.selected_label),
    ]

    if not vm.rows:
        rows.append(helper_text(vm.empty_help))
    else:
        list_controls: list[ft.Control] = []
        for row in vm.rows:
            trailing = status_badge(
                row.status_label,
                tone="error" if not row.is_usable else ("active" if row.selected else "neutral"),
            )

            def _make_handler(draft_id: str) -> Callable[[ft.ControlEvent], None]:
                def _handler(_event: ft.ControlEvent) -> None:
                    if on_select is not None:
                        on_select(draft_id)

                return _handler

            list_controls.append(
                compact_list_item(
                    row.display_name,
                    trailing=trailing,
                    selected=row.selected,
                    on_select=_make_handler(row.draft_id) if on_select else None,
                )
            )
            if row.error_text:
                list_controls.append(inline_error(row.error_text))
        rows.append(ft.Column(list_controls, spacing=SPACE_XS, tight=True))

    actions: list[ft.Control] = []
    if on_new is not None:
        actions.append(action_button(vm.action_new, on_click=lambda _e: on_new()))
    if on_load is not None:
        actions.append(action_button(vm.action_load, on_click=lambda _e: on_load()))
    if on_save is not None:
        actions.append(action_button(vm.action_save, on_click=lambda _e: on_save(), primary=True))
    if actions:
        rows.append(ft.Row(actions, spacing=SPACE_SM, wrap=True))

    return ft.Column(rows, spacing=SPACE_XS, tight=True)


def _row_status_label(item: SaasDraftListItem) -> str:
    if item.status == DRAFT_ITEM_CORRUPTED:
        return "beschädigt"
    if item.status == DRAFT_ITEM_MISSING:
        return "fehlt"
    if item.status == DRAFT_ITEM_OK:
        return LOCALITY_LABEL
    return item.status


def _assert_draft_list_ux_safe(vm: SaasDraftListVM) -> None:
    texts = vm.all_ui_texts()
    private = find_private_persistence_ux_violations(texts)
    for text in texts:
        for marker in _PRIVATE_UI_MARKERS:
            if marker in text:
                private.append(f"private_marker:{marker}")
    if private:
        raise AssertionError("Draft-Listen-UX enthält private Defaults: " + ", ".join(private))
    cloud = find_forbidden_cloud_claim_violations(texts)
    if cloud:
        raise AssertionError("Draft-Listen-UX behauptet Cloud-Persistenz: " + ", ".join(cloud))
    joined = " ".join(texts)
    assert DRAFT_LIST_TITLE in joined
    assert SEPARATION_HELP in joined
    assert NO_CLOUD_HELP in joined
    assert "interne Arbeitsprofil" in joined
    assert "Cloud-Synchronisierung" in joined
