# KI-Rechnungen Track B — Sandbox Copied Real Data Validation

**Task ID:** `KI_RECHNUNGEN_TRACK_B_SANDBOX_COPIED_REAL_DATA_VALIDATION_01`  
**Date:** 2026-07-22  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / Sandbox Copied Real Data Validation  
**Masterplan position:** Prompt 8 of 12 bis Produktversion 1 / lokale Pilotfähigkeit

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_SANDBOX_COPIED_REAL_DATA_VALIDATION_01`

## 2. Masterplan position: Prompt 8 of 12

Dieses Task validiert Track B gegen kopierte, realistische Fixture-Daten
innerhalb der Sandbox-Grenzen — ohne Originalordner, ohne OCR/AI, ohne
produktive Verarbeitung.

## 3. Purpose

1. Sichere Validierung mit kopierten/realistischen Fixture-Daten nur unter
   `pytest` `tmp_path` / Sandbox-Wurzel  
2. Nachweis, dass Gate Originalordner ausschließt und Sandbox-Pfade freigibt  
3. Boundary erhält nur kopierte Sandbox-Pfade  
4. Result-/Review-/Error-Kategorien werden realistisch gemappt  
5. Review zeigt Zahlungs- und betrieblich/persönliche Unklarheiten  
6. Export/Reporting deckt recognized/review/error/target/summary ab  
7. Workspace beantwortet die fünf Produktfragen mit kopierten Daten  
8. Keine privaten Defaults, kein Filename-as-Truth  
9. Track A unverändert  
10. Processing-Core unverändert  

## 4. What changed

Neu:

- `invoice_tool/ui_v2/copied_real_data_validation.py` — Validierungshelfer /
  Fixture / Report  
- `tests/test_ui_v2_copied_real_data_validation.py` — Sandbox-Validierungstests  
- dieses Audit-Dokument  

Nicht geändert:

- Track-A-Einstiege und Legacy-UI  
- Processing-Core (`processing` / `routing` / `classification` / `run` …)  
- Scripts, Resources, PDFs, venv, echte Rechnungsordner  
- `app_main.py`, Legacy-UI-Module, `pyproject.toml`  

## 5. Copied realistic fixture behavior

Modul: `copied_real_data_validation.py`

- `build_copied_realistic_fixture(tmp_root)` legt unter `tmp_path` an:
  - Sandbox-Wurzel `copied-realistic-sandbox`
  - `copied-inbox` / `copied-outbox`
  - ausgeschlossenen Originalpfad `copied-original-source-excluded`
- Neutrale Fake-Dateien: `copied-*.fakepdf` (leer) + `.meta.txt`
  mit `filename_is_not_source_of_truth=true`
- Dokumentlabels:
  - `copied-invoice-001` → recognized
  - `copied-receipt-002` → review_payment_unclear
  - `copied-unclear-003` → review_business_unclear
  - `copied-error-004` → error_unsupported
- Keine realen Vendor-Namen, keine privaten Zahlungs-/Konto-IDs
- Keine echten PDF-Bytes im Repository

## 6. Validation report behavior

- `CopiedRealDataValidationReport` fasst Gate-/Boundary-/Workspace-/Review-/
  Export-Beobachtungen zusammen  
- `build_quality_checklist_rows(...)` liefert pro Fall:
  document id, category, reason, expected UI section, expected export section,
  `filename_is_not_truth`  
- `validate_copied_real_data_sandbox(...)` verdrahtet den gesamten
  Track-B-Produktfluss und erzeugt den Report  

## 7. Sandbox gate behavior

- Freigabe nur bei Sandbox-Modus, kopierter-Daten-Bestätigung, expliziter Quelle,
  Profil/Konfiguration/Policy und Sandbox-Pfadkonfinement  
- Originalordner als Eingang → blockiert  
  (`blocked_original_folder` / `blocked_input_outside_sandbox`)  
- Produktive Ausführung bleibt blockiert  

## 8. Boundary path behavior

- Boundary erhält nur Sandbox-`input_folder` / `output_folder` / `sandbox_root`  
- Original-Quellordner nur als Ausschluss-Metadatum  
- Runner ist injizierbar; Validierung stubbt Ergebnisse (kein OCR/AI)  

## 9. Workspace five-question behavior

1. Was wurde erkannt? → `copied-invoice-001`  
2. Was ist unklar? → `copied-receipt-002`, `copied-unclear-003`  
3. Was ist fehlgeschlagen? → `copied-error-004` + Unsupported-Fehlertext  
4. Welche Dateien wären wohin gegangen? → geplante Sandbox-Ziele /
   „Zur Prüfung“  
5. Welche Zusammenfassung bekommt der Nutzer? → Klartext-Summary mit Counts  

## 10. Review workflow behavior

- Queue zeigt beide unklaren Fälle (Zahlung + betrieblich/persönlich)  
- Results/Errors bleiben getrennt  
- Keine Dateimutationen, keine PDF-Öffnung  

## 11. Export/reporting behavior

- Preview-Payload enthält recognized / unclear / failed / destinations /
  user_summary  
- `cloud=false`, `persistence=local_export_only`  
- Keine privaten/Zahlungs-/Konto-Defaults  
- Kein Dateiexport außerhalb von Test-`tmp_path` in diesem Task  

## 12. Result quality checklist behavior

Explizite Kategorien (Validierungs-Scaffolding, keine Produktionsklassifikation):

| document id | category | expected UI | expected export |
|---|---|---|---|
| copied-invoice-001 | recognized | recognized | recognized |
| copied-receipt-002 | review_payment_unclear | review | unclear |
| copied-unclear-003 | review_business_unclear | review | unclear |
| copied-error-004 | error_unsupported | error | failed |

Jedes Zeile bestätigt `filename_is_not_truth=true`.

## 13. Why this does not process original real PDFs

- Kein Import von Processing-Core  
- Boundary-Runner ist gestubbt  
- Fixture enthält nur leere `.fakepdf`-Platzhalter  
- Keine OCR/AI-Pipeline  

## 14. Why this does not touch real invoice folders

- Alle Pfade liegen unter `pytest` `tmp_path`  
- Originalordner ist ein ausgeschlossener Fixture-Pfad, nie Eingang  
- Kein Scan von Desktop / `02_Rechnungseingang` / `Eingang`  

## 15. Why this does not touch Track A

- Keine Änderungen an `app_main.py`, Internal Launcher, Legacy-UI  
- Track-A-Schutztest bleibt grün  
- Einstiege bleiben getrennt (`app_main` ≠ `app_ui_v2`)  

## 16. Why this does not touch processing-core

- Keine Edits an `processing.py` / `routing*.py` / `classification.py` /
  `target_routing.py` / `run.py`  
- AST-/Import-Checks verbieten Core-Imports in den Validierungsmodulen  

## 17. Tests added/updated

Neu:

- `tests/test_ui_v2_copied_real_data_validation.py`

Unverändert belassen (bereits abgedeckt, weiterhin Teil der Safe-Run-Liste):

- `tests/test_ui_v2_synthetic_e2e_product_flow.py`
- `tests/test_ui_v2_export_reporting.py`
- `tests/test_ui_v2_sandbox_execution_wiring.py`
- `tests/test_track_a_internal_app_protection.py`

## 18. Tests run and results

Focused:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_copied_real_data_validation.py \
  tests/test_ui_v2_synthetic_e2e_product_flow.py \
  tests/test_ui_v2_export_reporting.py \
  tests/test_ui_v2_sandbox_execution_wiring.py \
  tests/test_track_a_internal_app_protection.py
```

