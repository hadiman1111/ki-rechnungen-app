# Track-B Quality Fixes after Sandbox Validation

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_QUALITY_FIXES_AFTER_SANDBOX_VALIDATION_01`

## 2. Masterplan position

Prompt 9 of 12 bis Produktversion 1 / lokale Pilotfähigkeit.

## 3. Purpose

Track-B UI-v2 nach Synthetic-E2E und Copied-Realistic-Sandbox-Validierung qualitativ schärfen:

- unklare Review-/Fehlerhinweise verständlicher machen
- Workspace-Fünf-Fragen-Wortlaut und Sandbox-Status klarer trennen
- Export/Reporting als Vorschau kennzeichnen
- Sandbox-Validierungsreport menschenlesbar machen
- Empty/Blocked-States und irreführende Copy entfernen
- Tests gegen Fake-Daten, private Defaults und Filename-as-Truth stärken

Ohne reale Rechnungen, ohne OCR/AI, ohne produktive Verarbeitung, ohne Track-A-Änderung, ohne Processing-Core-Änderung.

## 4. Quality gap review findings

Vor den Fixes:

1. **Workspace:** Sandbox-/Originalordner-/Produktiv-Hinweise waren nah, aber nicht einheitlich („nicht freigegeben“ vs. „noch nicht freigegeben“; kein einheitlicher Sandbox-Lauf-Banner mit kopierten Daten).
2. **Review:** Trennung Ergebnisse/Prüffälle/Fehler war nur teilweise sichtbar; „Unklare Nachweise“ statt „Unklare Fälle“.
3. **Export:** `MSG_EXPORT_FROM_REAL_RUN` sagte „keine Vorschau-Daten“ und widersprach der geforderten Export-Vorschau-Klarheit; kein DATEV-/Cloud-Produktiv-Disclaimer.
4. **Sandbox-Validierung:** Booleans vorhanden, aber keine menschenlesbaren Pflicht-Klarheitzeilen im Report.
5. **Settings/Status:** produktive Sperre vorhanden, Export-Sektion ohne Vorschau-/DATEV-Hinweis; SaaS-Feedback konnte Produktreife suggerieren.
6. **Filename-as-Truth / Private Defaults:** technisch bereits blockiert; Sichtbarkeit im Workspace/Export/Review unvollständig.

## 5. What changed

- Neu: `invoice_tool/ui_v2/clarity_copy.py` als Single Source für die sieben Pflichtformulierungen.
- Sandbox-Gate / Boundary: Klarheitstexte für Sandbox-Lauf, Originalordner, produktive Sperre vereinheitlicht.
- Export/Reporting: Preview-Flags + Disclaimer; irreführende „keine Vorschau-Daten“-Copy entfernt.
- Review-Workflow: immer getrennte Buckets + „Unklare Fälle bleiben zur Prüfung.“
- Workspace/Settings/Review-Pages: Helper-/Banner-/Empty-Copy an Klarheitstexte angebunden.
- Copied-Realistic-Validierung: `user_clarity_lines` und menschenlesbare Report-Messages; Review-Gründe klarer.
- Profile/Config Feedback: „SaaS-Entwurf“ → „Profilentwurf“ (kein SaaS-ready Eindruck).
- Tests: neuer Quality-Test + Anpassungen an Export/Copied/Workspace.

## 6. Workspace clarity improvements

- Readiness-Linien beginnen mit „Dies ist ein Sandbox-Lauf mit kopierten Daten.“
- „Originalordner werden nicht verwendet.“
- „Produktive Verarbeitung ist noch nicht freigegeben.“
- Empty-Detail enthält Trennung, Unklar-Fälle und „Dateinamen sind keine Belegwahrheit.“
- Export-Panel zeigt Preview-/Trennung-/Filename-Hinweise.

## 7. Review clarity improvements

- `MSG_BUCKETS_SEPARATED` immer in `separation_notes` / `honest_copy`.
- `MSG_UNCLEAR_CASES_STAY_REVIEW` = „Unklare Fälle bleiben zur Prüfung.“
- Payment-/Business-Unklar-Gründe menschenlesbar („bitte manuell prüfen“, Filename-Hinweis).
- Aktionen bleiben disabled / readiness-only.

## 8. Export/reporting clarity improvements

- `MSG_EXPORT_IS_PREVIEW` = „Export ist eine Vorschau, kein produktiver DATEV-/Cloud-Export.“
- Payload: `preview=true`, `productive_export=false`, `datev_export=false`, `cloud_export=false`, `disclaimer`.
- Settings-Export-Sektion verweist explizit auf Preview/DATEV/Trennung.

## 9. Sandbox validation clarity improvements

- Report enthält `user_clarity_lines` inkl. aller sieben Pflichtformulierungen.
- Explizite Felder: Originalordner ausgeschlossen, nur kopierte Daten, Sandbox-Lauf, produktiv blockiert, Filename-not-truth.

## 10. Settings/status clarity improvements

- `PRODUCTIVE_EXECUTION_NOTICE` exakt auf Pflichtformulierung.
- Produktstatus-Sektion mit Sandbox-/Original-/Produktiv-/Filename-Klarheit.
- Readiness-Banner enthält Sandbox- und Produktiv-Hinweise.

## 11. Why this does not process original real PDFs

Alle Änderungen sind Copy-/View-Model-/Test-Änderungen in UI-v2. Copied-Realistic bleibt stubbed Boundary + Fake-Dateien unter `tmp_path`. Kein OCR/AI, kein Live-Core-Runner.

## 12. Why this does not touch real invoice folders

Keine Pfad-Defaults, keine Ordner-Scans, keine Writes außerhalb pytest `tmp_path`. Originalordner bleiben Exclusion-Metadaten.

## 13. Why this does not touch Track A

Track-A-Dateien (`app_main.py`, Legacy-UI, Internal Launcher) wurden nicht geändert. Protection-Test bleibt grün.

## 14. Why this does not touch processing-core

Keine Imports/Änderungen an `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, `run.py`.

