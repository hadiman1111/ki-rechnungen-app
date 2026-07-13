"""Navigation definitions for UI-v2 — ids, labels, icons only."""

from __future__ import annotations

import flet as ft

NAV_WORKSPACE = "arbeitsbereich"
NAV_CONFIGURATIONS = "konfigurationen"
NAV_PROFILES = "profile"

DAILY_NAV = (
    (NAV_WORKSPACE, "Arbeitsbereich", ft.Icons.DASHBOARD_OUTLINED),
    (NAV_CONFIGURATIONS, "Konfigurationen", ft.Icons.TUNE),
)

ADMIN_NAV = (
    (NAV_PROFILES, "Profile", ft.Icons.ACCOUNT_CIRCLE_OUTLINED),
)

ALL_NAV_ITEMS = (*DAILY_NAV, *ADMIN_NAV)
ALL_NAV_IDS = tuple(nav_id for nav_id, _, _ in ALL_NAV_ITEMS)
