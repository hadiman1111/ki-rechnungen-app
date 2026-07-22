# KI-Rechnungen Track A — Internal App Regression and Protection Gate

**Task ID:** `KI_RECHNUNGEN_TRACK_A_INTERNAL_APP_REGRESSION_AND_PROTECTION_GATE_01`  
**Date:** 2026-07-22  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track A Protection / Internal App Regression Gate  
**Masterplan position:** Prompt 6 of 12 bis Produktversion 1 / lokale Pilotfähigkeit

## 1. Task ID

`KI_RECHNUNGEN_TRACK_A_INTERNAL_APP_REGRESSION_AND_PROTECTION_GATE_01`

## 2. Masterplan position: Prompt 6 of 12

Nach Abschluss von Prompt 5 (Export / Reporting) prüft dieses Task, dass die
interne/lokale Track-A-App nach dem Track-B UI-v2-Ausbau funktional getrennt und
geschützt bleibt — ohne Track-A-Verhalten zu ändern.

## 3. Purpose

Track-A-Regressionsschutz und Trennungsgate schaffen:

1. `app_main.py` bleibt Track-A-/Internal-Entry  
2. `app_ui_v2.py` bleibt Track-B-/General-Product-Entry  
3. Track-A Legacy-UI-Dateien wurden nicht durch Track-B-Arbeit ersetzt  
4. Track-B ändert keine Track-A-Runtime-Pfade  
5. Internal Launcher / Folder-Picker bleiben geschützt prüfbar  
6. Processing-Core unverändert  
7. Keine Scripts/Resources/PDF/venv/testing/realen Rechnungen im Commit  
8. Bekannte Legacy-UI-Dirty-Dateien bleiben unstaged  
9. Sichere Regression ohne echte PDF-Verarbeitung  
10. Nächster Schritt: synthetischer Track-B E2E Product Flow  

## 4. Current Track A entry state

| Entry | Ziel |
|---|---|
| `app_main.py` | lazy `invoice_tool.gui.build_ui` — interne/Standalone-App |
| `app_internal_launcher.py` | `invoice_tool.internal_launcher.app.build_internal_launcher` |

- `app_main.py` importiert **nicht** `invoice_tool.ui_v2`  
- GUI startet nur unter `if __name__ == "__main__"`  
- Gegen HEAD: geschützte Track-A-Entry/Shell-Dateien unverändert (außer bekannte Legacy-Dirty)  

## 5. Current Track B entry state

| Entry | Ziel |
|---|---|
| `app_ui_v2.py` | lazy `invoice_tool.ui_v2.app.build_ui_v2` — General Product UI-v2 |

- Explizit dokumentiert: ersetzt `app_main.py` nicht  
- UI-v2-Module (`app.py`, `export_reporting.py`, Sandbox-/Adapter-Module) importieren keine Track-A-GUI-Module  

## 6. Track A / Track B separation findings

1. Distinct entry files: `app_main.py` ≠ `app_ui_v2.py`  
2. Track A → `invoice_tool.gui`; Track B → `invoice_tool.ui_v2`  
3. Track-A UI-Module (`gui`, `ui_shell`, `ui_workspace`, …) importieren kein `ui_v2`  
4. Geprüfte Track-B-Entry-Module importieren kein `gui` / Legacy-`ui_*` / `app_main`  
5. Letzte Track-B UI-v2-Commits (Sandbox, Review, Profil-Policy, …) enthalten keine geschützten Track-A- oder Processing-Core-Dateien  
6. `UiV2State`-Defaults: keine privaten Ordnerpfade; Sandbox/Export standardmäßig leer/aus  

## 7. Protected Track A files status

| Datei | Status |
|---|---|
| `app_main.py` | clean vs HEAD |
| `app_internal_launcher.py` | clean vs HEAD |
| `invoice_tool/gui.py` | clean vs HEAD |
| `invoice_tool/ui_shell.py` | clean vs HEAD |
| `invoice_tool/ui_workspace.py` | clean vs HEAD |
| `invoice_tool/ui_configurations.py` | clean vs HEAD |
| `invoice_tool/ui_profiles.py` | clean vs HEAD |
| `invoice_tool/ui_review.py` | clean vs HEAD |
| `invoice_tool/ui_settings.py` | clean vs HEAD |
| `invoice_tool/ui_profile_dialog.py` | lokal dirty, **unstaged** (bekannt) |
| `invoice_tool/ui_document_rules.py` | lokal untracked, **unstaged** (bekannt) |

