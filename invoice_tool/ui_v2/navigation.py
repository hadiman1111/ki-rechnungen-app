"""Navigation definitions for UI-v2 — ids, labels, icons only.

Workflow order (primary):
  Arbeitsbereich → Profile → Konfigurationen → Prüfung

Developer / diagnosis (not a user settings page):
  Entwickler / Diagnose — secondary, hidden unless
  KI_RECHNUNGEN_UI_V2_SHOW_DEV_SURFACES=1 (not DEV_DEFAULTS alone).
"""

from __future__ import annotations

import flet as ft

NAV_WORKSPACE = "arbeitsbereich"
NAV_CONFIGURATIONS = "konfigurationen"
NAV_REVIEW = "zur_pruefung"
NAV_PROFILES = "profile"
NAV_SETTINGS = "einstellungen"

# Primary user workflow — Profile before Konfigurationen.
DAILY_NAV = (
    (NAV_WORKSPACE, "Arbeitsbereich", ft.Icons.DASHBOARD_OUTLINED),
    (NAV_PROFILES, "Profile", ft.Icons.ACCOUNT_CIRCLE_OUTLINED),
    (NAV_CONFIGURATIONS, "Konfigurationen", ft.Icons.TUNE),
    (NAV_REVIEW, "Prüfung", ft.Icons.FACT_CHECK_OUTLINED),
)

# Not a normal user settings page — developer/diagnose only (SHOW_DEV_SURFACES).
ADMIN_NAV = (
    (NAV_SETTINGS, "Entwickler / Diagnose", ft.Icons.BUG_REPORT_OUTLINED),
)

ALL_NAV_ITEMS = (*DAILY_NAV, *ADMIN_NAV)
ALL_NAV_IDS = tuple(nav_id for nav_id, _, _ in ALL_NAV_ITEMS)

# Group labels for sidebar (shell).
NAV_GROUP_WORKFLOW = "NUTZERFLUSS"
NAV_GROUP_ADVANCED = "ENTWICKLER"
