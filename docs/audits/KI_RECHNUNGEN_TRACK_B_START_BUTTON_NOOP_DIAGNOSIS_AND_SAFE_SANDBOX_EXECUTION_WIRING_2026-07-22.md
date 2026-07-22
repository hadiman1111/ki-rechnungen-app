# KI-Rechnungen Track B — Start-Button No-Op Diagnosis & Safe Sandbox Execution Wiring

**Datum:** 2026-07-22  
**Task ID:** `KI_RECHNUNGEN_TRACK_B_START_BUTTON_NOOP_DIAGNOSIS_AND_SAFE_SANDBOX_EXECUTION_WIRING_01`

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_START_BUTTON_NOOP_DIAGNOSIS_AND_SAFE_SANDBOX_EXECUTION_WIRING_01`

## 2. User observation

Der Nutzer legt kopierte Dateien in den Inbox-/Test-Eingangsordner. In Track-B UI-v2 ist der sichtbare Start-/Sandbox-Button klickbar, aber es passiert nichts Sichtbares. Das blockiert den manuellen Pilottest.

## 3. Diagnosis of no-op cause

Ursache (kombiniert):

1. **Live-UI nutzte standardmäßig `NotYetConnectedProcessingService`** — der Click führte zwar `start_run` aus, lieferte aber nur einen Adapter-Block mit Text, der bereits als Idle-/Readiness-Hinweis sichtbar war.
2. **Sandbox-Intent war nie gesetzt** (`workspace_sandbox_mode=False`, kein `sandbox_root`, `copied_data_confirmed=False`) — selbst mit `LocalProcessingAdapter` hätte der Gate-Pfad nicht greifen können.
3. **CTA-Feedback lag nicht am Button** — Statusänderungen steckten in entfernten Hint-Blöcken und enthielten weiterhin Formulierungen wie „Kein Lauf gestartet“, sodass der Click wie ein No-Op wirkte.
4. **Echte Core-Ausführung ist unbound** — `sandbox_core_runner` ist absichtlich nicht an OCR/AI/`run_once` gebunden (`CORE_BRIDGE_REQUIRED_FOR_REAL_SANDBOX_EXECUTION`).

## 4. Click path before fix

1. Sichtbarer Button: Accent-CTA „Verarbeitung starten“ in `make_workspace_run_panel`
2. `on_click` → `_schedule_start_processing` → `apply_start_processing` → `refresh()`
3. `apply_start_processing` baute Request ohne Sandbox-Intent
4. Default-Service: `NotYetConnectedProcessingService.start_run` → `blocked` mit Adapter-Text
5. UI aktualisierte Hints, aber ohne klare CTA-nahe Rückmeldung → subjektiver No-Op

## 5. Click path after fix

1. Sichtbarer Button: Accent-CTA **„Sandbox-Lauf starten“**
2. `on_click` → `_schedule_start_processing` → `apply_start_processing` → `refresh()`
3. `prepare_sandbox_intent_for_cta`: setzt Sandbox-Modus, Kopie-Bestätigung, leitet `sandbox_root` aus Eingang/Ausgang ab
4. Live-App injiziert `LocalProcessingAdapter` (`app.build_ui_v2`)
5. Adapter validiert → Sandbox-Gate → Execution-Boundary (Default unbound)
6. `build_start_button_feedback` schreibt immer sichtbaren deutschen Status
7. Workspace zeigt `summary_alert` direkt über dem Run-Panel („Sandbox-Start“)

## 6. Whether real sandbox execution is wired or blocked

**Teilweise verdrahtet, echte Verarbeitung blockiert.**

- Sandbox-Gate + LocalProcessingAdapter + Execution-Boundary sind im Live-Click-Pfad aktiv.
- Stub-/Test-Runner können einen abgeschlossenen Sandbox-Lauf liefern.
- Default-Runner bleibt unbound → keine OCR/AI/Core-Verarbeitung.

## 7. If blocked, exact blocker

`CORE_BRIDGE_REQUIRED_FOR_REAL_SANDBOX_EXECUTION`

Sichtbarer CTA-Text u. a.:

- „Sandbox-Ausführung ist noch nicht mit der Verarbeitung verbunden.“
- „Sandbox-Lauf blockiert: Die echte Verarbeitung ist in Track B noch nicht sicher verbunden.“

## 8. UI feedback behavior

Nach jedem Klick immer einer dieser sichtbaren Zustände:

- gestartet / abgeschlossen (nur mit injiziertem Stub-Runner)
- blockiert mit Grund (Ordner / Profil / Konfiguration / produktiv / Core-Bridge)
- fehlgeschlagen mit Fehler

Zusätzliche Klartexte:

- „Keine Originalordner wurden verwendet.“
- „Ergebnisse erscheinen hier nach einem erfolgreichen Sandbox-Lauf.“

## 9. Files changed

- `invoice_tool/ui_v2/app.py` — injiziert `LocalProcessingAdapter`
- `invoice_tool/ui_v2/state.py` — `workspace_start_feedback`
- `invoice_tool/ui_v2/pages/workspace.py` — CTA-Wiring, Feedback, Sandbox-Intent
- `invoice_tool/ui_v2/sandbox_execution_boundary.py` — klarere Unbound-Meldung
- `invoice_tool/ui_v2/sandbox_processing_gate.py` — Originalpfad optional nach Kopie-Bestätigung
- `tests/test_ui_v2_start_button_noop_and_sandbox_wiring.py` — neu
- dieses Audit-Dokument

## 10. Tests run and results

Fokussiert:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_start_button_noop_and_sandbox_wiring.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_sandbox_execution_wiring.py \
  tests/test_ui_v2_copied_real_data_validation.py \
  tests/test_ui_v2_product_v1_release_gate.py
→ 88 passed
```

Vollständige Track-B UI-v2 Suite:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
→ 439 passed, 44 skipped
```

## 11. Confirmation: no Track A change

Track-A-geschützte Dateien wurden nicht geändert. Bekannte Legacy-Dirty-Dateien (`ui_profile_dialog.py`, `ui_document_rules.py`) bleiben unstaged.

## 12. Confirmation: no processing-core change

Keine Änderungen an `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, `run.py`. Keine neuen Core-Imports in UI-v2.

## 13. Confirmation: no productive processing

`productive_execution_allowed=False`, `dry_run=True`, produktive Gates bleiben blockiert.

## 14. Confirmation: no original folders touched

Keine Originalordner als Input/Output an die Execution-Boundary; CTA-Feedback bestätigt „Keine Originalordner wurden verwendet.“

## 15. Manual next test instruction

1. Track-B UI-v2 starten (`app_ui_v2.py` / bestehender UI-v2-Launcher).
2. Explizit kopierten Eingangsordner und Ausgangsordner unter derselben Sandbox-Wurzel wählen.
3. Profil/Konfiguration wählen, falls gefordert.
4. „Sandbox-Lauf starten“ klicken.
5. Erwartung: sichtbarer Status über dem Button (blockiert mit Core-Bridge-Hinweis **oder** Ergebnis nach Stub), niemals stiller No-Op.
6. Keine Originalordner wählen; keine produktive Verarbeitung erwarten.

Release-Tag unverändert: `product-v1-local-pilot-2026-07-22`
