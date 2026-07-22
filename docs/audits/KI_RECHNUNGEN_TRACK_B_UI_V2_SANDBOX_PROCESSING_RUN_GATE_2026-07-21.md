# KI-Rechnungen Track B UI-v2 — Sandbox Processing Run Gate

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_SANDBOX_PROCESSING_RUN_GATE_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Sandbox Processing Run Gate  
**Masterplan position:** Prompt 1 of 12 bis Produktversion 1 / lokale Pilotfähigkeit

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_SANDBOX_PROCESSING_RUN_GATE_01`

## 2. Masterplan position: Prompt 1 of 12

Dieses Task ist der erste von zwölf Schritten bis lokale Pilotfähigkeit.  
Es bereitet eine sichere Sandbox-Ausführungsgrenze vor — **ohne** produktive Verarbeitung und **ohne** Core-Dry-Run-Implementierung.

## 3. Purpose

Track-B-only Sandbox Execution Gate schaffen, das festlegt, wann ein zukünftiger UI-v2-Lauf den bestehenden Processing-Core gegen **kopierte** Testdaten aufrufen darf:

1. Sandbox-Pfadvalidierung  
2. Originalordner-Ausschluss  
3. Copied-data-only-Anforderung  
4. UI-v2 State/Contract-Readiness für Sandbox-Modus  
5. Tests gegen unsichere Ordner  
6. Audit-Vergleich Sandbox-Route vs Dry-Run-Route  
7. Exakter Next-Task: Sandbox Execution Wiring (falls sicher)

## 4. Why sandbox route is chosen before Core Dry Run

Der vorherige PO-Gate empfahl Option B (Core Dry Boundary Shim). Der Product Owner hat entschieden, **zuerst** eine schnellere Sandbox-Copy-Route zu bewerten:

| Route | Vorteil | Risiko |
|---|---|---|
| Core Dry Run | Keine Dateimutationen im Core | Erfordert Core-Änderung; Track-A-Blast-Radius |
| Sandbox Copy Gate | Track-B-only; Core unberührt; Originale ausgeschlossen | Späterer Core-Aufruf mutiert nur Sandbox-Kopien |

Die Sandbox-Route erlaubt Fortschritt ohne Core-Touch und ohne reale Originalordner. Core Dry Run bleibt dokumentiert als weiterhin fehlend.

## 5. Sandbox safety model

Neues Modul: `invoice_tool/ui_v2/sandbox_processing_gate.py`

Strukturen/Funktionen:

- `SandboxProcessingMode` (`disabled` / `sandbox` / `productive`)
- `SandboxPathValidationResult`
- `SandboxProcessingGate`
- `validate_sandbox_paths(...)`
- `build_sandbox_run_request(...)`
- `evaluate_sandbox_gate(...)`

Regeln (Auszug):

1. Sandbox-Modus muss explizit sein  
2. Input/Output müssen explizit gewählt sein  
3. Input/Output müssen unter `sandbox_root` liegen  
4. Original-Quellordner ≠ Sandbox-Input  
5. Original darf nicht Verarbeitungseingang sein  
6. `copied_data_confirmed` muss true sein  
7. Produktive Ausführung bleibt blockiert  
8. Validierung: keine FS-Writes, kein Ordner-Create, kein Scan, keine PDF-Verarbeitung  
9. Keine privaten Default-Pfade

## 6. Path validation behavior

String-only Normalisierung über `os.path.normpath` (Pfad muss nicht existieren):

- fehlender Sandbox-Modus → `blocked_missing_sandbox`
- fehlende Sandbox-Wurzel → `blocked_missing_sandbox_root`
- Input/Output außerhalb Sandbox → `blocked_*_outside_sandbox`
- Input == Output → `blocked_same_input_output`
- Output unter Original → `blocked_output_inside_original`

`creates_folders`, `scans_folders`, `processes_pdfs` sind immer `False`.

## 7. Original-folder exclusion behavior

- `original_source_folder` ist für Freigabe erforderlich  
- Input gleich Original oder unter Original → `blocked_original_folder`  
- Output unter Original → `blocked_output_inside_original`  
- Workspace-Copy: „Originalordner werden nicht als Verarbeitungseingang akzeptiert.“

## 8. Copied-data confirmation behavior

- `copied_data_confirmed` default `False`  
- ohne Bestätigung → `blocked_missing_copied_data_confirmation`  
- Workspace-Copy: „Verarbeitung ist nur mit kopierten Testdaten erlaubt.“

## 9. LocalProcessingAdapter behavior

`start_run`:

1. bestehende Struktur-/Policy-Validierung  
2. Benutzerbestätigung erforderlich  
3. produktive Ausführung immer blockiert (`blocked_productive_execution`)  
4. Sandbox-Gate auswerten  
5. ohne Freigabe → blocked mit Reason-Code  
6. mit Freigabe → `ready` / `ready_for_sandbox_execution`  
7. **kein** Core-Import, **kein** PDF-Lauf, **keine** Dateimutationen

Unterscheidbare Gates:

- `blocked_missing_sandbox`
- `blocked_original_folder`
- `blocked_missing_copied_data_confirmation`
- `blocked_productive_execution`
- `ready_for_sandbox_execution`

## 10. Workspace copy behavior

Ehrliche Sandbox-Readiness-Zeilen in Workspace:

- „Sandbox-Modus: vorbereitet“
- „Verarbeitung ist nur mit kopierten Testdaten erlaubt.“
- „Originalordner werden nicht als Verarbeitungseingang akzeptiert.“
- „Produktive Verarbeitung ist nicht freigegeben.“
- „Core-Dry-Run ist noch nicht vorhanden.“

Kein produktiver Toggle, kein Auto-Create von Sandbox-Ordnern, kein Scan.

State-Felder (Defaults sicher/blocked):

- `workspace_sandbox_mode`
- `workspace_sandbox_root`
- `workspace_original_source_folder`
- `workspace_copied_data_confirmed`

## 11. Why this does not process real PDFs

Validierung und Adapter-Start rufen weder `invoice_tool.processing` noch `invoice_tool.run` auf.  
Selbst bei Sandbox-Freigabe liefert der Adapter nur `ready_for_sandbox_execution` — keine Pipeline.

## 12. Why this does not touch real invoice folders

- keine Ordnererstellung  
- kein Ordner-Scan  
- keine Pfad-Defaults auf Desktop/private Invoice-Ordner  
- Originalpfade werden nur stringseitig ausgeschlossen  
- echte Rechnungsordner erscheinen nicht in diesem Commit

## 13. Why this does not touch Track A

Nicht geändert / nicht staged:

- `app_main.py`, `app_internal_launcher.py`
- Legacy-UI (`gui`, `ui_shell`, `ui_workspace`, …)
- Known legacy dirty files bleiben lokal unstaged

## 14. Why this does not touch processing-core

Nicht geändert:

- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`
- `invoice_tool/run.py`