## 15. Tests added/updated

Hinzugefügt:

- `tests/test_ui_v2_quality_after_sandbox_validation.py`

Aktualisiert:

- `tests/test_ui_v2_export_reporting.py`
- `tests/test_ui_v2_copied_real_data_validation.py`

## 16. Tests run and results

Focused:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_quality_after_sandbox_validation.py \
  tests/test_ui_v2_copied_real_data_validation.py \
  tests/test_ui_v2_synthetic_e2e_product_flow.py \
  tests/test_ui_v2_export_reporting.py \
  tests/test_ui_v2_review_workflow.py \
  tests/test_track_a_internal_app_protection.py
```

Ergebnis: **83 passed**.

Alle Track-B UI-v2 / SaaS UI-v2:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Ergebnis: **367 passed, 44 skipped**.

## 17. Generalization confirmation

- kopierte realistische Daten nur unter `tmp_path`
- synthetische/copied Marker klar
- keine realen Rechnungsordner
- keine privaten Defaults (Hadi/SOMAA/Bismarck/AMEX/voba/Desktop-Pfade)
- kein Filename-as-Truth
- keine erfundenen Produktivresultate
- kein produktiver Execution-Toggle
- kein produktiver DATEV-/Cloud-Export
- kein Ordner-Scan / keine Ordnererzeugung außerhalb `tmp_path`
- kein OCR/AI
- Track A und Processing-Core unberührt

## 18. Current progress

- Prompt 9/12 complete: **yes**
- Remaining prompts: **3**

## 19. Remaining gaps

- packaging/onboarding
- pilot acceptance
- final release gate

## 20. Exact next task recommendation

`KI_RECHNUNGEN_PRODUCT_PACKAGING_AND_ONBOARDING_READINESS_01`
