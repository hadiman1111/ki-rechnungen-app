# Core Dry-Run Sandbox API Contract

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`  
Masterplan: Prompt 1/34  
Status: `NOT_LOCAL_PILOT_READY_CORE_DRY_RUN_API_REQUIRED`  
Contract-Modul: `invoice_tool/ui_v2/core_dry_run_contract.py`

## Purpose

Definiert den verbindlichen API-Vertrag für einen sicheren Core-Dry-Run-/No-Mutation-Sandbox-Lauf, damit Track B echte kopierte PDFs verarbeiten kann, ohne Source-Ordner, Archive oder produktive Exporte zu mutieren.

## Why needed

Track B (UI-v2) hat Path B gewählt: die bestehende Core-Bridge importiert den Processing-Core bewusst nicht, weil `invoice_tool.run.run_once` kein Dry-Run-/No-Mutation-Verhalten bietet. Ohne diesen Vertrag ist kein lokaler Pilot akzeptabel.

## Current blocker

| Fakt | Bedeutung |
|------|-----------|
| `run_once` schreibt Outputs | Mutiert Ausgabeordner |
| `run_once` archiviert Quellen | `shutil.move` nach `<source>/archiv/<run-id>/` |
| App-Support-Artefakte | `~/Library/Application Support/KI-Rechnungen/runs/...` |
| Kein `dry_run`/`no_mutation`-Parameter | Keine sichere Preview-API |
| Bridge-Status | `requires_core_dry_run_contract` |

## API contract

Geplante Core-API (Implementierung = Prompt 2/34):

```text
validate_core_dry_run_request(request) -> CoreDryRunRequest
run_core_dry_run_sandbox(request) -> CoreDryRunResult   # Prompt 2
```

Aktuell in Track B vorhanden (nur Contract/Typen/Validation):

- `CoreDryRunRequest`
- `CoreDryRunResult` (+ Buckets)
- `CoreDryRunSafetyPolicy` / `CoreDryRunSafetyProof`
- `validate_core_dry_run_request(...)`
- `build_core_dry_run_contract_requirements(...)`

## Request model

`CoreDryRunRequest` muss mindestens enthalten:

| Feld | Pflicht | Semantik |
|------|---------|----------|
| `input_dir` | ja | nur kopierter Sandbox-Eingang |
| `output_dir` | ja | expliziter Sandbox-Ausgabeordner |
| `profile_id` **oder** `profile_name` | ja | kein privater Default |
| `configuration_id` **oder** `configuration_name` | ja | kein privater Default |
| `dry_run` | `true` | sonst Reject |
| `no_mutation` | `true` | sonst Reject |
| `copied_data_confirmation` | `true` | sonst Reject |
| `original_folder_exclusion_confirmation` | `true` | sonst Reject |
| `productive_mode_requested` | `false` | sonst Reject |
| `run_id` | optional | Caller-/Bridge-ID |
| `sandbox_root` | optional, empfohlen | wenn gesetzt: Input/Output müssen darunter liegen |
| Safety-Flags | `true` | `no_move_originals`, `no_archive_source`, `no_rename_source`, `no_delete_source`, `no_write_outside_sandbox` |

Validation lehnt ab:

- fehlende Input/Output-Pfade
- identische Input/Output-Pfade
- `dry_run=false`, `no_mutation=false`, Produktivmodus
- fehlende Confirmations
- fehlendes Profil/Konfiguration
- originalähnliche Desktop-/Invoice-/SOMAA-/AMEX-Pfade (Heuristik, string-only)
- Pfade außerhalb `sandbox_root` (wenn gesetzt)

## Result model

`CoreDryRunResult`:

| Feld | Inhalt |
|------|--------|
| `status` | `blocked` / `ready` / `completed` / `completed_with_review` / `failed` |
| `run_id` | Lauf-ID |
| `recognized` | erkannte Dokumente |
| `review` | unklare/Prüffälle |
| `errors` | Fehlerfälle |
| `planned_destinations` | nur Daten, `applied=false` |
| `summary` | Zähler |
| `warnings` | Warnungen |
| `safety_proof` | No-Mutation-Beweis |
| `contract_error_codes` | bei Blockierung vor Verarbeitung |

Trennung recognized / review / errors ist verpflichtend. Geplante Ziele sind **keine** durchgeführten Moves.

## Safety policy

`CoreDryRunSafetyPolicy` erzwingt:

- `dry_run = true`
- `no_mutation = true`
- `no_move_originals`
- `no_archive_source`
- `no_rename_source`
- `no_delete_source`
- `no_write_outside_sandbox`
- kein Produktivmodus
- kein echter DATEV-/Cloud-Export
- keine privaten Defaults
- kein Filename-as-Truth
- App-Support-Nebenwirkungen außerhalb Sandbox verboten
- planned destinations nur data-only

## Forbidden mutations

Der Dry-Run darf **nicht**:

1. Source-PDFs verschieben, umbenennen, löschen oder archivieren
2. Originalordner anfassen
3. außerhalb des Sandbox-Output schreiben
4. produktiven Modus aktivieren
5. echten DATEV-/Cloud-Export ausführen
6. private Default-Pfade/Profile implizieren
7. Dateiname als Wahrheitsquelle nutzen
8. technische Artefakte unter Application Support außerhalb einer expliziten Sandbox-Policy anlegen (Prompt-2-Pflicht)

## Allowed sandbox artifacts

Nur unter `output_dir` (Sandbox):

- strukturierte Result-Payloads / Reports
- optionale Dry-Run-Evidence-Dateien
- geplante Destination-Records (Daten, nicht Moves)

Keine Source-Archivierung. Keine Original-Mutation.

## Track-B integration expectations

Erwarteter Aufrufpfad nach Prompt 2/3:

```text
Workspace CTA
  → sandbox_execution_boundary / LocalProcessingAdapter
  → core_bridge (Path B heute: requires_core_dry_run_contract)
  → run_core_dry_run_sandbox(request)   # Prompt 2
  → map CoreDryRunResult → ProcessingRunState / Export-Preview
```

Bis Prompt 2 bleibt die Bridge auf Path B und erfindet keine Result-Zeilen.

## Processing-core implementation expectations (next prompt)

Prompt 2/34 `KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01` muss:

1. eine Core-API gemäß diesem Contract implementieren
2. `run_once` produktiv unverändert lassen (Track A)
3. Source-No-Mutation beweisen (Tests)
4. recognized/review/errors + planned_destinations liefern
5. Safety-Proof zurückgeben
6. keine OCR/AI gegen Originalordner und keinen Produktivexport freischalten

## Acceptance criteria

- [x] Contract-Typen unter `invoice_tool/ui_v2/core_dry_run_contract.py`
- [x] Request-Validation für alle Pflicht-Rejects
- [x] Result-Buckets + Safety-Proof modelliert
- [x] Contract-/Testplan-/Audit-Docs vorhanden
- [x] Tests ohne Processing-Core-Import
- [x] keine Processing-Core-Änderung in diesem Prompt
- [x] keine Track-A-Änderung
- [x] keine produktive / echte Rechnungsverarbeitung
- [ ] Prompt-2-Implementierung (nächster Task)