Track-B-only Gate war ohne Core-Änderung möglich → kein `CORE_CHANGE_REQUIRED`.

## 15. Tests added/updated

Neu:

- `tests/test_ui_v2_sandbox_processing_gate.py`

Aktualisiert:

- `tests/test_ui_v2_local_processing_adapter.py`
- `tests/test_ui_v2_workspace_processing_contract.py`
- `tests/test_ui_v2_workspace_folder_selection.py`
- `tests/test_ui_v2_workspace_empty_state.py`

## 16. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_local_processing_adapter.py \
  tests/test_ui_v2_workspace_folder_selection.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_run_result_display_shell.py \
  tests/test_ui_v2_policy_editor_controls.py \
  tests/test_ui_v2_sandbox_processing_gate.py
→ 93 passed

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
→ 253 passed, 44 skipped
```

## 17. Generalization confirmation

- keine Hadi/SOMAA/Bismarck/AMEX/voba Defaults  
- keine Desktop/`/Users`-Pfad-Defaults  
- kein Filename-as-truth  
- keine Fake Payment/Account/Business-Results  
- keine Fake Review-/Processing-Results  
- kein produktiver Execution-Toggle  
- kein Folder-Scan / Folder-Create / PDF-Processing in diesem Task  
- UI-Wording generisch  
- Track A unberührt  
- Processing/Routing/Classification-Core unberührt

## 18. Current progress

| Item | Status |
|---|---|
| Prompt 1/12 complete | **yes** |
| Remaining prompts | **11** |

## 19. Remaining gaps

- sandbox execution wiring  
- review workflow completion  
- profile/policy completion  
- export/reporting completion  
- Track A regression gate  
- synthetic E2E  
- copied-real-data validation  
- quality fixes  
- packaging/onboarding  
- pilot acceptance  
- final release gate  

## 20. Exact next task recommendation

**`KI_RECHNUNGEN_TRACK_B_UI_V2_SANDBOX_EXECUTION_WIRING_01`**

Sandbox Execution Wiring:

1. Nur nach Sandbox-Gate-Freigabe  
2. Core nur gegen Sandbox-Kopien aufrufen  
3. Originale weiterhin ausschließen  
4. Produktive Ausführung weiter blockiert  
5. Kein Fake-Result-Fallback  
6. Tests mit synthetischen Sandbox-Pfaden (keine echten Invoice-Ordner)

Vergleich bleibt gültig: Core Dry Run ist separat und erfordert Core-Änderung; Sandbox-Wiring kann Track-B-first erfolgen, solange Mutation strikt auf Sandbox-Kopien beschränkt bleibt.
