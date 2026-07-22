# KI-Rechnungen Track B UI-v2 — Sandbox Execution Wiring

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_SANDBOX_EXECUTION_WIRING_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Sandbox Execution Wiring  
**Masterplan position:** Prompt 2 of 12 bis Produktversion 1 / lokale Pilotfähigkeit

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_SANDBOX_EXECUTION_WIRING_01`

## 2. Masterplan position: Prompt 2 of 12

Dieses Task verdrahtet die erste kontrollierte Sandbox-Ausführung für Track-B UI-v2  
— nur nach Sandbox-Gate-Freigabe, nur gegen kopierte Testdaten, ohne produktive Freigabe.

## 3. Purpose

1. Sandbox-Gate-Freigabe erzwingen  
2. Copied-data-Bestätigung erzwingen  
3. Sandbox Input/Output-Pfade erzwingen  
4. Originalordner blockieren  
5. In Tests nur synthetische/tmp-Daten / monkeypatchte Boundary  
6. `ProcessingRunState` / `ProcessingResultSummary` an UI-v2 liefern  
7. Produktive Ausführung blockiert halten  
8. Track-A-Defaultverhalten erhalten  

## 4. What changed

Neu:

- `invoice_tool/ui_v2/sandbox_execution_boundary.py`
- `tests/test_ui_v2_sandbox_execution_wiring.py`
- dieses Audit-Dokument

Aktualisiert:

- `invoice_tool/ui_v2/local_processing_adapter.py` — nach Gate-Freigabe Boundary-Aufruf
- `invoice_tool/ui_v2/sandbox_processing_gate.py` — Readiness-Copy für verdrahtete Sandbox-Ausführung
- `invoice_tool/ui_v2/processing_state.py` — Message-Text
- `invoice_tool/ui_v2/pages/workspace.py` — `SANDBOX_EXECUTION_WIRED` export
- bestehende Adapter-/Gate-/Workspace-Tests an neues Verhalten angepasst

## 5. Sandbox execution wiring behavior

`LocalProcessingAdapter.start_run`:

1. Struktur-/Policy-Validierung  
2. Benutzerbestätigung erforderlich  
3. produktive Ausführung immer blockiert  
4. Sandbox-Gate auswerten  
5. ohne Freigabe → blocked, **kein** Boundary-Aufruf  
6. mit Freigabe + `execution_scope == sandbox` + `copied_data_confirmed`  
   → Sandbox-Boundary mit **nur** Sandbox-Input/Output  
7. Ergebnis → `ProcessingRunState` (`completed` / `failed`)  
8. kein Auto-Run beim Laden der Seite  

## 6. Core call boundary behavior

Modul: `sandbox_execution_boundary.py`

- `SandboxCoreCallArgs` — enthält Sandbox-Pfade + Profil/Konfig-IDs  
- `original_source_folder` nur zur Ausschlussprüfung, nie als Verarbeitungs-Input  
- `sandbox_core_runner` — Monkeypatch-/Injektions-Seam  
- **Default-Runner unbound:** ruft `invoice_tool.run.run_once` **nicht** auf  
  (kein Profil-Pfad-Resolver in UI-v2; Live-`run_once` bräuchte echte Config/PDF/OCR  
  und schreibt technische Run-Artefakte außerhalb der Sandbox-Wurzel)  
- Tests injizieren deterministische Stubs und beweisen Pfad-Confinement  
- Processing-Core bleibt unverändert; kein `CORE_CHANGE_REQUIRED` für diese Track-B-Seam  

## 7. Result mapping behavior

`map_sandbox_core_result_to_run_state`:

- `ok=True` → `completed`  
- `ok=False` → `failed`  
- mappt nur gelieferte `results` / `review_items` / `errors` / `run_id`  
- keine erfundenen Vendor-/Zahlungs-/Konto-/Business-Felder  

## 8. Workspace behavior

- zeigt Sandbox-Readiness inkl. „Sandbox-Ausführung nur nach Gate-Freigabe gegen kopierte Testdaten.“  
- Core-Dry-Run bleibt als fehlend ausgewiesen  
- Ergebnisanzeige nur wenn State echte Results enthält  
- keine Fake-Counter, kein produktiver Toggle, kein Auto-Run  
- UI-Click-Verdrahtung über bestehende `apply_start_processing` (Adapter muss injiziert sein);  
  breitere CTA-Live-UX bleibt Folgeaufgabe  

## 9. Why this does not touch original invoice folders

- Gate blockiert Original als Input und Output unter Original  
- Boundary erhält Original nur zur Ausschlussprüfung  
- Tests nutzen ausschließlich `pytest` `tmp_path`  
- kein Scan/Create außerhalb test-eigener tmp-Pfade  

## 10. Why this does not make Track B productive

- `dry_run=False` / `productive_execution_allowed` / `execution_scope == productive` → blocked  
- Default-Runner unbound → kein Live-PDF-Lauf  
- Workspace-Copy: produktive Verarbeitung nicht freigegeben  

## 11. Why this does not touch Track A

Nicht geändert / nicht staged:

- `app_main.py`, `app_internal_launcher.py`  
- Legacy-UI (`gui`, `ui_shell`, `ui_workspace`, …)  
- Known legacy dirty files bleiben lokal unstaged  

## 12. Processing-core untouched

Nicht geändert:

- `invoice_tool/processing.py`  
- `invoice_tool/routing.py`  
- `invoice_tool/routing_guards.py`  
- `invoice_tool/classification.py`  
- `invoice_tool/target_routing.py`  
- `invoice_tool/run.py`  

Kein `CORE_CHANGE_REQUIRED`: Track-B-Boundary verdrahtet den Aufruf ohne Core-Patch.  
Live-`run_once`-Bindung bleibt injizierbar und bewusst unbound (Profilpfade / Side-Effects).

## 13. Tests added/updated

Neu:

- `tests/test_ui_v2_sandbox_execution_wiring.py`

Aktualisiert:

- `tests/test_ui_v2_local_processing_adapter.py`  
- `tests/test_ui_v2_sandbox_processing_gate.py`  
- `tests/test_ui_v2_workspace_processing_contract.py`

## 14. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_sandbox_processing_gate.py \
  tests/test_ui_v2_local_processing_adapter.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_run_result_display_shell.py \
  tests/test_ui_v2_sandbox_execution_wiring.py \
  tests/test_ui_v2_workspace_folder_selection.py
→ 102 passed

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
→ 270 passed, 44 skipped
```

