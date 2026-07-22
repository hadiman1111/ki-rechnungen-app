"""Reusable UI-v2 components with truthful interaction semantics."""

from __future__ import annotations

from typing import Callable

import flet as ft

from invoice_tool.ui_v2.adapters.path_display import redact_private_path
from invoice_tool.ui_v2.theme import (
    COLOR_ACCENT_FAINT,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_CANVAS,
    COLOR_ERROR,
    COLOR_ERROR_SOFT,
    COLOR_MUTED_LIGHT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SUBTLE,
    COLOR_SUCCESS,
    COLOR_SUCCESS_SOFT,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    COLOR_WARNING_SOFT,
    COLOR_WARN_BORDER,
    CONTENT_MAX_WIDTH,
    DETAIL_PANEL_MIN_WIDTH,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_CARD_TITLE,
    FONT_SIZE_DETAIL_HEADER,
    FONT_SIZE_HELPER,
    FONT_SIZE_KPI_VALUE,
    FONT_SIZE_KPI_VALUE_LONG,
    FONT_SIZE_METADATA,
    FONT_SIZE_MONO,
    FONT_SIZE_NAV_GROUP,
    FONT_SIZE_PAGE_DESC,
    FONT_SIZE_PAGE_TITLE,
    FONT_SIZE_SECTION_TITLE,
    FORM_MAX_WIDTH,
    LIST_DETAIL_EDIT_HEIGHT,
    LIST_DETAIL_GAP,
    LIST_DETAIL_MAX_HEIGHT,
    LIST_DETAIL_MIN_HEIGHT,
    LIST_PANEL_MIN_WIDTH,
    METADATA_LABEL_WIDTH,
    PANEL_PADDING,
    PAGE_PADDING,
    RADIUS_BUTTON,
    RADIUS_CARD,
    RADIUS_INPUT,
    RADIUS_PANEL,
    COMPACT_CARD_MIN_WIDTH,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    SPACE_XXL,
    SPACE_3XL,
    WORKFLOW_PANEL_MIN_HEIGHT,
)


# ---------------------------------------------------------------------------
# Page structure
# ---------------------------------------------------------------------------


def page_header(title: str, *, subtitle: str | None = None, trailing: ft.Control | None = None) -> ft.Control:
    """Make PageHeader — 38px title, 28px bottom margin."""
    title_block: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_PAGE_TITLE,
            weight=ft.FontWeight.W_800,
            color=COLOR_TEXT_PRIMARY,
        ),
    ]
    if subtitle:
        title_block.append(
            ft.Text(
                subtitle,
                size=FONT_SIZE_PAGE_DESC,
                color=COLOR_TEXT_MUTED,
                max_lines=3,
            )
        )
    header_row = ft.Row(
        [
            ft.Column(title_block, spacing=8, expand=True),
            ft.Container(content=trailing, padding=ft.Padding.only(top=6)) if trailing is not None else ft.Container(),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    return ft.Container(margin=ft.Margin.only(bottom=12), content=header_row)


def page_heading(title: str, *, subtitle: str | None = None) -> ft.Column:
    """Backward-compatible alias for page_header."""
    return page_header(title, subtitle=subtitle)  # type: ignore[return-value]


def page_description(text: str) -> ft.Text:
    return ft.Text(text, size=FONT_SIZE_PAGE_DESC, color=COLOR_TEXT_SECONDARY)


def section_header(text: str, *, subtitle: str | None = None) -> ft.Column:
    items: list[ft.Control] = [
        ft.Text(text, size=FONT_SIZE_SECTION_TITLE, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
    ]
    if subtitle:
        items.append(ft.Text(subtitle, size=FONT_SIZE_CAPTION, color=COLOR_TEXT_MUTED))
    return ft.Column(items, spacing=SPACE_XS)


def page_scaffold(
    *controls: ft.Control,
    scroll: bool = True,
    expand_last: bool = False,
    dense: bool = True,
) -> ft.Container:
    """Canvas-backed page area — white surfaces come from individual panels."""
    items: list[ft.Control] = []
    for index, control in enumerate(controls):
        if expand_last and index == len(controls) - 1:
            items.append(ft.Container(key="ui-v2-page-fill", expand=True, content=control))
        else:
            items.append(control)
    pad = SPACE_LG if dense else PAGE_PADDING
    gap = SPACE_MD if dense else SPACE_XXL
    return ft.Container(
        expand=True,
        bgcolor=COLOR_CANVAS,
        padding=ft.Padding.only(left=pad, top=pad, bottom=pad, right=max(pad - 4, SPACE_SM)),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Column(
            items,
            spacing=gap,
            expand=expand_last,
            scroll=ft.ScrollMode.AUTO if expand_last else (ft.ScrollMode.ALWAYS if scroll else ft.ScrollMode.HIDDEN),
        ),
    )


def display_path_value(raw: str, *, max_chars: int = 56) -> str:
    """Readable path for UI — home shortened, ellipsized when long."""
    text = redact_private_path(str(raw or "").strip())
    if not text or text in {"—", "Noch nicht konfiguriert"}:
        return "Noch nicht konfiguriert"
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def path_value_text(value: str) -> ft.Text:
    """Monospace path rendering — international data-dense pattern."""
    return ft.Text(
        value,
        size=FONT_SIZE_MONO,
        color=COLOR_TEXT_PRIMARY,
        font_family="Menlo",
        selectable=True,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )


def workflow_grid(*columns: ft.Control) -> ft.Row:
    """Equal-width workflow columns — content-driven height."""
    return ft.Row(
        [ft.Container(expand=1, content=column) for column in columns],
        spacing=SPACE_MD,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def workflow_phase_card(title: str, body: ft.Control) -> ft.Container:
    """Numbered pipeline card — accent rail, content-driven height."""
    return ft.Container(
        expand=1,
        bgcolor=COLOR_SURFACE_ALT,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=SPACE_LG,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=3,
                            height=18,
                            bgcolor=COLOR_PRIMARY,
                            border_radius=2,
                        ),
                        ft.Text(
                            title,
                            size=FONT_SIZE_CARD_TITLE,
                            weight=ft.FontWeight.W_600,
                            color=COLOR_TEXT_PRIMARY,
                            expand=True,
                        ),
                    ],
                    spacing=SPACE_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                body,
            ],
            spacing=SPACE_SM,
        ),
    )


def resolve_list_detail_height(page: ft.Page | None, *, editing: bool) -> int:
    """List/detail panel height — bounded by the real browser/window height.

    The Make reference constants (`LIST_DETAIL_EDIT_HEIGHT` / `_MIN_HEIGHT`)
    stay as a floor for the initial paint (before the page has reported a
    real size) and for small windows, but on a larger window the panel grows
    with it instead of staying stuck at a fixed pixel count — most visible on
    the Konfigurationen edit panel, whose third field (Dateinamenmuster) needs
    the most room.

    Note: this intentionally computes a concrete height rather than switching
    the surrounding Row/Column to `expand=True`. UI-v2 previously shipped an
    `expand=True` list/detail layout that collapsed page content in Flet 0.85
    (see docs/audits/KI_RECHNUNGEN_UI_V2_RENDERING_LAYOUT_RECOVERY_2026-07-11.md)
    — do not reintroduce that pattern here.
    """
    baseline = LIST_DETAIL_EDIT_HEIGHT if editing else LIST_DETAIL_MIN_HEIGHT
    page_height = getattr(page, "height", None)
    if not page_height:
        return baseline
    chrome_reserved = 300  # page padding + header + KPI strip + safety margin
    available = int(page_height) - chrome_reserved
    return max(baseline, min(available, LIST_DETAIL_MAX_HEIGHT))


def list_detail_split(list_panel_ctrl: ft.Control, detail_panel_ctrl: ft.Control, *, expand: bool = False) -> ft.Row:
    """Make list/detail row — optional expand to fill remaining viewport height."""
    return ft.Row(
        [
            list_panel_ctrl,
            ft.Container(expand=True, content=detail_panel_ctrl),
        ],
        key="ui-v2-list-detail-row",
        spacing=LIST_DETAIL_GAP,
        expand=expand,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH if expand else ft.CrossAxisAlignment.START,
    )


