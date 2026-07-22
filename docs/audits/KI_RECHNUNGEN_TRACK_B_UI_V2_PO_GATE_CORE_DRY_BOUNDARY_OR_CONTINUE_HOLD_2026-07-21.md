# KI-Rechnungen Track B UI-v2 — PO Gate: Core Dry Boundary or Continue Hold

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_PO_GATE_CORE_DRY_BOUNDARY_OR_CONTINUE_HOLD_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Core Dry Boundary PO Gate

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_PO_GATE_CORE_DRY_BOUNDARY_OR_CONTINUE_HOLD_01`

## 2. Purpose

Product-Owner-Entscheidungspaket: klären, ob der nächste Implementierungsschritt

- **OPTION A** — UI-v2 Hold / Readiness only,
- **OPTION B** — minimale sichere Core dry/no-mutation Compatibility Boundary, oder
- **OPTION C** — spätere produktive lokale Track-B-Ausführung

sein soll — und wie Track B möglichst schnell funktional wird, **ohne** Track A oder reale Rechnungsdaten zu gefährden.

Dieses Task ist **nur** Entscheidungsvorbereitung und Risiko-Boundary-Definition:

- keine Core-Implementierung
- keine produktive Verarbeitung
- keine PDF-Verarbeitung
- keine Mutation realer Rechnungsordner
- kein Track-A-Touch
- keine Code-Änderung außer diesem Audit-Dokument

## 3. Current Track A state

Track A bleibt intern/lokal und geschützt:

| Entry | Rolle | Status |
|---|---|---|
| `app_main.py` | Standalone / interne lokale App → `invoice_tool.gui` | vorhanden, unberührt |
| `app_internal_launcher.py` | Interner SOMAA-Launcher → `invoice_tool.internal_launcher` | vorhanden, unberührt |

Track-A-Abhängigkeiten (read-only):

- bestehende productive Core-Pipeline über `invoice_tool.run.run_once` / `InvoiceProcessor`
- Legacy-GUI und interner Launcher
- keine privaten Defaults dürfen in Track B wandern; Track A bleibt getrennt

Known Legacy-UI dirty files bleiben lokal und unstaged (nicht processing-core):

- `invoice_tool/ui_profile_dialog.py` (modified)
- `invoice_tool/ui_document_rules.py` (untracked)

## 4. Current Track B UI-v2 readiness

Readiness-Block ist abgeschlossen (Score-Schätzung **78 / 100**):

| Bereich | Status |
|---|---|
| Workspace / Configurations / Profiles / Review / Settings | vorhanden |
| Policy Editor Controls | vorhanden |
| Explizite Input-/Output-Folder-State | vorhanden |
| `LocalProcessingAdapter` | vorhanden |
| `ProcessingRunState` / Result Display Shell | vorhanden |
| Keine Fake-Results | enforced |
| Keine PDF-Verarbeitung | enforced |
| Keine Mutation realer Rechnungsordner | enforced |
| Processing-Core | unberührt |
| Dry/no-mutation Start | **blocked** — `unsupported_without_core_change` / `CORE_DRY_GATE_REQUIRES_CORE_CHANGE` |

`LocalProcessingAdapter.validate_request` kann logisch `ready` erreichen.  
`start_run` mit `dry_run=True` endet ehrlich blockiert in `_run_core_dry_no_mutation` ohne Core-Import.

## 5. Why Track B is not yet functional

Track B ist **UI-/Contract-fertig**, aber **nicht verarbeitend funktional**, weil:

1. Der Adapter bewusst keinen Core aufruft, solange kein sicherer Dry-Pfad existiert.
2. `invoice_tool.run.run_once` hat **keinen** `dry_run` / `no_mutation`-Modus.
3. Ein Track-B-Wrapper um `run_once` würde immer Snapshots, Output-Writes, Archive und Reports auslösen.
4. Fake-Results sind verboten — ohne echten Dry-Pfad bleiben Results leer und Starts blockiert.

Funktionslücke = **Core dry/no-mutation Boundary fehlt**, nicht UI-Shell.

## 6. Core dry/no-mutation gap

Read-only Inspection von `run.py` / `processing.py` / Routing / Classification:

| Frage | Befund |
|---|---|
| Primärer Entrypoint | `run_once(source, output, *, config_path=None, rules_path=None, profile_path=None) -> Path` |
| Dry/no-mutation Parameter | **fehlt** |
| Validate-only ohne Write | **kein** öffentlicher Modus |
| Ergebnis-Summary ohne Output-Write | **nein** — Pipeline endet in Publish/Archive/Mapping/Report |
| Trennung Extract/Classify/Route vs Write | Module getrennt, Orchestrierung aber write-eingebettet |

`run_once` macht immer u. a.:

1. Source-PDF-Discovery  
2. Application-Support Run-Dir + `input_snapshot` (`shutil.copy2`)  
3. `documents`-Output `mkdir`  
4. `InvoiceProcessor.process_all()`  
5. Output-Copy/Rename, Archive-Move, Mapping-/Report-/Trace-Writes  

**Gap-Klassifikation:** `CORE_DRY_GATE_REQUIRES_CORE_CHANGE`

## 7. Required no-mutation boundary

Minimal benötigte Boundary (für eine spätere Implementierungsaufgabe, **nicht** in diesem Task):

1. Explizites `dry_run` / `no_mutation` am Core-Entrypoint (oder dedizierter Dry-Entrypoint)
2. Default **aus** (`dry_run=False`) → Track-A-/CLI-Verhalten unverändert
3. Bei `dry_run=True`: alle persistierenden Side Effects aus §8 blockieren
4. Optional: In-Memory-/Return-Summary für Klassifikation/Route-Intent ohne Dateischreiben
5. UI-v2 Adapter darf Core erst aufrufen, wenn `core_dry_run_status == dry_run_available`
6. Keine privaten Defaults; nur explizite User-Pfade / Synthetic-Temp-Tests

### Machbarkeits-Klassifikation (ohne Implementierung)

| Ansatz | Bewertung |
|---|---|
| Wrapper-only (nur Track B) | **unsicher / ungeeignet** — Side Effects stecken im Core |
| Kleiner Core-Shim (`dry_run=False` Default + Write-Gates) | **machbar** — bestes Risiko/Fortschritt-Verhältnis |
| Größerer Refactor (Extract/Classify/Route vs Write trennen) | möglich, aber langsamer und größerer Blast Radius |

Inspection belegt **nicht**, dass selbst ein kleiner Dry-Boundary unsicher wäre — vorausgesetzt Default bleibt productive/off und Tests erzwingen No-Mutation + Track-A-Regression.

## 8. Side effects to block

Für Dry/no-mutation müssen **mindestens** blockiert werden:

| Side Effect | Beobachtung (read-only) | Dry block |
|---|---|---|
| File copy (Output) | `InvoiceProcessor._write_active_output` → `shutil.copy2` | ja |
| File move / Archive | `_publish_and_archive` / `_archive_original` / `archive_original_safely` → `shutil.move` | ja |
| Rename von Outputs | Publish-Pfad-Naming + Write | ja |
| Archive write unter Input | `<input>/archiv/<run-id>/` | ja |
| Output folder / `documents` creation | `run_once` → `documents_basis.mkdir` | ja (oder nur ephemeral Temp unter Test-Policy) |
| Report write | `write_run_report` / `write_text` Reports | ja |
| Mapping write | `OutputMappingStore.flush` / `_write_output_mapping` | ja |
| Persistent Trace/Log write | `TraceWriter.flush`, App-Support Logs | ja (oder strikt temp + Cleanup, PO-scoped) |
| Input snapshot copy in User-Pfade | `create_run_snapshot` | ja gegen User-Ordner; Temp nur mit Cleanup |

Produktive Ausführung zusätzlich: Backup/Rollback + Test-Folder-only — **nicht** jetzt.

## 9. Options A / B / C

### OPTION A — Continue UI-v2 Hold

- Weiter nur UI-/Readiness-Arbeit
- Kein Core-Change
- **Risiko:** niedrigst
- **Pfad zu funktionalem Track B:** langsam — Verarbeitung bleibt blockiert

### OPTION B — Core Dry Boundary Shim

- Spätere Implementierungsaufgabe: minimale dry/no-mutation Compatibility Boundary
- Track A Default-Verhalten unverändert (`dry_run` off)
- Keine realen Rechnungsordner; nur Synthetic/Temp-Tests
- Keine produktive Track-B-Ausführung in dem nächsten Task
- **Risiko:** mittel (shared Core), aber mit Default-off + Tests beherrschbar
- **Pfad zu funktionalem Track B:** schnellster sicherer Fortschritt

### OPTION C — Productive Track-B Execution Gate

- Später echte lokale Verarbeitung erlauben
- Erfordert zuvor Dry-Run oder sehr starke Backup/Rollback-Schutzmaßnahmen
- **Risiko:** höchst
- **Nicht empfohlen** jetzt

## 10. Recommended option

**OPTION B — Core Dry Boundary Shim**

## 11. Reason for recommendation

1. UI-v2 Readiness ist substantiell fertig (~78/100); weiteres Hold liefert wenig Funktionsgewinn.
2. Wrapper-only ist unsicher — Gap sitzt im Core (`run_once` / `InvoiceProcessor`).
3. Ein kleiner Shim mit Default `dry_run=False` kann Track A schützen und Track B einen ehrlichen Dry-Pfad geben.
4. Inspection zeigt keinen Zwang zu einem großen Refactor als Einstieg.
5. OPTION C ohne Dry-Pfad würde reale Ordner Copy/Move/Archive/Report-Risiken aussetzen.

Daher: nächster Schritt = geschützte Core-Dry-Boundary-Implementierung — **nicht** produktive Ausführung.

## 12. Product Owner decision required

**Yes.**

PO muss explizit wählen:

- **A** Continue Hold, oder
- **B** Core Dry Boundary Shim freigeben (empfohlen), oder
- **C** Productive Execution Gate (nicht empfohlen jetzt)

Dieses Audit allein autorisiert **keine** Core-Implementierung und **keine** produktive Ausführung.

## 13. Exact next task

`KI_RECHNUNGEN_CORE_DRY_RUN_COMPATIBILITY_SHIM_PROTECTED_IMPLEMENTATION_01`

Scope (nur nach PO-Freigabe Option B):

- minimale dry/no-mutation Compatibility Boundary implementieren
- Track-A-Default-Verhalten erhalten
- Synthetic/Temp-only Tests
- keine realen Rechnungsordner
- keine produktive Track-B-Ausführung
- keine privaten Defaults

Kein vollständiger Implementierungs-Prompt in diesem Audit.

## 14. Track A protection requirements

Für den nächsten Task (falls Option B):

- `app_main.py` / `app_internal_launcher.py` nicht ändern
- `run_once`-Default ohne Dry-Flag = heutiges produktives Verhalten
- Track-A-Regressionstests vor Merge
- keine privaten SOMAA/Desktop-Defaults in Core oder UI-v2
- Legacy-UI dirty files nicht „mitaufräumen“ / nicht committen
- Kein Import/Call von produktivem Core aus UI-v2 außer über freigegebenen Dry-Pfad

## 15. Tests required for next task

Vor jeder Core-Änderung verpflichtend:

1. **Track-A-Regression** — Default-Pfad unverändert  
2. **No-mutation Tests** — `dry_run=True` schreibt/moved/copied nichts in User-/Output-/Archive-Pfade  
3. **Synthetic temp folder tests** — nur TemporaryDirectory / Fixture-Ordner  
4. **Real invoice folder exclusion tests** — bekannte private/real Pfade dürfen nicht verwendet werden  
5. **No private defaults tests** — keine hardcodierten privaten Pfade/Profile  

Zusätzlich: bestehende UI-v2 Adapter-/Display-Contract-Tests müssen weiter grün bleiben.

## 16. No productive processing confirmation

In diesem Task:

- kein `run_once` / `InvoiceProcessor`-Aufruf
- kein produktiver Adapter-Start
- Adapter-Gates bleiben blocked
- keine PDF-Pipeline ausgeführt

## 17. No real invoice changes confirmation

- kein Folder create/scan/write
- kein Archive/Move/Copy gegen reale Rechnungsordner
- Workspace-Folder-State bleibt UI-String only
- `profile_config.local.json` nicht in git status

## 18. Commit / push status

- Erlaubte Änderung: nur dieses Audit-Dokument
- Commit message: `docs: entscheide naechste UI-v2 Core-Dry-Grenze`
- Push nur wenn Safe Gates passen (`main`, behind=0, genau ein Commit ahead, Payload = dieses Doc only)

## Appendix — Preflight snapshot (this task)

- Worktree: `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App`
- Branch: `main`
- HEAD / origin/main (before): `51567c17bcab1ce7594ee5cef099c4dd80782c5e`
- ahead/behind (before): `0 / 0`
- Staged: empty
- Active Git operation: no
- Git locks: none
- Actual processing-core dirty: **no**
- Routing/classification dirty: **no**
- Known Legacy UI dirty: yes (unstaged, expected)
- `profile_config.local.json` in status: **no**
- Real invoice folders in status: **no**
- Track A entry: yes
- Track B entry: yes
- UI-v2 readiness audit: yes
- `LocalProcessingAdapter`: yes
- `run_result_display.py`: yes
- Initial classification: `READY_FOR_CORE_DRY_BOUNDARY_PO_GATE`

## Appendix — Optional safe tests (this task)

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_local_processing_adapter.py \
  tests/test_ui_v2_run_result_display_shell.py \
  tests/test_ui_v2_policy_editor_controls.py \
  tests/test_ui_v2_workspace_processing_contract.py
```

(Ergebnisse im Final Report; kein GUI, kein Build, keine PDFs.)