## 15. Generalization confirmation

- keine Hadi/SOMAA/Bismarck/AMEX/voba Pfad-Defaults  
- keine Desktop/`/Users`-Pfad-Defaults  
- kein Filename-as-truth  
- keine Fake Payment/Account/Business-Results  
- keine Fake Review-/Processing-Results (nur Stub-Boundary in Tests)  
- kein produktiver Execution-Toggle  
- kein Folder-Scan außerhalb Sandbox  
- kein Folder-Create außerhalb test-owned `tmp_path`  
- keine echte PDF-/OCR-/AI-Verarbeitung in diesem Task  
- UI-Wording generisch  
- Track A unberührt  
- Processing/Routing/Classification-Core unberührt  

## 16. Current progress

| Item | Status |
|---|---|
| Prompt 2/12 complete | **yes** |
| Remaining prompts | **10** |

## 17. Remaining gaps

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

(Live-Core-Bindung der Sandbox-Boundary / Profilpfad-Auflösung ist Teil der späteren Sandbox-/Pilot-Schritte.)

## 18. Exact next task recommendation

**`KI_RECHNUNGEN_TRACK_B_UI_V2_REVIEW_WORKFLOW_COMPLETION_01`**  
(oder nächster Masterplan-Prompt 3/12 laut PO: Review-Workflow-Vervollständigung)

Alternativ, falls PO Live-Sandbox gegen echte kopierte Fixtures priorisiert:

**`KI_RECHNUNGEN_TRACK_B_UI_V2_SANDBOX_LIVE_CORE_BRIDGE_01`** — injizierbaren Live-Runner mit Profilpfad-Auflösung nur für Sandbox-Kopien binden, ohne Track-A-/Core-Änderung soweit möglich.