All Track-B UI-v2:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Focused: **76 passed**  
All Track-B UI-v2 (`test_ui_v2_*.py` + `test_saas_ui_v2_*.py`): **356 passed, 44 skipped**

## 19. Generalization confirmation

- kopierte realistische Daten nur in `tmp_path`  
- keine realen Rechnungsordner  
- keine Hadi/SOMAA/Bismarck/AMEX/voba Defaults  
- keine Desktop-/`/Users`-Pfaddefaults in Modul/Fixture  
- kein Filename-as-Truth  
- keine Fake-Produktionsergebnisse jenseits der expliziten Fixture  
- kein produktiver Execution-Toggle  
- kein produktiver Export  
- kein Folder-Scan / keine Ordnererstellung außerhalb `tmp_path`  
- kein echtes PDF-Processing, kein OCR/AI  
- Track A unverändert, Einstiege getrennt  
- Processing-Core unberührt  

## 20. Current progress

- Prompt 8/12 complete: **yes** (nach grünem Testlauf + Commit/Push-Gates)  
- Remaining prompts: **4**

## 21. Remaining gaps

- quality fixes nach Sandbox-Validierung  
- packaging/onboarding  
- pilot acceptance  
- final release gate  

## 22. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_QUALITY_FIXES_AFTER_SANDBOX_VALIDATION_01`
