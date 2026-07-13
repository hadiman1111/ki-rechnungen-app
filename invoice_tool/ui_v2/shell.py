"""Persistent UI-v2 shell with sidebar and content host."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import flet as ft

from invoice_tool.ui_v2.navigation import ADMIN_NAV, DAILY_NAV
from invoice_tool.ui_v2.theme import (
    COLOR_CANVAS,
    COLOR_PRIMARY,
    PRODUCT_DISPLAY_NAME,
    COLOR_SIDEBAR_ACCENT_BG,
    COLOR_SIDEBAR_BG,
    COLOR_SIDEBAR_BORDER,
    COLOR_SIDEBAR_GROUP,
    COLOR_SIDEBAR_HOVER_BG,
    COLOR_SIDEBAR_TEXT,
    COLOR_SIDEBAR_TEXT_ACTIVE,
    COLOR_SIDEBAR_TEXT_HOVER,
    NAV_WIDTH,
)


def _apply_nav_style(container: ft.Container, *, active: bool) -> None:
    container.border_radius = 6
    container.border = ft.Border(
        left=ft.BorderSide(3, COLOR_PRIMARY if active else ft.Colors.TRANSPARENT),
    )
    container.bgcolor = COLOR_SIDEBAR_ACCENT_BG if active else None
    container.padding = ft.Padding.only(left=5 if active else 8, top=6, bottom=6, right=8)
    tile = container.content
    if not isinstance(tile, ft.ListTile):
        return
    if isinstance(tile.leading, ft.Icon):
        tile.leading.color = COLOR_SIDEBAR_TEXT_ACTIVE if active else COLOR_SIDEBAR_TEXT
    if isinstance(tile.title, ft.Text):
        tile.title.color = COLOR_SIDEBAR_TEXT_ACTIVE if active else COLOR_SIDEBAR_TEXT
        tile.title.weight = ft.FontWeight.W_600 if active else ft.FontWeight.W_400


def _wire_nav_hover(container: ft.Container, *, active: bool) -> None:
    def _on_hover(event: ft.HoverEvent) -> None:
        if active:
            return
        container.bgcolor = COLOR_SIDEBAR_HOVER_BG if event.data == "true" else None
        tile = container.content
        if isinstance(tile, ft.ListTile) and isinstance(tile.title, ft.Text):
            tile.title.color = COLOR_SIDEBAR_TEXT_HOVER if event.data == "true" else COLOR_SIDEBAR_TEXT
        try:
            container.update()
        except (AssertionError, RuntimeError, AttributeError):
            pass

    container.on_hover = _on_hover


@dataclass
class ShellHandles:
    root: ft.Container
    sidebar: ft.Container
    content_host: ft.Container
    nav_items: dict[str, ft.Container] = field(default_factory=dict)


def build_content_host(content: ft.Control) -> ft.Container:
    return ft.Container(
        key="ui-v2-content-host",
        expand=True,
        bgcolor=COLOR_CANVAS,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=content,
    )


def _nav_group_label(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=10,
        weight=ft.FontWeight.W_600,
        color=COLOR_SIDEBAR_TEXT_ACTIVE,
    )


def _nav_group(
    items: tuple[tuple[str, str, str], ...],
    *,
    active_nav: str,
    on_navigate: Callable[[str], None],
) -> tuple[ft.Column, dict[str, ft.Container]]:
    nav_controls: list[ft.Control] = []
    nav_items: dict[str, ft.Container] = {}
    for nav_id, label, icon_name in items:
        item = ft.Container(
            key=f"nav-{nav_id}",
            border_radius=6,
            margin=ft.Margin.only(bottom=1),
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            border=ft.Border(left=ft.BorderSide(3, ft.Colors.TRANSPARENT)),
            content=ft.ListTile(
                leading=ft.Icon(icon_name, size=14),
                title=ft.Text(label, size=13),
                dense=True,
                on_click=lambda _e, nid=nav_id: on_navigate(nid),
            ),
        )
        _apply_nav_style(item, active=(nav_id == active_nav))
        _wire_nav_hover(item, active=(nav_id == active_nav))
        nav_items[nav_id] = item
        nav_controls.append(item)
    return ft.Column(nav_controls, spacing=0), nav_items


def _build_sidebar(
    *,
    active_nav: str,
    on_navigate: Callable[[str], None],
) -> tuple[ft.Container, dict[str, ft.Container]]:
    daily_group, daily_items = _nav_group(DAILY_NAV, active_nav=active_nav, on_navigate=on_navigate)
    admin_group, admin_items = _nav_group(ADMIN_NAV, active_nav=active_nav, on_navigate=on_navigate)
    nav_items = {**daily_items, **admin_items}

    sidebar = ft.Container(
        key="ui-v2-sidebar",
        width=NAV_WIDTH,
        bgcolor=COLOR_SIDEBAR_BG,
        border=ft.Border(right=ft.BorderSide(1, COLOR_SIDEBAR_BORDER)),
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.Padding.all(16),
                    border=ft.Border(bottom=ft.BorderSide(1, COLOR_SIDEBAR_BORDER)),
                    content=ft.Text(
                        PRODUCT_DISPLAY_NAME,
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color=COLOR_SIDEBAR_TEXT_ACTIVE,
                    ),
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.only(left=8, right=8, top=14, bottom=14),
                    content=ft.Column(
                        [
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=8),
                                content=_nav_group_label("ARBEITSNAVIGATION"),
                            ),
                            ft.Container(height=3),
                            daily_group,
                            ft.Container(height=24),
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=8),
                                content=_nav_group_label("VERWALTUNG"),
                            ),
                            ft.Container(height=3),
                            admin_group,
                        ],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ),
            ],
            expand=True,
        ),
    )
    return sidebar, nav_items


def build_shell(
    *,
    active_nav: str,
    content: ft.Control,
    on_navigate: Callable[[str], None],
) -> ShellHandles:
    sidebar, nav_items = _build_sidebar(
        active_nav=active_nav,
        on_navigate=on_navigate,
    )
    content_host = build_content_host(content)

    layout = ft.Stack(
        [
            ft.Container(
                left=NAV_WIDTH,
                top=0,
                right=0,
                bottom=0,
                content=content_host,
            ),
            ft.Container(
                left=0,
                top=0,
                bottom=0,
                width=NAV_WIDTH,
                content=sidebar,
            ),
        ],
        expand=True,
    )

    root = ft.Container(
        key="ui-v2-shell",
        expand=True,
        bgcolor=COLOR_CANVAS,
        content=layout,
    )
    return ShellHandles(root=root, sidebar=sidebar, content_host=content_host, nav_items=nav_items)


def set_active_nav(handles: ShellHandles, nav_id: str) -> None:
    for item_id, container in handles.nav_items.items():
        _apply_nav_style(container, active=(item_id == nav_id))
        try:
            container.update()
        except (AssertionError, RuntimeError, AttributeError):
            pass


def replace_content(handles: ShellHandles, content: ft.Control) -> None:
    handles.content_host.content = content
    try:
        handles.content_host.update()
    except (AssertionError, RuntimeError, AttributeError):
        pass


def update_active_profile(handles: ShellHandles, profile_name: str | None) -> None:
    """No-op — active profile is shown on Profile/Arbeitsbereich pages, not in the sidebar."""
    del handles, profile_name