def kpi_strip(*items: tuple[str, str, bool]) -> ft.Container:
    """Make KPIStrip — unified panel, 26px values, 24px bottom margin."""
    cells: list[ft.Control] = []
    for index, (label, value, warn) in enumerate(items):
        if index > 0:
            cells.append(ft.Container(width=1, bgcolor=COLOR_BORDER))
        is_long = len(value) > 8
        cells.append(
            ft.Container(
                expand=True,
                padding=ft.Padding.symmetric(horizontal=20, vertical=14),
                border=ft.Border(top=ft.BorderSide(2, COLOR_ERROR if warn else ft.Colors.TRANSPARENT)),
                content=ft.Column(
                    [
                        ft.Text(
                            label.upper(),
                            size=10,
                            weight=ft.FontWeight.W_600,
                            color=COLOR_TEXT_MUTED,
                        ),
                        ft.Text(
                            value,
                            size=FONT_SIZE_KPI_VALUE_LONG if is_long else FONT_SIZE_KPI_VALUE,
                            weight=ft.FontWeight.W_800,
                            color=COLOR_ERROR if warn else COLOR_TEXT_PRIMARY,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=5,
                ),
            )
        )
    return ft.Container(
        margin=ft.Margin.only(bottom=24),
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Row(cells, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
    )


def summary_metrics_row(*metrics: ft.Control, columns: int = 4) -> ft.Control:
    """Backward-compatible wrapper — prefer kpi_strip for new pages."""
    _ = columns
    if not metrics:
        return ft.Container()
    extracted: list[tuple[str, str, bool]] = []
    for metric in metrics:
        if not isinstance(metric, ft.Container):
            continue
        column = metric.content
        if not isinstance(column, ft.Column) or len(column.controls) < 2:
            continue
        label_ctrl, value_ctrl = column.controls[0], column.controls[1]
        if isinstance(label_ctrl, ft.Text) and isinstance(value_ctrl, ft.Text):
            extracted.append((label_ctrl.value or "", value_ctrl.value or "", False))
    if extracted:
        return kpi_strip(*extracted)
    return ft.Column([ft.Row(list(metrics), spacing=SPACE_SM)], spacing=SPACE_SM)


def section_block(title: str, body: ft.Control, *, subtitle: str | None = None) -> ft.Column:
    """Section without extra border — for nested content under primary cards."""
    return ft.Column(
        [
            section_header(title, subtitle=subtitle),
            body,
        ],
        spacing=SPACE_SM,
    )


def panel_section(title: str, body: ft.Control, *, subtitle: str | None = None) -> ft.Column:
    """Section with subtle elevated surface — use sparingly (settings, empty states)."""
    return ft.Column(
        [
            section_header(title, subtitle=subtitle),
            ft.Container(
                bgcolor=COLOR_SURFACE_ALT,
                border=ft.Border.all(1, COLOR_BORDER),
                border_radius=RADIUS_CARD,
                padding=SPACE_LG,
                content=body,
            ),
        ],
        spacing=SPACE_SM,
    )


def stacked_list(*entries: ft.Control) -> ft.Column:
    """Vertical list with dividers between entries."""
    items: list[ft.Control] = []
    for index, entry in enumerate(entries):
        if index > 0:
            items.append(divider())
        items.append(entry)
    return ft.Column(items, spacing=SPACE_SM)


def destination_entry(name: str, path: str, *, warning: str | None = None) -> ft.Column:
    """Single Zielordner row — title plus inline path."""
    rows: list[ft.Control] = [
        ft.Text(name, size=FONT_SIZE_CARD_TITLE, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
        metadata_row_inline("Zielordner", path),
    ]
    if warning:
        rows.append(inline_warning(warning))
    return ft.Column(rows, spacing=SPACE_XS)


def compact_entry_row(
    title: str,
    *fields: tuple[str, str],
    trailing: ft.Control | None = None,
) -> ft.Container:
    """Dense list row — subtle surface, no nested card chrome."""
    header: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_CARD_TITLE,
            weight=ft.FontWeight.W_600,
            color=COLOR_TEXT_PRIMARY,
            expand=True,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
    ]
    if trailing is not None:
        header.append(trailing)
    body: list[ft.Control] = [ft.Row(header, spacing=SPACE_SM)]
    for label, value in fields:
        is_path = label in {"Zielordner", "Ziel"}
        body.append(metric_line(label, value, monospace=is_path))
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=SPACE_SM),
        content=ft.Column(body, spacing=SPACE_XS),
    )


def info_panel(title: str, body: ft.Control, *, width: int | None = FORM_MAX_WIDTH) -> ft.Container:
    """Settings/info card — constrained width, single elevation."""
    return ft.Container(
        width=width,
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_PANEL,
        padding=PANEL_PADDING,
        content=ft.Column(
            [
                section_header(title),
                divider(),
                body,
            ],
            spacing=SPACE_LG,
        ),
    )


def detail_metadata_block(
    *pairs: tuple[str, str],
    monospace_labels: set[str] | None = None,
    field_hints: dict[str, str] | None = None,
) -> ft.Column:
    """Grouped metadata — horizontal rows, optional inline field hints."""
    mono = monospace_labels or {"Zielordner", "Ziel"}
    hints = field_hints or {}
    items: list[ft.Control] = []
    for index, (label, value) in enumerate(pairs):
        if index > 0:
            items.append(divider())
        row_block: list[ft.Control] = [metadata_row(label, value, monospace=label in mono)]
        if label in hints:
            row_block.append(
                ft.Container(
                    padding=ft.Padding.only(left=METADATA_LABEL_WIDTH + SPACE_SM),
                    content=ft.Text(hints[label], size=FONT_SIZE_HELPER, color=COLOR_WARNING),
                )
            )
        items.append(ft.Column(row_block, spacing=2))
    return ft.Column(items, spacing=SPACE_SM)


def profile_context_line(*pairs: tuple[str, str]) -> ft.Container:
    """Profil + Erkennungsmodell — compact context strip under page title."""
    return ft.Container(
        bgcolor=COLOR_SURFACE_ALT,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_MD),
        content=ft.Row(
            [
                ft.Container(expand=1, content=metadata_row_inline(label, value))
                for label, value in pairs
            ],
            spacing=SPACE_XL,
        ),
    )


def make_context_strip(*pairs: tuple[str, str]) -> ft.Container:
    """Make ContextStrip — single-line printed header, no box."""
    segments: list[ft.Control] = []
    for index, (label, value) in enumerate(pairs):
        if index > 0:
            segments.append(ft.Text(" · ", size=FONT_SIZE_METADATA, color=COLOR_BORDER_STRONG))
        segments.append(ft.Text(f"{label}: ", size=FONT_SIZE_METADATA, color=COLOR_TEXT_MUTED))
        segments.append(
            ft.Text(
                value,
                size=FONT_SIZE_METADATA,
                color=COLOR_TEXT_SECONDARY,
                weight=ft.FontWeight.W_600,
                no_wrap=True,
            )
        )
    return ft.Container(
        padding=ft.Padding.only(bottom=8),
        margin=ft.Margin.only(bottom=8),
        border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
        content=ft.Row(segments, spacing=0, wrap=False),
    )


def make_section_label(text: str) -> ft.Container:
    """Make SectionLabel — uppercase caption above a panel."""
    return ft.Container(
        margin=ft.Margin.only(bottom=8),
        content=ft.Text(
            text.upper(),
            size=FONT_SIZE_NAV_GROUP,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_MUTED,
        ),
    )


def make_info_banner(message: str) -> ft.Container:
    """Make settings info row — subtle bordered banner with icon."""
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        bgcolor=COLOR_SURFACE_ALT,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO_OUTLINE, size=13, color=COLOR_PRIMARY),
                ft.Text(message, size=FONT_SIZE_METADATA, color=COLOR_TEXT_MUTED, expand=True),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def compact_status_banner(
    title: str,
    items: tuple[str, ...] | list[str],
    *,
    detail: str | None = None,
) -> ft.Container:
    """One dense status banner with chip-like items — avoids tall status tables."""

    chips: list[ft.Control] = [
        ft.Container(
            bgcolor=COLOR_PRIMARY_SUBTLE,
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            content=ft.Text(
                item,
                size=FONT_SIZE_HELPER,
                color=COLOR_PRIMARY,
                weight=ft.FontWeight.W_600,
            ),
        )
        for item in items
        if str(item or "").strip()
    ]
    body: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_METADATA,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_PRIMARY,
        ),
    ]
    if chips:
        body.append(ft.Row(chips, spacing=6, wrap=True, tight=True))
    if detail:
        body.append(
            ft.Text(detail, size=FONT_SIZE_HELPER, color=COLOR_TEXT_MUTED, max_lines=3)
        )
    return ft.Container(
        margin=ft.Margin.only(bottom=8),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        bgcolor=COLOR_SURFACE_ALT,
        content=ft.Column(body, spacing=6, tight=True),
    )


