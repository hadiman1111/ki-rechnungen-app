# Core Dry-Run No-Mutation Implementation

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01`  
Masterplan: Prompt **2/34**  
Status nach diesem Task: Core-API vorhanden; Track-B-Bridge noch nicht verdrahtet  
Nächster Task: `KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01`

## Purpose

Implementiert die im Contract definierte Core-API für einen sicheren Sandbox-Dry-Run auf **kopierten** Eingangsdaten — ohne Source-Archivierung, ohne Verschieben/Umbenennen/Löschen und ohne Schreiben außerhalb des expliziten Sandbox-Outputs.

## Implemented dry-run API

Modul: `invoice_tool/core_dry_run.py`

```text
run_core_dry_run_sandbox(request: CoreDryRunRequest) -> CoreDryRunResult
```

- Validiert den Request über `validate_core_dry_run_request`
- Liefert strukturierte Buckets + `CoreDryRunSafetyProof`
- Ruft **nicht** `invoice_tool.run.run_once` auf
- Schreibt standardmäßig **keine** Dateien (in-memory Result)

## Relationship to contract

Typen/Validation kommen aus `invoice_tool/ui_v2/core_dry_run_contract.py` (Prompt 1/34).

Der Core lädt das Contract-Modul über einen Package-Stub, damit `ui_v2.__init__` (Flet-Bootstrap) **nicht** als Side Effect der Core-API geladen wird. Die Modul-Identität bleibt `invoice_tool.ui_v2.core_dry_run_contract`, damit Prompt 3/34 dieselben Typen nutzen kann.

## Safety boundaries

| Guard | Verhalten |
|-------|-----------|
| Contract-Flags | `dry_run`, `no_mutation`, Confirmations, kein Produktivmodus |
| Pfade | explizite Input/Output, kein Same-Path, Original-Heuristik, optional `sandbox_root` |
| Source FS | Vorher/Nachher-Snapshot (Listing + Hash); bei Drift → `failed` |
| Archive | kein Anlegen von `<input>/archiv` |
| Writes | keine Dateischreibvorgänge im Default-Pfad |
| Produktiv | kein `run_once`, kein DATEV/Cloud-Export |
| Filename-as-Truth | Dateiname allein erzeugt nie `recognized` |

## What processing is real

- Scan top-level Kandidaten im kopierten Input (ohne Archive-Subtree)
- Sicheres Lesen von Textdateien (UTF-8/Latin-1)
- Marker-basierte Text-Evidenz für begrenzte `recognized`-Fälle
- PDF ohne Extraktion → `review`/`unklar`
- Unsupported/unreadable → `errors`
- `planned_destinations` als Daten unter `output_dir/geplant/...` mit `applied=false`

## What processing is intentionally limited

- Kein OCR
- Kein AI/Vision
- Kein Laden privater Default-Profile/Pfade
- Keine produktive Routing-/Archive-Pipeline von `InvoiceProcessor` / `run_once`
- Keine echten Output-Writes und keine App-Support-Run-Dirs

## What is returned

`CoreDryRunResult` mit:

- `status`: `completed` / `completed_with_review` / `failed` (Contract-Violations → Exception/`blocked` via Contract)
- `recognized` / `review` / `errors`
- `planned_destinations` (data-only)
- `summary`, `warnings`, `safety_proof`

## What is not mutated

- Source-Dateien und -Ordner
- Originalordner
- produktive Ausgaben
- DATEV/Cloud
- Track-A-/Internal-App-Verhalten

## Track A preservation

Bestehende Core-Dateien unverändert:

- `invoice_tool/run.py`
- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`

`run_once` bleibt Default- und Produktivpfad für Track A. Dry-Run ist nur über die neue API aktiv.

## Tests

- `tests/test_core_dry_run_no_mutation.py` — Mutation-/Bucket-/Safety-Proof
- `tests/test_ui_v2_core_dry_run_contract.py` — Contract-Regression
- `tests/test_track_a_internal_app_protection.py` — Track-A-Schutz

## Remaining limitation before local pilot

Track B muss diese API in Prompt **3/34** über die Core-Bridge / Sandbox-Execution-Boundary aufrufen und auf `ProcessingRunState` mappen. Solange das fehlt: **kein** Local-Pilot-Ready.
