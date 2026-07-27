# Track-B Product UI Mode Cleanup — 2026-07-27

Task: `KI_RECHNUNGEN_TRACK_B_PRODUCT_UI_MODE_CLEANUP_01`

## Goal

Normale Produktoberfläche ohne Entwicklerdiagnose; Profil-/Konfigurationstitel
klickbar; einheitliche Aufklapp-Chevrons; konkrete Prüfungsaktionen; volle
Detailkartenbreite; Dateiname-Scroll/Fokus.

## Changes

### A. Dev defaults vs dev surfaces

- `KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1` setzt nur kontrollierte Testordner/Profile.
- Entwicklerflächen brauchen separat `KI_RECHNUNGEN_UI_V2_SHOW_DEV_SURFACES=1`.
- Helper: `invoice_tool.ui_v2.state.is_track_b_show_dev_surfaces_enabled`.
- Shell-Nav, Arbeitsbereich-Advanced und Prüfungs-Testtools nutzen nur SHOW_DEV_SURFACES.

### B. Hauptmenü

Normal sichtbar: Arbeitsbereich · Profile · Konfigurationen · Prüfung  
Entwickler / Diagnose nur bei SHOW_DEV_SURFACES (kollabiert, sekundär).

### C. Arbeitsbereich

- Profilname und Konfigurationsname sind klickbar (Hover, Stift-Icon, Tooltip).
- Separate „Bearbeiten“-Buttons entfallen.

### D. Aufklapp-Logik

- `make_expansion_tile` setzt shared Chevron: geschlossen rechts, geöffnet unten.
- Marker: `ui_v2_collapsible_chevron_right_down_v1`.

### E. Prüfung

- Detailkarten: volle verfügbare Breite (`review_detail_card_full_width_v1`).
- Aktionen: „Vorschlag übernehmen“, „Dateiname anpassen“, „Weiter manuell prüfen“,
  „Nicht exportieren“.
- Kein „Zur Prüfung zulassen/lassen“ als Nutzerwahl.
- Dateiname-bearbeiten scrollt zur Dateiname-Sektion und markiert sie aktiv.

## Safety

- Kein Track-A / Processing-Core geändert.
- Kein run_once / productive final write.
- Keine realen Rechnungsordner.
- Release-Tags unverändert.

## Classification

`TRACK_B_PRODUCT_UI_MODE_CLEANUP_READY_COMMITTED_AND_PUSHED` (nach Commit/Push)