def compact_info_row(label: str, value: str) -> ft.Container:
    """Dense label/value row with reduced padding — no large table chrome."""

    return ft.Container(
        padding=ft.Padding.symmetric(vertical=4),
        content=ft.Row(
            [
                ft.Container(
                    width=140,
                    content=ft.Text(
                        label,
                        size=FONT_SIZE_HELPER,
                        color=COLOR_TEXT_MUTED,
                        weight=ft.FontWeight.W_600,
                    ),
                ),
                ft.Text(
                    value,
                    size=FONT_SIZE_HELPER,
                    color=COLOR_TEXT_SECONDARY,
                    expand=True,
                    selectable=True,
                    max_lines=3,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def compact_hint_block(*hints: str, title: str = "Hinweise") -> ft.Container:
    """Single compact hint card instead of many repeated Hinweis table rows."""

    cleaned = [str(hint).strip() for hint in hints if str(hint or "").strip()]
    lines: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_HELPER,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_MUTED,
        ),
    ]
    for hint in cleaned:
        lines.append(
            ft.Text(f"· {hint}", size=FONT_SIZE_HELPER, color=COLOR_TEXT_SECONDARY)
        )
    return ft.Container(
        margin=ft.Margin.only(bottom=6),
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        bgcolor=COLOR_SURFACE,
        content=ft.Column(lines, spacing=2, tight=True),
    )


def collapsible_details(
    *lines: str,
    title: str = "Details anzeigen",
    initially_expanded: bool = False,
) -> ft.Control:
    """Hide secondary help / technical lines behind a compact disclosure."""

    cleaned = [str(line).strip() for line in lines if str(line or "").strip()]
    if not cleaned:
        return ft.Container(height=0)
    body = ft.Column(
        [
            ft.Text(f"· {line}", size=FONT_SIZE_HELPER, color=COLOR_TEXT_SECONDARY)
            for line in cleaned
        ],
        spacing=2,
        tight=True,
    )
    # Flet 0.85 uses `expanded`; newer Flet uses `initially_expanded`.
    tile_kwargs: dict = {
        "title": ft.Text(
            title, size=FONT_SIZE_HELPER, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.W_600
        ),
        "controls": [ft.Container(padding=ft.Padding.only(left=4, bottom=4), content=body)],
        "dense": True,
        "controls_padding": ft.Padding.symmetric(horizontal=8, vertical=2),
        "tile_padding": ft.Padding.symmetric(horizontal=8, vertical=0),
    }
    try:
        return ft.ExpansionTile(**tile_kwargs, initially_expanded=initially_expanded)
    except TypeError:
        return ft.ExpansionTile(**tile_kwargs, expanded=initially_expanded)


def compact_run_status_panel(
    *,
    status_label: str,
    primary_reason: str,
    details: tuple[str, ...] | list[str] = (),
    tone: str = "neutral",
    details_title: str = "Details anzeigen",
) -> ft.Container:
    """Prominent but dense run-interaction status — primary reason + optional details."""

    tones = {
        "checking": (COLOR_PRIMARY_SUBTLE, COLOR_PRIMARY, ft.Icons.HOURGLASS_TOP_ROUNDED),
        "blocked": (COLOR_WARNING_SOFT, COLOR_WARNING, ft.Icons.BLOCK_FLIPPED),
        "sandbox_not_connected": (COLOR_WARNING_SOFT, COLOR_WARNING, ft.Icons.LINK_OFF_ROUNDED),
        "failed": (COLOR_ERROR_SOFT, COLOR_ERROR, ft.Icons.ERROR_OUTLINE),
        "completed": (COLOR_SUCCESS_SOFT, COLOR_SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
        "ready": (COLOR_PRIMARY_SUBTLE, COLOR_PRIMARY, ft.Icons.PLAY_CIRCLE_OUTLINE),
        "idle": (COLOR_SURFACE_ALT, COLOR_TEXT_MUTED, ft.Icons.INFO_OUTLINE),
        "neutral": (COLOR_SURFACE_ALT, COLOR_TEXT_SECONDARY, ft.Icons.INFO_OUTLINE),
    }
    bg, fg, icon = tones.get(tone, tones["neutral"])
    body: list[ft.Control] = [
        ft.Row(
            [
                ft.Icon(icon, size=16, color=fg),
                ft.Text(
                    status_label,
                    size=FONT_SIZE_METADATA,
                    weight=ft.FontWeight.W_700,
                    color=fg,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ft.Text(
            primary_reason,
            size=FONT_SIZE_BODY,
            color=COLOR_TEXT_PRIMARY,
            weight=ft.FontWeight.W_600,
        ),
    ]
    detail_lines = [str(item).strip() for item in details if str(item or "").strip()]
    if detail_lines:
        body.append(collapsible_details(*detail_lines, title=details_title))
    return ft.Container(
        margin=ft.Margin.only(bottom=6),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        border=ft.Border.all(1, fg),
        border_radius=RADIUS_CARD,
        bgcolor=bg,
        content=ft.Column(body, spacing=4, tight=True),
    )


def compact_checklist_block(
    items: tuple[tuple[bool, str], ...] | list[tuple[bool, str]],
    *,
    title: str = "Checkliste",
) -> ft.Container:
    """Dense checklist without one metadata row per item."""

    rows: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_HELPER,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_MUTED,
        ),
    ]
    for done, label in items:
        mark = "☑" if done else "☐"
        rows.append(
            ft.Text(
                f"{mark} {label}",
                size=FONT_SIZE_HELPER,
                color=COLOR_TEXT_SECONDARY,
            )
        )
    return ft.Container(
        margin=ft.Margin.only(bottom=8),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        bgcolor=COLOR_SURFACE,
        content=ft.Column(rows, spacing=2, tight=True),
    )


def compact_capability_matrix(
    items: tuple[tuple[str, str], ...] | list[tuple[str, str]],
    *,
    title: str = "Fähigkeiten",
) -> ft.Container:
    """Compact capability matrix as wrapped chips — no tall readiness table."""

    chips: list[ft.Control] = [
        ft.Container(
            border=ft.Border.all(1, COLOR_BORDER),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            bgcolor=COLOR_SURFACE_ALT,
            content=ft.Text(
                f"{label}: {status}",
                size=FONT_SIZE_HELPER,
                color=COLOR_TEXT_SECONDARY,
            ),
        )
        for label, status in items
        if str(label or "").strip()
    ]
    return ft.Container(
        margin=ft.Margin.only(bottom=8),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        bgcolor=COLOR_SURFACE,
        content=ft.Column(
            [
                ft.Text(
                    title,
                    size=FONT_SIZE_HELPER,
                    weight=ft.FontWeight.W_700,
                    color=COLOR_TEXT_MUTED,
                ),
                ft.Row(chips, spacing=6, wrap=True, tight=True),
            ],
            spacing=6,
            tight=True,
        ),
    )


def dense_card(*controls: ft.Control, margin_bottom: int = 8) -> ft.Container:
    """Smaller card shell for repeated status / readiness blocks."""

    return ft.Container(
        margin=ft.Margin.only(bottom=margin_bottom),
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        content=ft.Column(list(controls), spacing=2, tight=True),
    )


def make_value_tag_pill(
    label: str,
    *,
    on_remove: Callable[[ft.ControlEvent], None] | None = None,
) -> ft.Container:
    """Read-only or removable value chip — pill shape, not button-like."""
    row_items: list[ft.Control] = [
        ft.Text(label, size=11, color=COLOR_PRIMARY, weight=ft.FontWeight.W_500),
    ]
    if on_remove is not None:
        row_items.append(
            ft.Container(
                width=16,
                height=16,
                border_radius=8,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=on_remove,
                content=ft.Text("×", size=12, color=COLOR_TEXT_MUTED),
            )
        )
    return ft.Container(
        bgcolor=COLOR_PRIMARY_SUBTLE,
        border_radius=12,
        padding=ft.Padding.only(left=10, right=6 if on_remove else 10, top=4, bottom=4),
        content=ft.Row(row_items, spacing=4, tight=True),
    )


def make_matching_rule_display(feature_label: str, values: tuple[str, ...] | list[str]) -> ft.Control:
    """Make RuleDisplay — field label, operator chip, value tags."""
    cleaned = [value.strip() for value in values if str(value or "").strip()]
    if not feature_label or not cleaned:
        return ft.Text(
            "Keine Regel definiert",
            size=FONT_SIZE_METADATA,
            color=COLOR_MUTED_LIGHT,
            italic=True,
        )
    chips: list[ft.Control] = [
        ft.Text(feature_label, size=FONT_SIZE_METADATA, color=COLOR_TEXT_SECONDARY, weight=ft.FontWeight.W_500),
        ft.Container(
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            border_radius=12,
            bgcolor=COLOR_SURFACE_ALT,
            content=ft.Text("ist", size=11, color=COLOR_TEXT_MUTED),
        ),
    ]
    for value in cleaned:
        chips.append(make_value_tag_pill(value))
    return ft.Row(chips, spacing=6, wrap=True)


def make_workflow_phase(phase_num: int, title: str, body: ft.Control) -> ft.Column:
    """Single workflow column content."""
    return ft.Column(
        [
            ft.Text(
                f"PHASE {phase_num}",
                size=FONT_SIZE_NAV_GROUP,
                weight=ft.FontWeight.W_700,
                color=COLOR_TEXT_MUTED,
            ),
            ft.Container(height=4),
            ft.Text(
                title,
                size=FONT_SIZE_BODY,
                weight=ft.FontWeight.W_700,
                color=COLOR_TEXT_PRIMARY,
            ),
            ft.Container(height=14),
            body,
        ],
        spacing=0,
        tight=True,
    )


def make_workflow_panel(
    eingang: ft.Column,
    verarbeitung: ft.Column,
    ergebnisse: ft.Column,
    *,
    center_width: int = 128,
) -> ft.Container:
    """Make unified workflow panel — wide sides, narrow centered processing."""
    divider_h = WORKFLOW_PANEL_MIN_HEIGHT - 24

    def _phase(content: ft.Column, *, width: int | None = None, center: bool = False) -> ft.Container:
        return ft.Container(
            width=width,
            expand=width is None,
            padding=16,
            alignment=ft.Alignment.TOP_CENTER if center else ft.Alignment.TOP_LEFT,
            content=content,
        )

    row_items: list[ft.Control] = [
        _phase(eingang),
        ft.Container(width=1, height=divider_h, bgcolor=COLOR_BORDER, margin=ft.Margin.symmetric(vertical=12)),
        _phase(verarbeitung, width=center_width, center=True),
        ft.Container(width=1, height=divider_h, bgcolor=COLOR_BORDER, margin=ft.Margin.symmetric(vertical=12)),
        _phase(ergebnisse),
    ]
    return ft.Container(
        height=WORKFLOW_PANEL_MIN_HEIGHT,
        margin=ft.Margin.only(bottom=12),
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Row(
            row_items,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def make_tab_bar(
    tabs: tuple[tuple[str, str], ...],
    *,
    active_id: str,
    on_select: Callable[[str], None],
    badges: dict[str, int] | None = None,
) -> ft.Container:
    """Make underline tab bar."""
    badge_map = badges or {}
    tab_controls: list[ft.Control] = []
    for tab_id, label in tabs:
        is_active = tab_id == active_id
        label_row: list[ft.Control] = [
            ft.Text(
                label,
                size=FONT_SIZE_BODY,
                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
                color=COLOR_TEXT_PRIMARY if is_active else COLOR_TEXT_MUTED,
            ),
        ]
        count = badge_map.get(tab_id, 0)
        if count > 0:
            label_row.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=6, vertical=1),
                    border_radius=99,
                    bgcolor=COLOR_ERROR,
                    content=ft.Text(str(count), size=10, weight=ft.FontWeight.W_700, color=COLOR_SURFACE),
                )
            )
        tab_controls.append(
            ft.Container(
                on_click=lambda _e, tid=tab_id: on_select(tid),
                ink=True,
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                border=ft.Border(bottom=ft.BorderSide(2, COLOR_PRIMARY if is_active else ft.Colors.TRANSPARENT)),
                content=ft.Row(label_row, spacing=6),
            )
        )
    return ft.Container(
        margin=ft.Margin.only(bottom=12),
        border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
        content=ft.Row(tab_controls, spacing=0),
    )


def make_scroll_file_list(*filenames: str, max_items: int = 10, height: int = 120) -> ft.Container:
    """Scrollable mono file list — one line per file, ellipsis overflow."""
    visible = list(filenames[:max_items])
    if not visible:
        visible = ["Keine PDF-Dateien"]
    rows = [
        ft.Text(
            name,
            size=11,
            font_family="Menlo",
            color=COLOR_TEXT_MUTED,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            no_wrap=True,
        )
        for name in visible
    ]
    if len(filenames) > max_items:
        rows.append(ft.Text(f"+ {len(filenames) - max_items} weitere …", size=10, color=COLOR_MUTED_LIGHT, italic=True))
    return ft.Container(
        height=height,
        border=ft.Border(top=ft.BorderSide(1, COLOR_BORDER)),
        padding=ft.Padding.only(top=6),
        content=ft.ListView(rows, spacing=2, padding=0, auto_scroll=False),
    )


def make_full_width_panel(content: ft.Control) -> ft.Container:
    """White panel matching workflow width."""
    return ft.Container(
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=content,
    )


def make_accent_cta_button(
    label: str,
    *,
    on_click: Callable[[ft.ControlEvent], None],
    disabled: bool = False,
) -> ft.FilledButton:
    """Solid accent CTA — e.g. „Neu starten“ in workspace run panel."""
    return ft.FilledButton(
        content=label,
        on_click=on_click,
        disabled=disabled,
        height=28,
        bgcolor=COLOR_PRIMARY,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=ft.Padding.symmetric(horizontal=12, vertical=4),
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.W_500, color="#ffffff"),
        ),
    )


def make_file_mapping_row(source: str, target: str) -> ft.Container:
    """Single Eingang → Ergebnis mapping row inside workspace run panel."""
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=7),
        content=ft.Row(
            [
                ft.Text(
                    source,
                    size=11,
                    font_family="Menlo",
                    color=COLOR_TEXT_MUTED,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    no_wrap=True,
                    expand=True,
                ),
                ft.Text("→", size=11, color=COLOR_BORDER_STRONG),
                ft.Text(
                    target,
                    size=11,
                    font_family="Menlo",
                    color=COLOR_TEXT_SECONDARY,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    no_wrap=True,
                    expand=True,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def make_workspace_folder_row(
    *,
    label: str,
    path_display: str | None,
    empty_text: str,
    pick_label: str,
    on_pick: Callable[[ft.ControlEvent], None] | None,
    pick_disabled: bool = False,
) -> ft.Container:
    """Single input/output folder row — path display or honest empty copy; no FS IO."""

    path_control: ft.Control
    if path_display:
        path_control = ft.Text(
            path_display,
            size=12,
            font_family="Menlo",
            color=COLOR_TEXT_SECONDARY,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
            selectable=True,
            expand=True,
        )
    else:
        path_control = ft.Text(
            empty_text,
            size=12,
            color=COLOR_MUTED_LIGHT,
            expand=True,
        )

    actions: list[ft.Control] = []
    if on_pick is not None:
        actions.append(
            secondary_button(pick_label, on_click=on_pick, disabled=pick_disabled)
        )

    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        content=ft.Column(
            [
                ft.Text(
                    label,
                    size=FONT_SIZE_NAV_GROUP,
                    weight=ft.FontWeight.W_700,
                    color=COLOR_TEXT_MUTED,
                ),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.FOLDER_OUTLINED, size=14, color=COLOR_TEXT_MUTED),
                        path_control,
                        *actions,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=6,
        ),
    )


def make_workspace_folder_selection_panel(
    *,
    input_path_display: str | None,
    output_path_display: str | None,
    input_empty_text: str,
    output_empty_text: str,
    input_pick_label: str,
    output_pick_label: str,
    on_pick_input: Callable[[ft.ControlEvent], None] | None,
    on_pick_output: Callable[[ft.ControlEvent], None] | None,
    pick_disabled: bool = False,
) -> ft.Container:
    """Workspace input/output folder selection — state wiring only; never processes PDFs."""

    rows: list[ft.Control] = [
        make_workspace_folder_row(
            label="Eingangsordner",
            path_display=input_path_display,
            empty_text=input_empty_text,
            pick_label=input_pick_label,
            on_pick=on_pick_input,
            pick_disabled=pick_disabled,
        ),
        divider(),
        make_workspace_folder_row(
            label="Ausgabeordner",
            path_display=output_path_display,
            empty_text=output_empty_text,
            pick_label=output_pick_label,
            on_pick=on_pick_output,
            pick_disabled=pick_disabled,
        ),
    ]
    return ft.Container(
        margin=ft.Margin.only(bottom=12),
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(rows, spacing=0),
    )


def make_workspace_run_panel(
    *,
    folder_path: str | None,
    on_change_folder: Callable[[ft.ControlEvent], None] | None,
    on_pick_folder: Callable[[ft.ControlEvent], None] | None,
    on_restart: Callable[[ft.ControlEvent], None] | None,
    on_details: Callable[[ft.ControlEvent], None] | None,
    ok_count: int | None,
    fail_count: int | None,
    mappings: tuple[tuple[str, str], ...],
    on_start: Callable[[ft.ControlEvent], None] | None = None,
    start_label: str = "Verarbeitung starten",
    start_disabled: bool = False,
    pick_folder_label: str = "Ordner auswählen",
    empty_folder_text: str = "Kein Ordner ausgewählt",
) -> ft.Container:
    """Figma workspace run panel — folder toolbar + Eingangs/Ergebnis mapping list."""
    header_left: list[ft.Control]
    if folder_path:
        header_left = [
            ft.Icon(ft.Icons.FOLDER_OUTLINED, size=14, color=COLOR_TEXT_MUTED),
            ft.Text(
                folder_path,
                size=12,
                font_family="Menlo",
                color=COLOR_TEXT_SECONDARY,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                no_wrap=True,
                expand=True,
            ),
        ]
    else:
        header_left = [
            ft.Text(empty_folder_text, size=12, color=COLOR_MUTED_LIGHT, expand=True),
        ]

    header_actions: list[ft.Control] = []
    if folder_path and on_change_folder is not None:
        header_actions.append(secondary_button("Ändern", on_click=on_change_folder))
    elif on_pick_folder is not None:
        header_actions.append(secondary_button(pick_folder_label, on_click=on_pick_folder))
    if on_start is not None:
        header_actions.append(
            make_accent_cta_button(
                start_label,
                on_click=on_start,
                disabled=start_disabled,
            )
        )
    if folder_path and on_restart is not None:
        header_actions.append(make_accent_cta_button("Neu starten", on_click=on_restart))

    if folder_path and ok_count is not None and fail_count is not None:
        header_actions.extend(
            [
                ft.Text(f"{ok_count} OK", size=11, weight=ft.FontWeight.W_600, color=COLOR_SUCCESS),
                ft.Text(f"{fail_count} Fehler", size=11, weight=ft.FontWeight.W_600, color=COLOR_ERROR),
                ft.TextButton(
                    content="Details →",
                    on_click=on_details,
                    style=ft.ButtonStyle(
                        color=COLOR_PRIMARY,
                        padding=ft.Padding.symmetric(horizontal=4, vertical=0),
                        text_style=ft.TextStyle(size=11, weight=ft.FontWeight.W_500),
                    ),
                ),
            ]
        )

    mapping_section: ft.Control
    if folder_path and mappings:
        mapping_rows: list[ft.Control] = [
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                bgcolor=COLOR_SURFACE_ALT,
                border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
                content=ft.Row(
                    [
                        ft.Text(
                            "EINGANGSORDNER",
                            size=FONT_SIZE_NAV_GROUP,
                            weight=ft.FontWeight.W_700,
                            color=COLOR_TEXT_MUTED,
                            expand=True,
                        ),
                        ft.Container(width=16),
                        ft.Text(
                            "ERGEBNISORDNER",
                            size=FONT_SIZE_NAV_GROUP,
                            weight=ft.FontWeight.W_700,
                            color=COLOR_TEXT_MUTED,
                            expand=True,
                        ),
                    ],
                ),
            ),
        ]
        for index, (source, target) in enumerate(mappings):
            if index > 0:
                mapping_rows.append(divider())
            mapping_rows.append(make_file_mapping_row(source, target))
        mapping_section = ft.Container(
            height=min(220, 44 + len(mappings) * 34),
            content=ft.Column(mapping_rows, spacing=0, scroll=ft.ScrollMode.AUTO),
        )
    elif folder_path:
        mapping_section = ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=24),
            alignment=ft.Alignment.CENTER,
            content=ft.Text("Noch keine Zuordnungen", size=12, color=COLOR_MUTED_LIGHT),
        )
    else:
        mapping_section = ft.Container(height=0)

    return ft.Container(
        margin=ft.Margin.only(bottom=12),
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
                    content=ft.Row(
                        [
                            ft.Row(header_left, spacing=8, expand=True),
                            ft.Row(header_actions, spacing=8, wrap=False),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                mapping_section,
            ],
            spacing=0,
            tight=True,
        ),
    )


