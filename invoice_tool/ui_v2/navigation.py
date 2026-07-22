"""Navigation definitions for UI-v2 — ids, labels, icons only."""

from __future__ import annotations

import flet as ft

NAV_WORKSPACE = "arbeitsbereich"
NAV_CONFIGURATIONS = "konfigurationen"
NAV_REVIEW = "zur_pruefung"
NAV_PROFILES = "profile"
NAV_SETTINGS = "einstellungen"

DAILY_NAV = (
    (NAV_WORKSPACE, "Arbeitsbereich", ft.Icons.DASHBOARD_OUTLINED),
    (NAV_CONFIGURATIONS, "Konfigurationen", ft.Icons.TUNE),
    (NAV_REVIEW, "Zur Prüfung", ft.Icons.FACT_CHECK_OUTLINED),
)

ADMIN_NAV = (
    (NAV_PROFILES, "Profile", ft.Icons.ACCOUNT_CIRCLE_OUTLINED),
    (NAV_SETTINGS, "Einstellungen", ft.Icons.SETTINGS_OUTLINED),
)

ALL_NAV_ITEMS = (*DAILY_NAV, *ADMIN_NAV)
ALL_NAV_IDS = tuple(nav_id for nav_id, _, _ in ALL_NAV_ITEMS)
