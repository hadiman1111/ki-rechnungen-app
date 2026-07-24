# Audit: Track-B Guided Review UX Cleanup (2026-07-24)

## Scope

UI/UX + document-specific user-facing reasons only.

Allowed touchpoints:

- `invoice_tool/ui_v2/pages/review.py`
- `invoice_tool/ui_v2/track_b_smoke_debug_copy.py`
- guided / accordion / polish / declutter / user-mode tests
- docs under `docs/` and `docs/audits/`

## Screenshot-based issues

Technische Überladung, zu prominente Testwerkzeuge, schwache Entscheidung,
sofortiges Dateiname-Editierfeld, PayPal-Bleed in Böttcher-Kartenfall.

## Document-specific reason fix

`review_case_kind` gated by this document's payment/art; PayPal CTA/reasons
require `payment == paypal`.

## Böttcher no-PayPal result

Card case reasons/guided lines contain AMEX/card text only — never PayPal.

## Guided status panel

Top panel with plain-German status/reason/recommendation.

## Decision-first layout

Decision section immediately after guided status; primary_button for primary action.

## Filename preview behavior

Preview-only by default; TextField only when edit mode is active.

## Test/tools collapse behavior

`_test_tools_collapsed` ExpansionTile (`Test & Nachweis`) holds dry-run,
sandbox, finalization detail, copy/advanced tools; collapsed by default.

## Safety result

| Gate | Result |
|---|---|
| No productive processing | pass |
| No real invoice folders | pass |
| No run_once / auto-oracle | pass |
| No production final-write | pass |
| Track A protected files untouched | pass |
| Processing-core untouched | pass |
| Release tags unchanged | pass |

## Tests

- `tests/test_track_b_guided_review_ux_cleanup.py`
- accordion / polish / user-mode / declutter / oracle / filename / Track-A
- `tests/test_ui_v2_*.py` / `tests/test_saas_ui_v2_*.py`

## Oracle rerun

Automated smoke oracle re-run after cleanup.

## No productive processing / no real invoice folders

Confirmed by VM flags and forbidden-folder string checks.

## No Track A / Core changes

Protected files not modified in this task.

## Release tags unchanged

No release-tag mutations.

## Next step

PO visual check in Live-GUI; then next Track-B product step.