def make_ergebnis_row(
    *,
    result_id: str,
    source_filename: str,
    target_filename: str,
    configuration_label: str,
    failed: bool,
    reason: str | None = None,
    suggestion: str | None = None,
    action_label: str | None = None,
    expanded: bool = False,
    on_toggle: Callable[[ft.ControlEvent], None] | None = None,
    on_action: Callable[[ft.ControlEvent], None] | None = None,
) -> ft.Column:
    """Figma ErgebnisRow — success two-line layout, failure with expandable suggestion."""
    if failed:
        status_icon = ft.Container(
            width=18,
            height=18,
            border_radius=9,
            bgcolor=COLOR_ERROR_SOFT,
            border=ft.Border.all(1, COLOR_ERROR),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.CLOSE, size=10, color=COLOR_ERROR),
        )
        filename_control = ft.Text(
            source_filename,
            size=12,
            font_family="Menlo",
            color=COLOR_ERROR,
            weight=ft.FontWeight.W_500,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            no_wrap=True,
            expand=True,
        )
        trailing = ft.Row(
            [
                ft.Text(reason or "Fehlgeschlagen", size=11, color=COLOR_ERROR, no_wrap=True),
                ft.Icon(
                    ft.Icons.KEYBOARD_ARROW_DOWN if expanded else ft.Icons.KEYBOARD_ARROW_RIGHT,
                    size=14,
                    color=COLOR_TEXT_MUTED,
                ),
            ],
            spacing=8,
            tight=True,
        )
        row_bg = COLOR_ERROR_SOFT
    else:
        status_icon = ft.Container(
            width=18,
            height=18,
            border_radius=9,
            bgcolor=COLOR_SUCCESS_SOFT,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.CHECK, size=10, color=COLOR_SUCCESS),
        )
        filename_control = ft.Column(
            [
                ft.Text(
                    target_filename,
                    size=13,
                    weight=ft.FontWeight.W_500,
                    color=COLOR_TEXT_PRIMARY,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    source_filename,
                    size=11,
                    font_family="Menlo",
                    color=COLOR_TEXT_MUTED,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=2,
            expand=True,
        )
        trailing = ft.Row(
            [
                ft.Text(f"→ {configuration_label}", size=11, color=COLOR_TEXT_MUTED, no_wrap=True),
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=14, color=COLOR_TEXT_MUTED),
            ],
            spacing=4,
            tight=True,
        )
        row_bg = None

    header = ft.Container(
        bgcolor=row_bg,
        padding=ft.Padding.symmetric(horizontal=16, vertical=9),
        on_click=on_toggle if failed and on_toggle else None,
        ink=bool(failed and on_toggle),
        content=ft.Row(
            [
                status_icon,
                filename_control,
                trailing,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
    sections: list[ft.Control] = [header]
    if failed and expanded and suggestion:
        sections.append(
            ft.Container(
                margin=ft.Margin.only(left=16, right=16, bottom=10),
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                bgcolor=COLOR_WARNING_SOFT,
                border=ft.Border.all(1, COLOR_WARN_BORDER),
                border_radius=6,
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, size=13, color=COLOR_WARNING),
                        ft.Column(
                            [
                                ft.Text(
                                    "Handlungsvorschlag",
                                    size=11,
                                    weight=ft.FontWeight.W_700,
                                    color=COLOR_WARNING,
                                ),
                                ft.Text(suggestion, size=12, color=COLOR_WARNING),
                                secondary_button(action_label or "Konfiguration bearbeiten", on_click=on_action)
                                if on_action
                                else ft.Container(),
                            ],
                            spacing=6,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            )
        )
    return ft.Column(sections, spacing=0, tight=True)


def make_destination_list_row(
    name: str,
    path: str,
    *,
    missing: bool,
    on_correct: Callable[[ft.ControlEvent], None] | None = None,
) -> ft.Container:
    """Zielordner list row — name, mono path, badge, optional Korrigieren."""
    trailing: list[ft.Control] = []
    if missing:
        trailing.append(status_badge("Nicht erreichbar", tone="fehlt"))
    if on_correct is not None:
        trailing.append(secondary_button("Korrigieren", on_click=on_correct))
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(name, size=FONT_SIZE_BODY, weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY),
                        ft.Text(
                            path,
                            size=11,
                            color=COLOR_TEXT_MUTED,
                            font_family="Menlo",
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Row(trailing, spacing=10) if trailing else ft.Container(),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def make_workspace_result_row(
    result_id: str,
    source_filename: str,
    target_filename: str,
    configuration_label: str,
    destination_summary: str,
    status_label: str,
    *,
    failed: bool,
    expanded: bool,
    rename_value: str,
    on_toggle: Callable[[ft.ControlEvent], None],
    on_rename_change: Callable[[ft.ControlEvent], None],
) -> ft.Column:
    """Expandable workspace result row with optional rename draft."""
    tone = "fehlt" if failed else "active"
    header = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        content=ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_ARROW_DOWN if expanded else ft.Icons.KEYBOARD_ARROW_RIGHT,
                    icon_size=18,
                    on_click=on_toggle,
                    style=ft.ButtonStyle(padding=0),
                ),
                ft.Column(
                    [
                        ft.Text(source_filename, size=13, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(
                            f"{configuration_label} → {target_filename}",
                            size=11,
                            color=COLOR_TEXT_MUTED,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                status_badge(status_label, tone=tone),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
    sections: list[ft.Control] = [header]
    if expanded:
        sections.append(
            ft.Container(
                padding=ft.Padding.only(left=48, right=16, bottom=12),
                content=ft.Column(
                    [
                        ft.Text("Zieldatei", size=10, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.W_600),
                        ft.TextField(
                            value=rename_value,
                            dense=True,
                            text_size=12,
                            on_change=on_rename_change,
                            hint_text="Vorschlag bearbeiten",
                        ),
                        ft.Text(
                            display_path_value(destination_summary),
                            size=10,
                            color=COLOR_TEXT_MUTED,
                            font_family="Menlo",
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=6,
                    tight=True,
                ),
            )
        )
    return ft.Column(sections, spacing=0, tight=True)


def make_settings_panel(*rows: ft.Control) -> ft.Container:
    """Settings metadata panel — rows only, no internal title."""
    return ft.Container(
        margin=ft.Margin.only(bottom=12),
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=16, vertical=2),
        content=ft.Column(list(rows), spacing=0),
    )


def make_panel_footer_profile(
    *leading: ft.Control,
    primary: ft.Control | None = None,
    destructive: ft.Control | None = None,
) -> ft.Container:
    """Profile view footer — leading actions, optional primary, destructive on far right."""
    row_items: list[ft.Control] = list(leading)
    if primary is not None:
        row_items.append(primary)
    if destructive is not None:
        row_items.extend([ft.Container(expand=True), destructive])
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=18, vertical=12),
        border=ft.Border(top=ft.BorderSide(1, COLOR_BORDER)),
        bgcolor=COLOR_SURFACE,
        content=ft.Row(row_items, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=False),
    )


def metric_line(label: str, value: str, *, monospace: bool = False) -> ft.Row:
    """Eine kompakte Kennzahl pro Zeile (label links, Wert rechts)."""
    value_control: ft.Control = path_value_text(value) if monospace else ft.Text(
        value,
        size=FONT_SIZE_BODY,
        color=COLOR_TEXT_PRIMARY,
        weight=ft.FontWeight.W_500,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
        expand=True,
    )
    return ft.Row(
        controls=[
            ft.Text(label, size=FONT_SIZE_METADATA, color=COLOR_TEXT_MUTED, width=METADATA_LABEL_WIDTH),
            value_control,
        ],
        spacing=SPACE_SM,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def metric_tile_row(*tiles: ft.Control) -> ft.Row:
    """Horizontal row of compact metric tiles inside a workflow card."""
    return ft.Row(
        list(tiles),
        spacing=SPACE_SM,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def compact_card_grid(*cards: ft.Control) -> ft.Row:
    """Wrapped grid of compact cards (e.g. Zielordner overview)."""
    tile_width = max(COMPACT_CARD_MIN_WIDTH + 100, 280)
    return ft.Row(
        [ft.Container(width=tile_width, content=card) for card in cards],
        spacing=SPACE_MD,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


# ---------------------------------------------------------------------------
# Cards and panels
# ---------------------------------------------------------------------------


def section_card(title: str, body: ft.Control, *, expand: bool = False) -> ft.Container:
    return ft.Container(
        expand=expand,
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=PANEL_PADDING,
        content=ft.Column(
            [
                ft.Text(title, size=FONT_SIZE_CARD_TITLE, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                body,
            ],
            spacing=SPACE_SM,
        ),
    )


def neutral_card(title: str, body: str | ft.Control, *, expand: bool = False) -> ft.Container:
    content = body if isinstance(body, ft.Control) else ft.Text(str(body), size=FONT_SIZE_BODY, color=COLOR_TEXT_SECONDARY)
    return section_card(title, content, expand=expand)


def summary_card(label: str, value: str, *, hint: str | None = None, expand: bool = False) -> ft.Container:
    body: list[ft.Control] = [
        ft.Text(value, size=FONT_SIZE_BODY, color=COLOR_TEXT_PRIMARY, weight=ft.FontWeight.W_500),
    ]
    if hint:
        body.append(ft.Text(hint, size=FONT_SIZE_HELPER, color=COLOR_TEXT_MUTED))
    return ft.Container(
        expand=expand,
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=SPACE_LG,
        content=ft.Column(
            [
                ft.Text(label, size=FONT_SIZE_CAPTION, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.W_600),
                *body,
            ],
            spacing=SPACE_XS,
        ),
    )


def summary_tile(label: str, value: str) -> ft.Container:
    """Backward-compatible alias."""
    return summary_card(label, value)


def metric_tile(label: str, value: str, *, expand: bool = True) -> ft.Container:
    """Compact KPI tile — dense dashboard rhythm."""
    return ft.Container(
        expand=expand,
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
        content=ft.Column(
            [
                ft.Text(
                    label,
                    size=FONT_SIZE_CAPTION,
                    color=COLOR_TEXT_MUTED,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    value,
                    size=FONT_SIZE_CARD_TITLE,
                    color=COLOR_TEXT_PRIMARY,
                    weight=ft.FontWeight.W_600,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=2,
        ),
    )


def compact_metric(label: str, value: str) -> ft.Container:
    return metric_tile(label, value, expand=False)


def list_panel(
    title: str,
    body: ft.Control,
    *,
    width: int | None = None,
    height: int | None = None,
    expand: bool = False,
) -> ft.Container:
    container_kwargs: dict = {
        "key": "ui-v2-list-panel",
        "width": width or LIST_PANEL_MIN_WIDTH,
        "bgcolor": COLOR_SURFACE,
        "border": ft.Border.all(1, COLOR_BORDER),
        "border_radius": RADIUS_CARD,
        "clip_behavior": ft.ClipBehavior.ANTI_ALIAS,
        "content": ft.Column(
            [
                ft.Container(
                    padding=ft.Padding.only(left=14, right=14, top=10, bottom=8),
                    content=ft.Text(
                        title.upper(),
                        size=FONT_SIZE_NAV_GROUP,
                        weight=ft.FontWeight.W_700,
                        color=COLOR_TEXT_MUTED,
                    ),
                ),
                divider(),
                ft.Container(expand=True, content=body),
            ],
            spacing=0,
            expand=True,
        ),
    }
    if expand:
        container_kwargs["expand"] = True
    elif height is not None:
        container_kwargs["height"] = height
    else:
        container_kwargs["height"] = LIST_DETAIL_MIN_HEIGHT
    return ft.Container(**container_kwargs)


def make_create_list_marker(label: str) -> ft.Container:
    """Selected create row in list — Make accent rail."""
    return ft.Container(
        padding=ft.Padding.only(left=11, right=14, top=9, bottom=9),
        bgcolor=COLOR_ACCENT_FAINT,
        border=ft.Border(left=ft.BorderSide(3, COLOR_PRIMARY)),
        content=ft.Text(label, size=FONT_SIZE_BODY, weight=ft.FontWeight.W_600, color=COLOR_PRIMARY),
    )


def vertical_divider(*, height: int = 24) -> ft.Container:
    return ft.Container(width=1, height=height, bgcolor=COLOR_BORDER)


def make_metadata_row(
    label: str,
    value: str | ft.Control,
    *,
    mono: bool = False,
    warn: str | None = None,
    italic: bool = False,
) -> ft.Container:
    """Make MetadataRow — 168px label column, bottom border."""
    if isinstance(value, str):
        value_ctrl: ft.Control = ft.Text(
            value,
            size=FONT_SIZE_METADATA,
            color=COLOR_TEXT_MUTED if italic else COLOR_TEXT_SECONDARY,
            italic=italic,
            font_family="Menlo" if mono else None,
            selectable=True,
            max_lines=4,
        )
    else:
        value_ctrl = value
    value_col: list[ft.Control] = [value_ctrl]
    if warn:
        value_col.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=11, color=COLOR_WARNING),
                    ft.Text(warn, size=FONT_SIZE_HELPER, color=COLOR_WARNING, expand=True),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=8),
        border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
        content=ft.Row(
            [
                ft.Container(
                    width=METADATA_LABEL_WIDTH,
                    content=ft.Text(
                        label,
                        size=FONT_SIZE_METADATA,
                        color=COLOR_TEXT_MUTED,
                    ),
                ),
                ft.Column(value_col, spacing=4, expand=True),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def make_metadata_block(*rows: ft.Control) -> ft.Column:
    return ft.Column(list(rows), spacing=0)


def make_status_toggle_pill(*, active: bool, on_toggle: Callable[[ft.ControlEvent], None]) -> ft.Container:
    """Make view-mode active toggle in detail header."""
    dot_color = COLOR_PRIMARY if active else COLOR_BORDER_STRONG
    label = "Aktiv" if active else "Inaktiv"
    text_color = COLOR_PRIMARY if active else COLOR_TEXT_MUTED
    bg = COLOR_ACCENT_FAINT if active else COLOR_SURFACE
    border_color = COLOR_PRIMARY if active else COLOR_BORDER_STRONG
    return ft.Container(
        on_click=on_toggle,
        ink=True,
        border=ft.Border.all(1, border_color),
        border_radius=20,
        bgcolor=bg,
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        content=ft.Row(
            [
                ft.Container(width=6, height=6, border_radius=3, bgcolor=dot_color),
                ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=text_color),
            ],
            spacing=6,
        ),
    )


def make_panel_close_button(on_click: Callable[[ft.ControlEvent], None]) -> ft.IconButton:
    return ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_size=16,
        icon_color=COLOR_TEXT_MUTED,
        style=ft.ButtonStyle(padding=2),
        on_click=on_click,
    )


def make_panel_footer_start(*actions: ft.Control, destructive: ft.Control | None = None) -> ft.Container:
    """View footer — leading actions, destructive on far right."""
    row_items: list[ft.Control] = list(actions)
    if destructive is not None:
        row_items.extend([ft.Container(expand=True), destructive])
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=18, vertical=12),
        border=ft.Border(top=ft.BorderSide(1, COLOR_BORDER)),
        bgcolor=COLOR_SURFACE,
        content=ft.Row(row_items, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=False),
    )


def make_panel_footer_end(*actions: ft.Control) -> ft.Container:
    """Edit/create footer — actions right-aligned."""
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=18, vertical=12),
        border=ft.Border(top=ft.BorderSide(1, COLOR_BORDER)),
        bgcolor=COLOR_SURFACE,
        content=ft.Row(list(actions), alignment=ft.MainAxisAlignment.END, spacing=8, wrap=False),
    )


def make_split_detail_panel(
    title: str,
    body: ft.Control,
    *,
    height: int | None = None,
    header_trailing: ft.Control | None = None,
    footer: ft.Control | None = None,
    body_padding: ft.Padding | None = None,
    compact_body: bool = False,
    scroll_body: bool | None = None,
) -> ft.Container:
    """Make strong detail panel — header bar, body, optional footer."""
    pad = body_padding or ft.Padding.only(left=18, right=18, top=2, bottom=0)
    header_row: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_DETAIL_HEADER,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_PRIMARY,
            expand=True,
        ),
    ]
    if header_trailing is not None:
        header_row.append(header_trailing)
    use_scroll = scroll_body if scroll_body is not None else (height is not None and (footer is not None or not compact_body))
    if use_scroll and isinstance(body, ft.ListView):
        body_section = ft.Container(
            expand=True,
            padding=pad,
            alignment=ft.Alignment.TOP_LEFT,
            content=body,
        )
    elif use_scroll:
        body_section = ft.Container(
            expand=True,
            padding=pad,
            alignment=ft.Alignment.TOP_LEFT,
            content=ft.Column(
                [body],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=0,
                auto_scroll=False,
            ),
        )
    else:
        body_section = ft.Container(expand=True, padding=pad, alignment=ft.Alignment.TOP_LEFT, content=body)
    sections: list[ft.Control] = [
        ft.Container(
            bgcolor=COLOR_SURFACE_ALT,
            padding=ft.Padding.symmetric(horizontal=18, vertical=13),
            border=ft.Border(bottom=ft.BorderSide(1, COLOR_BORDER)),
            content=ft.Row(header_row, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ),
        body_section,
    ]
    if footer is not None:
        sections.append(footer)
    container_kwargs: dict = {
        "key": "ui-v2-detail-panel",
        "expand": True,
        "bgcolor": COLOR_SURFACE,
        "border": ft.Border.all(1, COLOR_BORDER_STRONG),
        "border_radius": RADIUS_CARD,
        "clip_behavior": ft.ClipBehavior.ANTI_ALIAS,
        "content": ft.Column(sections, spacing=0, expand=True),
    }
    if height is not None:
        container_kwargs["height"] = height
    return ft.Container(**container_kwargs)


def detail_panel(title: str, body: ft.Control, *, height: int | None = None) -> ft.Container:
    """Backward-compatible alias — prefer make_split_detail_panel."""
    return make_split_detail_panel(title, body, height=height)


def compact_card(title: str, body: ft.Control, *, trailing: ft.Control | None = None) -> ft.Container:
    header: list[ft.Control] = [
        ft.Text(title, size=FONT_SIZE_CARD_TITLE, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY, expand=True),
    ]
    if trailing is not None:
        header = [ft.Row(header + [trailing], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]
    return ft.Container(
        bgcolor=COLOR_SURFACE,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_CARD,
        padding=SPACE_LG,
        content=ft.Column(header + [body], spacing=SPACE_SM),
    )


# ---------------------------------------------------------------------------
# List items
# ---------------------------------------------------------------------------


def make_form_status_toggle(*, active: bool, on_change: Callable[[bool], None]) -> ft.Column:
    """Make StatusToggle — Aktiv/Inaktiv segmented control."""
    def _button(value: bool, label: str) -> ft.Container:
        selected = active == value
        if selected and value:
            bg, fg, border = COLOR_SUCCESS_SOFT, COLOR_SUCCESS, COLOR_SUCCESS
        elif selected:
            bg, fg, border = "#f0f0f2", COLOR_MUTED_LIGHT, COLOR_BORDER_STRONG
        else:
            bg, fg, border = COLOR_SURFACE, COLOR_TEXT_MUTED, COLOR_BORDER
        return ft.Container(
            on_click=lambda _e, v=value: on_change(v),
            ink=True,
            border=ft.Border.all(1, border),
            border_radius=6,
            bgcolor=bg,
            padding=ft.Padding.symmetric(horizontal=12, vertical=5),
            content=ft.Text(label, size=12, weight=ft.FontWeight.W_500, color=fg),
        )

    return ft.Column(
        [
            ft.Text(
                "STATUS",
                size=10,
                weight=ft.FontWeight.W_700,
                color=COLOR_TEXT_MUTED,
            ),
            ft.Row([_button(True, "Aktiv"), _button(False, "Inaktiv")], spacing=6),
        ],
        spacing=5,
    )


def compact_list_item(
    title: str,
    *,
    subtitle: str | None = None,
    trailing: ft.Control | None = None,
    selected: bool = False,
    on_select: Callable[[ft.ControlEvent], None] | None = None,
) -> ft.Container:
    """Selectable list row — left accent rail, flat list rhythm."""
    title_row: list[ft.Control] = [
        ft.Text(
            title,
            size=FONT_SIZE_BODY,
            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
            color=COLOR_PRIMARY if selected else COLOR_TEXT_PRIMARY,
            expand=True,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
    ]
    if trailing is not None:
        title_row.append(ft.Container(content=trailing, margin=ft.Margin.only(left=8)))
    body: list[ft.Control] = [ft.Row(title_row, spacing=SPACE_SM, vertical_alignment=ft.CrossAxisAlignment.CENTER)]
    if subtitle:
        body.append(
            ft.Text(
                subtitle,
                size=FONT_SIZE_CAPTION,
                color=COLOR_TEXT_MUTED,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )
    return ft.Container(
        bgcolor=COLOR_ACCENT_FAINT if selected else None,
        border=ft.Border(left=ft.BorderSide(3, COLOR_PRIMARY if selected else ft.Colors.TRANSPARENT)),
        padding=ft.Padding.only(left=11 if selected else 14, right=14, top=9, bottom=9),
        on_click=on_select,
        ink=on_select is not None,
        content=ft.Column(body, spacing=SPACE_XS),
    )


# ---------------------------------------------------------------------------
# Status, warnings, empty states
# ---------------------------------------------------------------------------


def status_badge(label: str, *, tone: str = "neutral") -> ft.Container:
    """Non-interactive status stamp — uppercase, compact."""
    colors = {
        "neutral": ("#f0f0f2", COLOR_TEXT_MUTED),
        "active": (COLOR_SUCCESS_SOFT, COLOR_SUCCESS),
        "inactive": ("#f0f0f2", COLOR_MUTED_LIGHT),
        "selected": (COLOR_PRIMARY, COLOR_SURFACE),
        "warning": (COLOR_WARNING_SOFT, COLOR_WARNING),
        "error": (COLOR_ERROR_SOFT, COLOR_ERROR),
        "success": (COLOR_SUCCESS_SOFT, COLOR_SUCCESS),
        "fehlt": (COLOR_ERROR_SOFT, COLOR_ERROR),
    }
    bg, fg = colors.get(tone, colors["neutral"])
    display = label.upper() if tone in {"active", "inactive", "warning", "error", "fehlt"} else label
    return ft.Container(
        bgcolor=bg,
        border_radius=3,
        padding=ft.Padding.symmetric(horizontal=5, vertical=1),
        content=ft.Text(
            display,
            size=9,
            color=fg,
            weight=ft.FontWeight.W_700,
        ),
    )


def warning_message(message: str) -> ft.Container:
    return inline_warning(message)


def summary_alert(message: str) -> ft.Container:
    """Section-level alert — one banner instead of repeated row warnings."""
    return ft.Container(
        margin=ft.Margin.only(bottom=10),
        bgcolor=COLOR_WARNING_SOFT,
        border=ft.Border.all(1, COLOR_WARNING),
        border_radius=RADIUS_CARD,
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=15, color=COLOR_WARNING),
                ft.Text(message, size=FONT_SIZE_BODY, color=COLOR_WARNING, expand=True),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def focus_panel(body: ft.Control) -> ft.Container:
    """Content well for sparse pages — reduces lost-in-whitespace effect."""
    return ft.Container(
        bgcolor=COLOR_SURFACE_ALT,
        border=ft.Border.all(1, COLOR_BORDER),
        border_radius=RADIUS_PANEL,
        padding=PANEL_PADDING,
        content=body,
    )


def inline_warning(message: str) -> ft.Container:
    """Non-interactive inline warning — icon + message (Carbon/MD3 pattern)."""
    return ft.Container(
        bgcolor=COLOR_WARNING_SOFT,
        border=ft.Border.all(1, COLOR_WARNING),
        border_radius=RADIUS_CARD,
        padding=SPACE_MD,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=18, color=COLOR_WARNING),
                ft.Text(message, size=FONT_SIZE_CAPTION, color=COLOR_WARNING, selectable=True, expand=True),
            ],
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def inline_error(message: str) -> ft.Container:
    return ft.Container(
        bgcolor=COLOR_ERROR_SOFT,
        border=ft.Border.all(1, COLOR_ERROR),
        border_radius=RADIUS_CARD,
        padding=SPACE_MD,
        content=ft.Text(message, size=FONT_SIZE_CAPTION, color=COLOR_ERROR, selectable=True),
    )


def empty_state(
    title: str,
    *,
    detail: str | None = None,
    icon: str | None = ft.Icons.INBOX_OUTLINED,
    compact: bool = True,
) -> ft.Container:
    """Centered empty state — accent icon circle (compact by default)."""
    body: list[ft.Control] = []
    if icon:
        size = 36 if compact else 52
        body.append(
            ft.Container(
                width=size,
                height=size,
                bgcolor=COLOR_ACCENT_FAINT,
                border=ft.Border.all(1, COLOR_PRIMARY_SUBTLE),
                border_radius=size // 2,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, size=16 if compact else 22, color=COLOR_PRIMARY),
            )
        )
    body.append(
        ft.Text(
            title,
            size=13 if compact else 15,
            color=COLOR_TEXT_PRIMARY,
            weight=ft.FontWeight.W_700,
            text_align=ft.TextAlign.CENTER,
        )
    )
    if detail:
        body.append(
            ft.Container(
                width=320 if compact else 340,
                content=ft.Text(
                    detail,
                    size=FONT_SIZE_HELPER if compact else FONT_SIZE_BODY,
                    color=COLOR_TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=3 if compact else None,
                ),
            )
        )
    return ft.Container(
        padding=ft.Padding.symmetric(
            horizontal=SPACE_MD if compact else SPACE_XL,
            vertical=SPACE_MD if compact else SPACE_3XL,
        ),
        content=ft.Column(
            body,
            spacing=6 if compact else 14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
    )


# ---------------------------------------------------------------------------
# Metadata and forms
# ---------------------------------------------------------------------------


def metadata_row(label: str, value: str, *, monospace: bool = False) -> ft.Row:
    """Horizontal definition row — Stripe/Settings pattern for detail panels."""
    if monospace:
        value_control: ft.Control = path_value_text(value)
    else:
        value_control = ft.Text(
            value,
            size=FONT_SIZE_BODY,
            color=COLOR_TEXT_PRIMARY,
            selectable=True,
            max_lines=3,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
    return ft.Row(
        controls=[
            ft.Text(label, size=FONT_SIZE_METADATA, color=COLOR_TEXT_MUTED, width=METADATA_LABEL_WIDTH),
            value_control,
        ],
        spacing=SPACE_SM,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def metadata_row_inline(label: str, value: str) -> ft.Row:
    """Compact inline metadata — label + value on one line."""
    return ft.Row(
        controls=[
            ft.Text(f"{label}:", size=FONT_SIZE_METADATA, color=COLOR_TEXT_MUTED),
            ft.Text(
                value,
                size=FONT_SIZE_BODY,
                color=COLOR_TEXT_PRIMARY,
                weight=ft.FontWeight.W_500,
                selectable=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                expand=True,
            ),
        ],
        spacing=SPACE_XS,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def key_value_row(label: str, value: str) -> ft.Row:
    """Backward-compatible alias."""
    return metadata_row(label, value)


def field_error(message: str) -> ft.Text:
    return ft.Text(message, size=FONT_SIZE_HELPER, color=COLOR_ERROR)


def form_field_group(label: str, field: ft.Control, *, error: str | None = None, helper: str | None = None) -> ft.Column:
    items: list[ft.Control] = [
        ft.Text(
            label.upper(),
            size=FONT_SIZE_NAV_GROUP,
            weight=ft.FontWeight.W_700,
            color=COLOR_TEXT_MUTED,
        ),
        field,
    ]
    if error:
        items.append(field_error(error))
    if helper:
        items.append(ft.Text(helper, size=FONT_SIZE_HELPER, color=COLOR_TEXT_MUTED))
    return ft.Column(items, spacing=SPACE_SM, tight=True)


def divider() -> ft.Divider:
    return ft.Divider(height=1, color=COLOR_BORDER)


# ---------------------------------------------------------------------------
# Buttons and action bars
# ---------------------------------------------------------------------------


def _outline_button_style(*, text_color: str = COLOR_TEXT_SECONDARY) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        color=text_color,
        # Slightly tinted surface (not pure white) so outline buttons stay
        # visible as buttons against the white panel background instead of
        # looking transparent/invisible with just a hairline border.
        bgcolor=COLOR_SURFACE_ALT,
        elevation=0,
        side=ft.BorderSide(1, COLOR_BORDER),
        shape=ft.RoundedRectangleBorder(radius=6),
        padding=ft.Padding.symmetric(horizontal=10, vertical=3),
        text_style=ft.TextStyle(size=12, weight=ft.FontWeight.W_500),
    )


def primary_button(label: str, *, on_click: Callable[[ft.ControlEvent], None], disabled: bool = False, height: int = 28) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        content=label,
        on_click=on_click,
        disabled=disabled,
        height=height,
        style=_outline_button_style(text_color=COLOR_PRIMARY),
    )


def secondary_button(label: str, *, on_click: Callable[[ft.ControlEvent], None], disabled: bool = False, height: int = 28) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        content=label,
        on_click=on_click,
        disabled=disabled,
        height=height,
        style=_outline_button_style(),
    )


def tertiary_button(label: str, *, on_click: Callable[[ft.ControlEvent], None], disabled: bool = False) -> ft.TextButton:
    return ft.TextButton(content=label, on_click=on_click, disabled=disabled)


def destructive_button(label: str, *, on_click: Callable[[ft.ControlEvent], None], disabled: bool = False) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        content=label,
        on_click=on_click,
        disabled=disabled,
        height=28,
        style=_outline_button_style(text_color=COLOR_ERROR),
    )


def action_bar(*controls: ft.Control, destructive: ft.Control | None = None) -> ft.Column:
    primary_row = ft.Row(list(controls), spacing=SPACE_SM, wrap=True)
    if destructive is not None:
        return ft.Column(
            [
                primary_row,
                ft.Container(
                    padding=ft.Padding.only(top=SPACE_MD),
                    border=ft.Border(top=ft.BorderSide(1, COLOR_BORDER)),
                    content=destructive,
                ),
            ],
            spacing=0,
        )
    return ft.Column([primary_row], spacing=0)


def destructive_section(*controls: ft.Control) -> ft.Container:
    return ft.Container(
        padding=ft.Padding.only(top=SPACE_MD),
        border=ft.Border(top=ft.BorderSide(1, COLOR_BORDER)),
        content=ft.Column(list(controls), spacing=SPACE_SM),
    )
