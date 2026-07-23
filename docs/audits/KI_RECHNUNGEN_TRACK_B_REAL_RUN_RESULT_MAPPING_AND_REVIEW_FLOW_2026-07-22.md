# Audit: Track-B Real Run Result Mapping and Review Flow

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_01`

## 2. Masterplan position: Prompt 4/34

## 3. HEAD before/after

- Before: `163e6ec163c075d9b5acaf4f4a15a55ebac78ffc`
- After: `9baffeb73077e6752604963fd1533b4e689660d0`

## 4. Diagnosis

1. **Bisher gemappt:** Status, run_id, recognized→results, review→review_items, errors→Strings, planned paths/count, warnings, safety_proof_summary.
2. **Fehlend für Review-Flow:** strukturierte Error-Items, strukturierte Planned Destinations im State, outcome_kind (empty/all_review/mixed), zentrale Mapping-Schicht, Review-State mit getrennten Fehler-/Zielvorschau-Bereichen.
3. **Wiederverwendbar:** `ProcessingRunState`, `ProcessingResultSummary`, `ProcessingReviewItem`, Bridge-/Boundary-Transport, `review_workflow`, Export-Preview-VMs.
4. **Neue Helper-Datei nötig:** ja — `invoice_tool/ui_v2/result_mapping.py`.
5. **Review page/state:** Review-Page + `review_workflow` existierten; `review_state.py` / `review_components.py` neu für Dry-Run-Flow.
6. **Buckets:** erkannt/geplant, Prüfung, Fehler, Warnungen, Safety-Proof.
7. **Planned destinations:** `preview_only=True`, `applied=False`, Anzeige als Vorschau.
8. **Safety proof:** Kompaktzeile „Originale unverändert · Produktiv gesperrt · Export Vorschau“.
9. **Prompt 5/34:** Export-/Reporting-Vorschau-Polish / Parity.
10. **Local pilot pending:** kein Acceptance-Gate (Prompt 6/34), kein Produktivmodus, keine Originalordner.

## 5. Files changed

- `invoice_tool/ui_v2/result_mapping.py` (neu)
- `invoice_tool/ui_v2/review_state.py` (neu)
- `invoice_tool/ui_v2/review_components.py` (neu)
- `invoice_tool/ui_v2/processing_state.py`
- `invoice_tool/ui_v2/core_bridge.py`
- `invoice_tool/ui_v2/sandbox_execution_boundary.py`
- `invoice_tool/ui_v2/local_processing_adapter.py`
- `invoice_tool/ui_v2/run_result_display.py`
- `invoice_tool/ui_v2/export_reporting.py`
- `invoice_tool/ui_v2/pages/workspace.py`
- `invoice_tool/ui_v2/pages/review.py`
- `tests/test_ui_v2_real_run_result_mapping_and_review_flow.py` (neu)
- `docs/KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_2026-07-22.md`

Nicht geändert: Track-A-UI, processing-core (`run.py`/`processing.py`/`core_dry_run.py`/…), scripts, resources, Release-Tags.

## 6. Result mapping behavior

`CoreDryRunResult` → `result_mapping` → `ProcessingRunState` (+ Bridge/Boundary-Transport). Keine erfundenen Rows; leere/fehlgeschlagene/gemischte Outcomes ehrlich.

## 7. Bucket model

Erkannt/geplant · Zur Prüfung · Fehler · Warnungen · Sicherheitsnachweis (+ geplante Ziele als Preview).

## 8. Review flow behavior

Review nur aus `review_items`; Fehler getrennt; erkannte nicht in Review; geplante Ziele preview-only; Aktionen disabled; keine produktiven Finalaktionen.

## 9. Workspace behavior

Counts, Outcome-Hinweise (leer / mit Prüffällen), Safety-Proof, gleiche State-Quelle wie Review; kein Fake-Erfolg.

## 10. Export/reporting behavior

Preview-only; kann strukturierte planned destinations lesen; kein DATEV-/Cloud-Produktivexport. Rest → Prompt 5/34.

## 11. Mutation prevention proof

tmp_path: Original-Digests unverändert; kein `run_once`; planned paths nicht angewendet; Core-Dry-Run-No-Mutation-Tests grün.

## 12. Track A preservation proof

Geschützte Track-A-UI-Dateien nicht geändert; `test_track_a_internal_app_protection` grün; bekannte Legacy-Dirty-Dateien bleiben unstaged.

## 13. Tests run/results

- Focused (inkl. neuer Mapping-Suite + Bridge/Core/Workspace/Track-A): grün  
- Full UI-v2 / SaaS UI-v2: **533 passed, 44 skipped**  
- `git diff --check`: clean

## 14. No productive processing

yes

## 15. No real invoice folders touched

yes (nur pytest `tmp_path`)

## 16. No release tag changes

yes (`product-v1-local-pilot-2026-07-22` unverändert)

## 17. Product status after task

`TRACK_B_REAL_RUN_RESULT_MAPPING_AVAILABLE_PENDING_EXPORT_AND_ACCEPTANCE`

## 18. Remaining prompts: 30

## 19. Exact next task

`KI_RECHNUNGEN_TRACK_B_EXPORT_REPORTING_PREVIEW_POLISH_01`
