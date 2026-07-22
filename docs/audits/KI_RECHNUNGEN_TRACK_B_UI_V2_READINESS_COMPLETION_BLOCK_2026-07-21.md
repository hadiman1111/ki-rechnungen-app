# KI-Rechnungen Track B UI-v2 — Readiness Completion Block

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_READINESS_COMPLETION_BLOCK_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Readiness Completion Block

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_READINESS_COMPLETION_BLOCK_01`

## 2. Purpose

Complete the next practical Track-B UI-v2 readiness layer in one bundled safe block under OPTION A (productive execution hold / continue UI readiness):

1. Policy Editor Controls readiness  
2. Review detail shell readiness  
3. Settings detail shell readiness  
4. Workspace/result display refinement  
5. Navigation/UX consistency check  
6. Final readiness gap report for the next PO decision  

No productive processing, no PDF processing, no processing-core change, no Track-A change.

## 3. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/policy_editor_controls.py` | New generic Policy Editor Controls readiness shell |
| `invoice_tool/ui_v2/pages/settings.py` | Settings detail shell + Produktstatus + policy editor embed |
| `invoice_tool/ui_v2/pages/review.py` | Review detail shell with generic detail fields + honest copy |
| `invoice_tool/ui_v2/pages/workspace.py` | Workspace readiness display VM + honest folder/run/count strips |
| `invoice_tool/ui_v2/run_result_display.py` | Optional review detail fields on summary VM |
| `invoice_tool/ui_v2/processing_state.py` | Optional review detail fields on `ProcessingReviewItem` |
| `tests/test_ui_v2_policy_editor_controls.py` | New non-GUI policy-editor readiness tests |
| `tests/test_ui_v2_review_navigation.py` | Review detail shell assertions |
| `tests/test_ui_v2_settings_navigation.py` | Settings detail / Dry-Run / Produktstatus assertions |
| `tests/test_ui_v2_run_result_display_shell.py` | Workspace readiness display assertions |
| `tests/test_ui_v2_navigation_structure.py` | Exact Track-B nav label order |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_READINESS_COMPLETION_BLOCK_2026-07-21.md` | This audit |

## 4. Policy Editor Controls behavior

- New pure VM `build_policy_editor_controls_vm()` with disabled/readiness-only controls for:
  - filename never source of truth
  - unknown evidence → review/unclear
  - supplier IBAN alone is not payer evidence
  - generic card text without account reference → review/unclear
  - business/payment/account rules are profile-configurable
- Honest copy required and present:
  - „Regeln werden pro Profil konfiguriert.“
  - „Dateinamen sind keine Belegwahrheit.“
  - „Unklare Nachweise bleiben zur Prüfung.“
  - „Produktive Verarbeitung ist noch nicht freigegeben.“
- Embedded in Settings under the detail shell.
- No persistence, no private defaults, no productive execution toggle, no processing-core import, no FS access.

## 5. Review Detail Shell behavior

- Review page still shows only injected `ProcessingRunState.review_items`.
- Detail shell fields: document label/id, reason, suggested status, evidence summary, next action hint.
- Empty state remains honest when no items exist.
- Required honest copy:
  - „Prüffälle entstehen erst aus einem echten Verarbeitungslauf.“
  - „Diese Ansicht verändert keine Dateien.“
- `mutates_files=False`; no mark-as-done persistence; no PDF open; no folder scan.

## 6. Settings Detail Shell behavior

- Generic sections: Allgemein, Verarbeitung, Sicherheit, Export, Produktstatus.
- Visible safety state:
  - Dry-Run unavailable until Core boundary exists
  - productive execution not enabled
  - no private defaults
  - no automatic folder scan
- Required honest copy:
  - „Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar.“
  - „Produktive lokale Verarbeitung ist noch nicht freigegeben.“
  - „Diese Einstellungen sind produktneutral und enthalten keine privaten Standardwerte.“
- No productive execution toggle; no private path settings; no processing-core import.

## 7. Workspace/result refinement behavior

- New `WorkspaceReadinessDisplayVM` / `build_workspace_readiness_display_vm()` aggregates:
  - selected input/output folder state
  - current run status/message
  - dry-gate blocked state
  - result/review/error counts from real `ProcessingRunState` only
- Counts are never invented (`has_fake_counters=False`).
- Successful processing implied only when status is `completed`.
- Productive execution is never offered (`offers_productive_execution=False`).
- Workspace strips show folder/run/dry-gate/count readiness honestly.

## 8. Navigation/UX consistency

Track-B UI-v2 navigation remains exactly:

1. Arbeitsbereich  
2. Konfigurationen  
3. Zur Prüfung  
4. Profile  
5. Einstellungen  

No top-level Scanprofile, no Track-A nav change, no private labels, no fake demo data, no productive execution claims.

## 9. Why this does not process real PDFs

All additions are presentation/readiness VMs and page shells. No adapter start path was opened beyond the existing bounded/blocked contract. No PDF IO, no folder scan, no core import.

## 10. Why this does not touch real invoice folders

No folder create/scan/move/copy was added. Existing folder selection still stores UI state path strings only.

## 11. Why this does not touch Track A

Only `invoice_tool/ui_v2/**`, Track-B UI-v2 tests, and this audit doc were changed. `app_main.py` and legacy `ui_*.py` were not modified.

## 12. Why this does not touch processing-core

No edits to `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, or `run.py`.

## 13. Tests added/updated

Added:

- `tests/test_ui_v2_policy_editor_controls.py`

Updated:

- `tests/test_ui_v2_review_navigation.py`
- `tests/test_ui_v2_settings_navigation.py`
- `tests/test_ui_v2_run_result_display_shell.py`
- `tests/test_ui_v2_navigation_structure.py`

## 14. Tests run and results

Required suite + new readiness tests:

```text
121 passed
```

All Track-B UI-v2 / SaaS UI-v2 non-GUI tests:

```text
235 passed, 44 skipped
```

No GUI window tests. No PDF processing. No real invoice folders.

## 15. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded defaults  
- No Desktop / `/Users` / private path defaults  
- No filename-as-truth behavior  
- No fake payment/account/business classification results  
- No fake review items / fake processing results  
- No productive execution toggle  
- No folder scan/create / PDF processing  
- UI wording remains generic  
- Track A untouched  
- processing/routing/classification core untouched  

## 16. Current Track-B UI-v2 readiness score estimate

**78 / 100** (UI readiness high; execution still held).

| Area | Score |
|---|---|
| Navigation / empty honesty | 95 |
| Settings / Policy readiness shells | 85 |
| Review detail shell | 80 |
| Workspace folder/run/result display | 85 |
| Processing contract / adapter boundary | 80 |
| Real dry-run / productive execution | 20 (held by design) |

## 17. Remaining gaps

- native folder picker final behavior if still limited  
- real dry-run bridge if Core gets safe dry mode  
- productive execution PO gate  
- real processing adapter execution after PO approval  
- SaaS backend/auth/billing/multi-tenant not in local UI-v2 scope  

## 18. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_PO_GATE_CORE_DRY_BOUNDARY_OR_CONTINUE_HOLD_01`

PO decision between:

1. keep OPTION A (hold) and start a later SaaS/product packaging track, or  
2. open a **processing-core** dry/no-mutation boundary task (outside Track-B UI-v2) before any real adapter execution.
