# Audit — Track-B Export-/Reporting-Vorschau Polish

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_EXPORT_REPORTING_PREVIEW_POLISH_01`

## 2. Masterplan position: Prompt 5/34

Prompt 5 von 34 bis echter SaaS-Reife.

## 3. HEAD before/after

- **HEAD before:** `e8f65cb3e8505f58ec5b3eeca9ec1884f6ea11e3`
- **HEAD after:** `407df4942f1a71d821c924e3d837b03cb17a9fc1`

## 4. Diagnosis

1. **Bisheriges Export/Reporting:** Fünf-Fragen-Report aus `ProcessingRunState`, lokaler JSON/CSV-Export, Preview-Flags — aber ohne vollständige Sandbox-/Profil-Header, ohne klare Empty/Failed/All-Review-Parity und ohne einheitliche Prompt-5-Vorschau-Formulierungen.
2. **Bereits verfügbare Dry-Run-Felder:** `run_id`, status, recognized/review/error items, warnings, planned_destinations, safety_proof_summary, outcome_kind.
3. **Fehlende Report-Felder vor Polish:** Sandbox-Quell-/Zielpfad, Profil/Konfiguration, Warning-Count/Summary, Report-Titel „Export-Vorschau“, In-Memory-Preview-Text, explizite Non-Claims (Local-Pilot/SaaS).
4. **Risiko produktiver Schreibimplikation:** Export-Button und „Ergebnisbericht“ konnten als Produktivexport gelesen werden; Zielhinweise brauchten klarere „nur Vorschlag“-Sprache.
5. **Preview-only-Sprache vorher:** Clarity-Copy + „Export ist eine Vorschau…“, aber nicht die vollständige Prompt-5-Wortliste.
6. **Polish für Prompt 5/34:** Preview-Report-Modell, Workspace-/Review-Verdrahtung, ehrliche Outcome-Fälle, Write nur auf expliziten lokalen Pfad / In-Memory-Text.
7. **Verbleibt für Prompt 6/34:** Local-Pilot Acceptance Gate.
8. **Local Pilot pending:** Kein Acceptance-Gate, keine produktive Verarbeitung, keine Originalmutation, kein Pilot-Claim.

## 5. Files changed

- `invoice_tool/ui_v2/export_reporting.py`
- `invoice_tool/ui_v2/pages/workspace.py`
- `invoice_tool/ui_v2/pages/review.py`
- `tests/test_ui_v2_export_reporting_preview_polish.py`
- `docs/KI_RECHNUNGEN_TRACK_B_EXPORT_REPORTING_PREVIEW_POLISH_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_EXPORT_REPORTING_PREVIEW_POLISH_2026-07-22.md`

## 6. Preview report behavior

- `build_export_preview_report` / `build_run_report_view_model` aus echtem `ProcessingRunState`
- Optional `ExportPreviewContext` für Sandbox-Pfade und Profil/Konfiguration
- Counts, Safety-Proof, geplante Ziele (preview-only), Review-/Fehler-/Warnungs-Summaries
- Kein Lauf → „Noch kein Sandbox-Lauf vorhanden.“, kein Fake-Report
- Empty / all-review / mixed / failed ehrlich

## 7. Preview-only wording

Export-Vorschau; Keine Dateien wurden final geschrieben.; Originale unverändert.; Produktive Verarbeitung gesperrt.; Zielpfade sind Vorschläge aus dem Sandbox-Dry-Run.; Diese Vorschau ersetzt keinen finalen Produktivlauf.; Local-Pilot-/SaaS-Ready nicht erreicht.

## 8. Workspace behavior

Abschnitt „Export-Vorschau“ nutzt denselben Dry-Run-State; Kontext aus Workspace-Ordnern/Selektion; Speichern nur bei vorhandenem Lauf via `apply_workspace_export_preview`.

## 9. Review behavior

Kompakte `export_preview_summary`; `final_actions_blocked=True`; keine Final-/Produktiv-Aktion.

## 10. Export/write boundaries

- In-Memory-Text bevorzugt verfügbar
- Dateischreiben nur auf expliziten lokalen Pfad (JSON/CSV)
- Keine Schreibvorgänge in Original-/Rechnungsordner
- Kein PDF/Excel-Produktivexport

## 11. Mutation prevention proof

- Tests mit Original-Digest vor/nach Export unverändert
- Export schreibt nur unter `tmp_path`
- `mutates_original_files=False`, `starts_processing=False`
- Kein `run_once`-Aufruf

## 12. Track A preservation proof

- Keine Track-A-UI-Dateien geändert
- `tests/test_track_a_internal_app_protection.py` bestanden
- Processing-Core-Dateien unverändert

## 13. Tests run/results

Focused:

```text
tests/test_ui_v2_export_reporting_preview_polish.py
tests/test_ui_v2_real_run_result_mapping_and_review_flow.py
tests/test_ui_v2_core_bridge_real_sandbox_run_wiring.py
tests/test_ui_v2_workspace_processing_contract.py
tests/test_core_dry_run_no_mutation.py
tests/test_track_a_internal_app_protection.py
(+ legacy export_reporting)
```

Full UI-v2 / SaaS UI-v2: **556 passed, 44 skipped**  
`git diff --check`: clean (nach Staging geprüft)

## 14. No productive processing

Bestätigt — kein Produktivmodus, kein `run_once`, keine Core-Mutation.

## 15. No real invoice folders touched

Nur `tmp_path` / Sandbox-Testdaten in Tests.

## 16. No release tag changes

Tags unverändert (`product-v1-local-pilot-2026-07-22`, `internal-working-version-2026-07-21`).

## 17. Product status after task

`TRACK_B_EXPORT_REPORTING_PREVIEW_AVAILABLE_PENDING_ACCEPTANCE_GATE`

## 18. Remaining prompts: 29

## 19. Exact next task

`KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_ACCEPTANCE_GATE_01`
