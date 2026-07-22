# KI-Rechnungen Track B UI-v2 — Run Result Display Shell Readiness

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_RUN_RESULT_DISPLAY_SHELL_READINESS_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Run Result Display Shell Readiness

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_RUN_RESULT_DISPLAY_SHELL_READINESS_01`

## 2. Purpose

Prepare an honest Track-B UI-v2 run result display shell so the workspace (and review) can show future `ProcessingRunState` / `ProcessingResultSummary` data without inventing results and without enabling productive PDF processing.

PO decision context: OPTION A — productive execution hold / continue UI readiness.

## 3. Files changed

| Path | Change |
|---|---|
| `invoice_tool/ui_v2/run_result_display.py` | New pure run/result/review/error display shell view models |
| `invoice_tool/ui_v2/pages/workspace.py` | Wire run-status summary, contract results, review/error separation, blocked copy |
| `invoice_tool/ui_v2/pages/review.py` | Keep review queue from `review_items`; expose error/result counts separately |
| `tests/test_ui_v2_run_result_display_shell.py` | New non-GUI display-shell tests |
| `tests/test_ui_v2_review_navigation.py` | Assert errors stay out of review queue |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_RUN_RESULT_DISPLAY_SHELL_READINESS_2026-07-21.md` | This audit |

## 4. Run result shell behavior

- Pure helper `build_run_result_display_shell(ProcessingRunState)` maps status to labels:
  - idle · not_configured · ready · running · completed · failed · blocked
- Workspace shows a **Laufstatus** strip from real `state.processing_run_state`.
- Blocked execution hints include:
  - „Produktive Verarbeitung ist noch nicht freigegeben.“
  - „Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar.“
- No auto-run, no folder scan, no PDF processing.

## 5. Result summary behavior

- Results are rendered only from provided `ProcessingResultSummary` items.
- Generic fields only: document_name, document_type, classification_status, status_label, confidence_label, target_hint.
- No invented payment/account/business classification.
- No filename-as-truth inference.
- Empty results remain empty — no fake rows.

## 6. Review item summary behavior

- Workspace shows review count/summary separately when `review_items` exist.
- Detail routing hint: „Details unter Zur Prüfung.“
- Review page continues to list only `review_items`.
- Review VM exposes `error_count` / `result_count` but does not mix them into the queue.

## 7. Error summary behavior

- Workspace shows error count separately from review items.
- Errors come only from `ProcessingRunState.errors`.
- No fake errors.

## 8. Workspace behavior

- Honest empty state remains when no run/results/review/errors exist.
- Contract results take precedence over snapshot results when present.
- Snapshot results still display if provided and contract results are empty.
- Start CTA still goes through bounded processing service only (no core import).

## 9. Review page behavior if changed

- Empty state unchanged: „Noch keine Prüffälle vorhanden.“
- Injected `review_items` still render with generic fields only.
- No file-mutating actions; no mark-as-done persistence.
- Errors/results remain separated via counts, not mixed into the list.

## 10. Why this does not process real PDFs

Display shell and page wiring are presentation-only. They do not call productive adapters that mutate files, do not open PDFs, and do not import processing-core. Results stay empty unless a future real run injects state.

## 11. Why this does not touch real invoice folders

No folder scan/create/move/copy was added. Existing folder selection still writes UI state strings only.

## 12. Why this does not touch Track A

Only `invoice_tool/ui_v2/**`, Track-B tests, and this audit doc were changed. `app_main.py` and legacy `ui_*.py` were not modified.

## 13. Why this does not touch processing-core

No edits to `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, or `run.py`. Display helpers import only UI-v2 processing state/contract types.

## 14. Tests added/updated

Added:

- `tests/test_ui_v2_run_result_display_shell.py`

Updated:

- `tests/test_ui_v2_review_navigation.py`

## 15. Tests run and results

Required set + new run-result display tests: **passed**.

Full Track-B suite:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py -q
221 passed, 44 skipped
```

## 16. Generalization confirmation

- No Hadi/SOMAA/Bismarck/AMEX/voba hardcoded defaults
- No Desktop/`/Users` private path defaults
- No filename-as-truth behavior
- No fake payment/account/business classification results
- No fake review items / fake processing results
- No productive execution toggle
- No folder scan/create
- No PDF processing
- UI wording is generic
- Track A untouched
- processing/routing/classification core untouched

## 17. Remaining gaps

- policy editor controls
- native folder picker final behavior if still limited
- real dry-run bridge if Core gets safe dry mode
- productive execution PO gate
- real processing adapter execution after PO approval

## 18. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_POLICY_EDITOR_CONTROLS_READINESS_01`  
— or, if PO prefers execution path later: wait for Core dry/no-mutation gate before any real adapter execution bridge.
