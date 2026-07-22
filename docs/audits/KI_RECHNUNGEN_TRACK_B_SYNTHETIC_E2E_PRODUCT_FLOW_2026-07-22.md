# KI-Rechnungen Track B — Synthetic E2E Product Flow

**Task ID:** `KI_RECHNUNGEN_TRACK_B_SYNTHETIC_E2E_PRODUCT_FLOW_01`  
**Date:** 2026-07-22  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / Synthetic End-to-End Product Flow  
**Masterplan position:** Prompt 7 of 12 bis Produktversion 1 / lokale Pilotfähigkeit

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_SYNTHETIC_E2E_PRODUCT_FLOW_01`

## 2. Masterplan position: Prompt 7 of 12

Dieses Task beweist, dass die Track-B UI-v2-Module als ein kohärenter
Produktfluss zusammenarbeiten — ausschließlich mit synthetischen Testdaten.

## 3. Purpose

1. Explizites Sandbox-Setup  
2. Profile/Policy-Readiness  
3. Sandbox-Execution-Boundary mit gestubbten/synthetischen Ergebnissen  
4. Mapping in `ProcessingRunState` / `ProcessingResultSummary`  
5. Workspace-Ergebnisanzeige (fünf Nutzerfragen)  
6. Review-Workflow-Anzeige  
7. Export/Reporting-Vorschau  
8. Fehlertrennung  
9. Keine Fake-Daten jenseits der expliziten Synthetic-Fixture  
10. Keine realen Dateien/Ordner außerhalb von `pytest` `tmp_path`  
11. Track A unverändert  
12. Processing-Core unverändert  

## 4. What changed

Neu:

- `invoice_tool/ui_v2/synthetic_e2e_flow.py` — reine Synthetic-E2E-Helfer  
- `tests/test_ui_v2_synthetic_e2e_product_flow.py` — Produktfluss-Tests  
- dieses Audit-Dokument  

Mit aufgenommen (erlaubter UI-v2-Scope, lokal vorhanden, für E2E/Export nötig):

- `invoice_tool/ui_v2/export_reporting.py`  
- `invoice_tool/ui_v2/pages/workspace.py` (Ergebnisbericht / fünf Fragen)  
- `invoice_tool/ui_v2/pages/settings.py` (Export-Hinweis)  
- `invoice_tool/ui_v2/state.py` (`export_run_report`)  
- `tests/test_ui_v2_export_reporting.py`  

Nicht geändert:

- Track-A-Einstiege und Legacy-UI  
- Processing-Core (`processing` / `routing` / `classification` / `run` …)  
- Scripts, Resources, PDFs, venv, echte Rechnungsordner  

## 5. Synthetic E2E fixture behavior

Modul: `synthetic_e2e_flow.py`

- `SyntheticE2ECase` legt unter `tmp_path` nur Sandbox-/Original-Pfadlayout an  
- Dokumentlabels: `document-001` (Erfolg), `document-002` (Review),
  `document-003` (Fehler)  
- Geplante Zielhinweise nur unter Sandbox-Ausgabeordner  
- `build_synthetic_boundary_result(...)` liefert Stub-Payload ohne OCR/AI  
- `run_synthetic_track_b_product_flow(...)` verdrahtet Gate → Adapter →
  Workspace → Review → Export-Preview  
- Kein Schreiben außerhalb von `tmp_path` durch den Flow-Helper  

## 6. Sandbox gate behavior

- Freigabe nur bei Sandbox-Modus, kopierter-Daten-Bestätigung, expliziter Quelle,
  Profil/Konfiguration/Policy und Sandbox-Pfadkonfinement  
- Ohne `copied_data_confirmed` → `blocked_missing_copied_data_confirmation`  
- Produktive Ausführung bleibt blockiert  

## 7. Sandbox execution boundary behavior

- Boundary erhält nur Sandbox-`input_folder` / `output_folder` / `sandbox_root`  
- Original-Quellordner nur als Ausschluss-Metadatum, nie als VerarbeitungsPfad  
- Runner ist injizierbar; Synthetic-E2E stubbt Ergebnisse  

## 8. Adapter mapping behavior

- `LocalProcessingAdapter` mappt Stub-Ergebnis auf `ProcessingRunState`  
- Counts: 2 Results (davon 1 fehlgeschlagen), 1 Review-Item, 1 Error-String  
- `execution_gate=ready_for_sandbox_execution` bei erfolgreichem Stub  

## 9. Workspace five-question behavior

Über `build_run_report_view_model` / Workspace-Report-VM:

1. Was wurde erkannt? → `document-001`  
2. Was ist unklar? → `document-002`  
3. Was ist fehlgeschlagen? → `document-003` + synthetischer Fehlertext  
4. Welche Dateien wären wohin gegangen? → geplante Sandbox-Zielhinweise /
   „Zur Prüfung“  
5. Welche Zusammenfassung bekommt der Nutzer? → Klartext-Summary mit Counts  

## 10. Review workflow behavior

- Queue zeigt genau den synthetischen Prüffall `document-002`  
- Results/Errors bleiben getrennt (`MSG_RESULTS_SEPARATED` /
  `MSG_ERRORS_SEPARATED`)  
- Keine Dateimutationen, keine PDF-Öffnung  

## 11. Export/reporting behavior

- Preview-Payload enthält die fünf Frageblöcke  
- `cloud=false`, `persistence=local_export_only`  
- Keine privaten/Zahlungs-/Konto-Defaults  
- Optionaler Dateiexport nur auf expliziten Pfad (Tests: `tmp_path`)  

## 12. Why this does not process real PDFs

- Kein Import von Processing-Core  
- Boundary-Runner ist gestubbt  
- Fixture enthält keine PDF-Bytes und startet keine OCR/AI-Pipeline  

## 13. Why this does not touch real invoice folders

- Alle Pfade liegen unter `pytest` `tmp_path`  
- Originalordner ist ein synthetischer Ausschlusspfad, nie Eingang  
- Kein Scan von Desktop-/Users-Rechnungsordnern  

## 14. Why this does not touch Track A

- Keine Änderungen an `app_main.py`, Internal Launcher oder Legacy-UI  
- Synthetic-Modul importiert Track A nicht  
- Einstiege `app_main` vs `app_ui_v2` bleiben getrennt  

## 15. Why this does not touch processing-core

- AST-/Import-Checks verbieten Core-Imports in den Flow-Modulen  
- Laufzeit nutzt nur UI-v2-Adapter + injizierten Stub-Runner  

## 16. Tests added/updated

Neu:

- `tests/test_ui_v2_synthetic_e2e_product_flow.py`

Mit aufgenommen:

- `tests/test_ui_v2_export_reporting.py`

## 17. Tests run and results

Focused:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_synthetic_e2e_product_flow.py \
  tests/test_ui_v2_export_reporting.py \
  tests/test_ui_v2_sandbox_execution_wiring.py \
  tests/test_ui_v2_review_workflow.py \
  tests/test_track_a_internal_app_protection.py
```

Ergebnis: **72 passed**

Alle Track-B UI-v2 Tests:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Ergebnis: **339 passed, 44 skipped**

## 18. Generalization confirmation

- Nur synthetische Labels (`document-001` …)  
- Keine Hadi/SOMAA/Bismarck/AMEX/voba-Defaults  
- Keine Desktop-/Users-Privatpfade  
- Keine Filename-as-truth-Inferenz  
- Keine produktive Ausführung / kein produktiver Export  
- Kein Folder-Scan außerhalb `tmp_path`  
- Track A und Processing-Core unverändert  

## 19. Current progress

- Prompt 7/12 complete: **yes**  
- Remaining prompts: **5**

## 20. Remaining gaps

- copied-real-data validation  
- quality fixes  
- packaging/onboarding  
- pilot acceptance  
- final release gate  

## 21. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_SANDBOX_COPIED_REAL_DATA_VALIDATION_01`
