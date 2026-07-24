# Audit: Track-B Review Accordion Layout (2026-07-24)

## Scope

UI-v2 presentation only — accordion list/detail for Simple User Review.

Allowed touchpoints:

- `invoice_tool/ui_v2/pages/review.py`
- `invoice_tool/ui_v2/track_b_smoke_debug_copy.py`
- accordion / polish / declutter / user-mode tests
- docs under `docs/` and `docs/audits/`

## Previous list/detail problem

Zu viele Felder in der Liste; Detailpanel nach der gesamten Liste statt
direkt unter dem gewählten Dokument.

## New compact card behavior

Eingeklappte Karten: Name/Lieferant, Datum, Betrag, Details öffnen/schließen.

## Accordion behavior

Single-open über `open_review_item_id`; vorheriges Detail schließt beim Öffnen
eines anderen Dokuments.

## Inline detail behavior

`render_review_inline_detail` hängt den Detailblock unmittelbar unter die
gewählte Karte; Simple-User-Review-Abschnitte bleiben erhalten.

## Active highlight result

Aktive Karte: Hintergrund, Border, Akzentstreifen, Marker
`review_card_active_highlight`.

## Distinct detail background result

Detailpanel: `COLOR_SURFACE_ALT`, starker Border, Padding; Marker
`detail_panel_distinct_background` / `inline_detail_under_selected_card`.

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

- `tests/test_track_b_review_accordion_layout.py`
- `tests/test_track_b_simple_user_review_ui_polish.py`
- `tests/test_track_b_simple_user_review_mode.py`
- `tests/test_track_b_review_surface_declutter.py`
- `tests/test_track_b_automated_smoke_oracle.py`
- `tests/test_track_b_filename_pattern_simplification.py`
- `tests/test_track_a_internal_app_protection.py`
- `tests/test_ui_v2_*.py` / `tests/test_saas_ui_v2_*.py`

## Oracle rerun

Automated smoke oracle remains the fachliche regression gate and is re-run
after the accordion layout change.

## No productive processing / no real invoice folders

Confirmed by VM flags, source AST guards, and forbidden-folder string checks.

## No Track A / Core changes

Protected Track-A UI and processing-core files were not modified in this task.

## Release tags unchanged

No release-tag mutations in this work block.

## Next step

PO visual check of accordion UX in Live-GUI; then next Track-B product step.
