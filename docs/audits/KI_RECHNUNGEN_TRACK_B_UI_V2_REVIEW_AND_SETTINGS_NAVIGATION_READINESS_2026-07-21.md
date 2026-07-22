# KI-Rechnungen Track B UI-v2 — Review and Settings Navigation Readiness

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_REVIEW_AND_SETTINGS_NAVIGATION_READINESS_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Review and Settings Navigation Readiness

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_REVIEW_AND_SETTINGS_NAVIGATION_READINESS_01`

## 2. Purpose

Wire Review („Zur Prüfung“) and Settings („Einstellungen“) into Track-B UI-v2 navigation and provide honest empty/readiness shells without enabling productive processing, PDF processing, folder scan/create, Track-A changes, or processing-core changes.

PO decision context: OPTION A — productive execution hold / continue UI readiness.

## 3. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/navigation.py` | Added `NAV_REVIEW` / `NAV_SETTINGS`; daily + admin nav complete |
| `invoice_tool/ui_v2/app.py` | Wired `build_review_page` / `build_settings_page` into `_render_page` |
| `invoice_tool/ui_v2/pages/review.py` | Honest review queue from `ProcessingRunState` only |
| `invoice_tool/ui_v2/pages/settings.py` | Generic readiness sections; no productive toggle |
| `tests/test_ui_v2_navigation_structure.py` | New non-GUI navigation structure tests |
| `tests/test_ui_v2_review_navigation.py` | New review nav/empty-state tests |
| `tests/test_ui_v2_settings_navigation.py` | New settings nav/readiness tests |
| `tests/test_ui_v2_flet085_foundation_gate.py` | Expected nav ids updated to 5 items |
| `tests/test_ui_v2_design_fidelity.py` | Nav assertion now expects Review + Settings |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_REVIEW_AND_SETTINGS_NAVIGATION_READINESS_2026-07-21.md` | This audit |

## 4. Review navigation behavior

- Sidebar daily nav now includes **Zur Prüfung** (`zur_pruefung`).
- Click navigates via existing UI-v2 shell `on_navigate` → `app._render_page` → `build_review_page`.
- No top-level „Scanprofile“.

## 5. Review page behavior

- Default: honest empty state:
  - „Noch keine Prüffälle vorhanden.“
  - „Unklare Dokumente erscheinen hier erst nach einem echten Verarbeitungslauf.“
- Items only when `state.processing_run_state.review_items` is non-empty (real injected run state).
- No fake unclear documents, no private names/paths, no folder scan, no PDF processing.

## 6. Settings navigation behavior

- Sidebar admin nav now includes **Einstellungen** (`einstellungen`).
- Click navigates via existing UI-v2 shell → `build_settings_page`.

## 7. Settings page behavior

- Generic readiness shell with disabled/readiness sections:
  - Allgemein
  - Verarbeitung
  - Sicherheit
  - Export
- Explicit notice: productive local execution is not released/enabled.
- No private defaults, no local private paths, no account/payment hardcoding.
- No productive execution toggle (`Switch`/`Checkbox`).
- No settings persistence in this step.
- No processing-core import.

## 8. Navigation structure

| Group | Items |
|---|---|
| ARBEITSNAVIGATION | Arbeitsbereich · Konfigurationen · Zur Prüfung |
| VERWALTUNG | Profile · Einstellungen |

IDs: `arbeitsbereich`, `konfigurationen`, `zur_pruefung`, `profile`, `einstellungen`.

## 9. Why this does not process real PDFs

Review/settings pages are presentation-only. They do not call `LocalProcessingAdapter.start_run`, do not import processing-core, and do not open or read PDF files. Review items remain empty unless a future real run injects `ProcessingRunState.review_items`.

## 10. Why this does not touch real invoice folders

No folder picker, scan, create, move, or copy logic was added on these pages. Workspace folder state remains the only UI folder surface and still writes UI state only.

## 11. Why this does not touch Track A

Only `invoice_tool/ui_v2/**`, Track-B tests, and this audit doc were changed. `app_main.py`, legacy `ui_*.py`, and Track-A shell were not modified.

## 12. Why this does not touch processing-core

No edits to `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, or `run.py`. Review/settings pages do not import those modules.

## 13. Tests added/updated

Added:

- `tests/test_ui_v2_navigation_structure.py`
- `tests/test_ui_v2_review_navigation.py`
- `tests/test_ui_v2_settings_navigation.py`

Updated:

- `tests/test_ui_v2_flet085_foundation_gate.py`
- `tests/test_ui_v2_design_fidelity.py`

## 14. Tests run and results

Required set + new navigation/review/settings/empty-state tests: **passed**.

Full Track-B suite:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py -q
208 passed, 44 skipped
```

## 15. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded defaults in changed UI-v2 pages
- No Desktop/`/Users` private path defaults
- No fake review items or fake processing results
- No productive execution toggle
- No folder scan/create
- No PDF processing
- Wording is generic Track-B product copy
- Track A untouched
- processing/routing/classification core untouched

## 16. Remaining gaps

- policy editor controls
- real run result display shell (workspace/results depth)
- native folder picker final behavior if still limited
- real dry-run bridge if Core gets safe dry mode
- productive execution PO gate

## 17. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_RUN_RESULT_DISPLAY_SHELL_READINESS_01`

Prepare a bounded, honest run-result display shell in UI-v2 (workspace/results) that can later bind to real `ProcessingRunState` results/review items — still without productive execution, PDF processing, or processing-core changes.
