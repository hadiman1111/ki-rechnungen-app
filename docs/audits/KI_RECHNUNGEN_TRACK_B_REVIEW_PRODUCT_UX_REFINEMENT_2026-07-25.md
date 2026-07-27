# Track-B Review Product UX Refinement — 2026-07-25

## Scope

UI-v2 only: navigation labels, review detail structure, dual scroll targets,
dev-only Entwickler/Test surfaces. No OCR/matching/final-write/core changes.

## Product decisions implemented

1. Main nav + page title: **Prüfung** (was „Zur Prüfung“).
2. Workspace action: **Prüfung öffnen**.
3. Filename labels: **Geplanter Dateiname**; section title **Dateiname**.
4. File click scrolls to **file-card anchor**; „Dateiname bearbeiten“ scrolls to
   **filename-section anchor** (separate targets).
5. „Was muss ich entscheiden?“ = open/uncertain points only.
6. „Erkannte Angaben“ = safe core values (Datum, Lieferant, Betrag, Belegart,
   Zahlungsart when confident).
7. „Test & Nachweis“ hidden from normal review (dev-defaults only).
8. „Entwickler / Diagnose“ hidden from normal main menu (dev-defaults only).

## Safety

- No productive processing, no `run_once`, no real invoice folders.
- Track A and processing core untouched.
- Release tags unchanged.