In diesem Task wurden **keine** Track-A-Dateien geändert.

## 8. Processing-core status

Alle unverändert vs HEAD und nicht staged:

- `invoice_tool/processing.py`  
- `invoice_tool/routing.py`  
- `invoice_tool/routing_guards.py`  
- `invoice_tool/classification.py`  
- `invoice_tool/target_routing.py`  
- `invoice_tool/run.py`  

## 9. Legacy dirty files status

Bekannte lokale Legacy-UI-Dirty-Dateien bewusst **nicht** gestaged/committed:

- `invoice_tool/ui_profile_dialog.py` (modified)  
- `invoice_tool/ui_document_rules.py` (untracked)  

Nicht als Processing-Core-Dirty klassifiziert.

## 10. Tests added/updated

Neu:

- `tests/test_track_a_internal_app_protection.py`

Prüft u. a.:

- getrennte Entry-Points  
- `app_main` ohne `ui_v2` als App-Pfad  
- `app_ui_v2` nutzt `ui_v2`  
- Track-A-Module importieren kein `ui_v2`  
- Track-B-Entry-Module importieren keine Track-A-Runtime  
- geschützte Track-A-/Core-Dateien nicht staged  
- `profile_config.local.json` nicht staged  
- keine echten Rechnungs-/PDF-Pfade staged  
- recent Track-B-Commits ohne Track-A-/Core-Payload  
- keine privaten Track-B-Default-Ordner  
- sichere Imports von Entry/`ui_v2.app`/`export_reporting`  

Bestehende Safe-Tests unverändert mitgelaufen:

- `tests/test_internal_launcher_folder_picker.py`  
- `tests/test_gui_startup.py`  

## 11. Tests run and results

Fokussiert:

```text
.venv/bin/python -m pytest \
  tests/test_track_a_internal_app_protection.py \
  tests/test_ui_v2_export_reporting.py \
  tests/test_ui_v2_sandbox_execution_wiring.py \
  tests/test_ui_v2_profile_policy.py \
  tests/test_ui_v2_review_workflow.py \
  tests/test_internal_launcher_folder_picker.py \
  tests/test_gui_startup.py
```

Ergebnis: **80 passed, 16 skipped**

UI-v2 + Protection:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_*.py \
  tests/test_saas_ui_v2_*.py \
  tests/test_track_a_internal_app_protection.py
```

Ergebnis: **340 passed, 44 skipped**

## 12. Generalization confirmation

- Keine neuen Hadi/SOMAA/Bismarck/AMEX/voba Defaults in Track-B-Entry/State  
- Keine Desktop-/`/Users/`-Defaultpfade in Entry-Bootstrap  
- Kein Filename-as-truth in diesem Task  
- Keine Fake-Results eingeführt  
- Kein produktiver Execution-Toggle  
- Kein produktiver Export aktiviert  
- Kein Folder-Scan / Folder-Creation  
- Keine echte PDF-Verarbeitung  

## 13. Why this does not process real PDFs

Nur statische AST-/Git-/Default-Checks und bestehende UI-v2-Unit-Tests.
Kein OCR, kein AI-Call, kein Processing-Core-Lauf, kein PDF-IO.

## 14. Why this does not touch real invoice folders

Keine Originalordner-Scans, keine Pfadmutation, keine Staging von Rechnungsordnern
oder PDFs. Track-B-Defaults bleiben ohne feste privaten Eingangs-/Ausgangspfade.

## 15. Why this does not modify Track A behavior

Erlaubt waren nur neue Protection-Tests und dieses Audit.
`app_main.py`, Launcher und Legacy-UI wurden nicht geändert.

## 16. Current progress

- Prompt 6/12 complete: **yes**  
- Remaining prompts: **6**

## 17. Remaining gaps

- synthetic E2E  
- copied-real-data validation  
- quality fixes  
- packaging/onboarding  
- pilot acceptance  
- final release gate  

## 18. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_SYNTHETIC_E2E_PRODUCT_FLOW_01`
