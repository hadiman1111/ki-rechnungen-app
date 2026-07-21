"""Application shell with left navigation and content area."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import flet as ft

from invoice_tool.ui_theme import (
    COLOR_BORDER,
    COLOR_CANVAS,
    COLOR_NAV_ACTIVE_BG,
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_SIZE_BODY,
    NAV_WIDTH,
    RADIUS_MD,
    SPACE_MD,
    SPACE_SM,
)

NAV_WORKSPACE = "arbeitsbereich"
NAV_CONFIGURATIONS = "konfigurationen"
NAV_REVIEW = "zur_pruefung"
NAV_PROFILES = "profile"
NAV_SETTINGS = "einstellungen"

DAILY_NAV = (
    (NAV_WORKSPACE, "Arbeitsbereich", ft.Icons.HOME_OUTLINED),
    (NAV_CONFIGURATIONS, "Konfigurationen", ft.Icons.TUNE),
    (NAV_REVIEW, "Zur Prüfung", ft.Icons.FACT_CHECK_OUTLINED),
)

ADMIN_NAV = (
    (NAV_PROFILES, "Profile", ft.Icons.ACCOUNT_TREE_OUTLINED),
    (NAV_SETTINGS, "Einstellungen", ft.Icons.SETTINGS_OUTLINED),
)

ALL_NAV_IDS = tuple(nav_id for nav_id, _, _ in (*DAILY_NAV, *ADMIN_NAV))


def _apply_nav_active_style(container: ft.Container, *, active: bool) -> None:
    container.bgcolor = COLOR_NAV_ACTIVE_BG if active else None
    container.border = ft.Border(
        left=ft.BorderSide(3, COLOR_PRIMARY if active else ft.Colors.TRANSPARENT),
    )
    row = container.content
    if not isinstance(row, ft.Row) or not row.controls:
        return
    icon = row.controls[0]
    label = row.controls[1]
    if isinstance(icon, ft.Icon):
        icon.color = COLOR_PRIMARY if active else COLOR_TEXT_MUTED
    if isinstance(label, ft.Text):
        label.color = COLOR_PRIMARY if active else COLOR_TEXT_SECONDARY
        label.weight = ft.FontWeight.W_600 if active else ft.FontWeight.W_500


@dataclass
class ShellState:
    """Persistent shell with a stable content host and updatable navigation."""

    root: ft.Container
    content_host: ft.Container
    nav_items: dict[str, ft.Container] = field(default_factory=dict)
    profile_summary_text: ft.Text | None = None
    review_badge_host: dict[str, ft.Container] = field(default_factory=dict)

    def update_active_nav(self, nav_id: str) -> None:
        for item_id, container in self.nav_items.items():
            _apply_nav_active_style(container, active=(item_id == nav_id))

    def set_profile_summary(self, summary: str | None) -> None:
        if self.profile_summary_text is not None:
            self.profile_summary_text.value = summary or "Profil"

    def set_review_badge(self, badge: str | None) -> None:
        badge_container = self.review_badge_host.get(NAV_REVIEW)
        if badge_container is None:
            return
        badge_container.visible = bool(badge)
        content = badge_container.content
        if isinstance(content, ft.Text) and badge:
            content.value = badge


def build_content_host(content: ft.Control) -> ft.Container:
    """Stable expand host for the active page module."""
    return ft.Container(expand=True, content=content)


def build_app_shell(
    *,
    active_nav: str,
    content: ft.Control,
    on_navigate: Callable[[str], None],
    profile_summary: str | None = None,
    review_badge: str | None = None,
) -> ft.Container:
    return build_app_shell_state(
        active_nav=active_nav,
        content=content,
        on_navigate=on_navigate,
        profile_summary=profile_summary,
        review_badge=review_badge,
    ).root


def build_app_shell_state(
    *,
    active_nav: str,
    content: ft.Control,
    on_navigate: Callable[[str], None],
    profile_summary: str | None = None,
    review_badge: str | None = None,
) -> ShellState:
    nav_items: dict[str, ft.Container] = {}
    review_badge_host: dict[str, ft.Container] = {}

    def _nav_item(nav_id: str, label: str, icon: str) -> ft.Container:
        badge_container: ft.Container | None = None
        trailing: list[ft.Control] = []
        if nav_id == NAV_REVIEW:
            badge_container = ft.Container(
                visible=bool(review_badge),
                content=ft.Text(
                    review_badge or "",
                    size=10,
                    color=COLOR_TEXT_MUTED,
                    weight=ft.FontWeight.W_700,
                ),
                bgcolor=COLOR_SURFACE_ALT,
                border_radius=RADIUS_MD,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            )
            review_badge_host[NAV_REVIEW] = badge_container
            trailing.append(badge_container)

        item = ft.Container(
            on_click=lambda _e, target=nav_id: on_navigate(target),
            border_radius=ft.BorderRadius.only(top_right=RADIUS_MD, bottom_right=RADIUS_MD),
            padding=ft.Padding.only(left=10, right=SPACE_MD, top=SPACE_SM, bottom=SPACE_SM),
            ink=True,
            content=ft.Row(
                [
                    ft.Icon(icon, size=18),
                    ft.Text(label, size=FONT_SIZE_BODY, expand=True),
                    *trailing,
                ],
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        _apply_nav_active_style(item, active=(active_nav == nav_id))
        nav_items[nav_id] = item
        return item

    daily_items = [_nav_item(nav_id, label, icon) for nav_id, label, icon in DAILY_NAV]
    admin_items = [_nav_item(nav_id, label, icon) for nav_id, label, icon in ADMIN_NAV]

    profile_summary_text = ft.Text(
        profile_summary or "Profil",
        size=12,
        weight=ft.FontWeight.W_600,
        color=COLOR_TEXT_PRIMARY,
    )
    footer: list[ft.Control] = [
        ft.Container(
            padding=SPACE_SM,
            bgcolor=COLOR_SURFACE_ALT,
            border_radius=8,
            content=ft.Column(
                [
                    ft.Text("Aktives Profil", size=10, color=COLOR_TEXT_MUTED),
                    profile_summary_text,
                ],
                spacing=2,
            ),
        )
    ]

    sidebar = ft.Container(
        width=NAV_WIDTH,
        bgcolor=COLOR_SURFACE,
        border=ft.Border(right=ft.BorderSide(1, COLOR_BORDER)),
        padding=ft.Padding.only(top=SPACE_MD, bottom=SPACE_MD),
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SPACE_MD),
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=COLOR_TEXT_PRIMARY),
                            ft.Text("KI-Rechnungen", size=15, weight=ft.FontWeight.W_700),
                        ],
                        spacing=SPACE_SM,
                    ),
                ),
                ft.Container(height=SPACE_MD),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SPACE_SM),
                    content=ft.Column(daily_items, spacing=2),
                ),
                ft.Divider(height=1, color=COLOR_BORDER),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SPACE_SM),
                    content=ft.Column(admin_items, spacing=2),
                ),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=SPACE_MD),
                    content=ft.Column(footer, spacing=SPACE_SM),
                ),
            ],
            spacing=SPACE_SM,
            expand=True,
        ),
    )

    content_host = build_content_host(content)
    root = ft.Container(
        expand=True,
        bgcolor=COLOR_CANVAS,
        content=ft.Row(
            [sidebar, content_host],
            spacing=0,
            expand=True,
        ),
    )
    return ShellState(
        root=root,
        content_host=content_host,
        nav_items=nav_items,
        profile_summary_text=profile_summary_text,
        review_badge_host=review_badge_host,
    )
