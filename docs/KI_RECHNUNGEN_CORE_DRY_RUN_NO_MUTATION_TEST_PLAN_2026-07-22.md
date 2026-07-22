# Core Dry-Run No-Mutation Test Plan

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`  
Nächste Implementierung: `KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01`  
Contract: `docs/KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_2026-07-22.md`

## Zweck

Definiert die Testmatrix, die **vor** jedem als „sicher“ geltenden echten Sandbox-Dry-Run bestehen muss. Prompt 1 deckt Contract-/Validation-Tests ab; Prompt 2 muss Mutation-/Parity-Tests ergänzen.

## Test matrix

| # | Bereich | Prompt 1 (jetzt) | Prompt 2 (Implementierung) | Prompt 3 (Bridge-Wiring) |
|---|---------|------------------|----------------------------|--------------------------|
| 1 | Request-Validation | Pflicht | Regression | Regression |
| 2 | Path-Safety | Heuristik string-only | + tmp sandbox FS | Bridge-Integration |
| 3 | Mutation prevention | Contract flags | Harte FS-Beweise | Kein `run_once`-Produktivpfad |
| 4 | Result mapping | Bucket-Shape | Mapping aus Core | Mapping → UI-State |
| 5 | Review/Error separation | Datenmodell | Core-Ausgabe | Workspace-Anzeige |
| 6 | Output-only artifacts | Policy | FS unter `output_dir` | Export-Preview aus Lauf |
| 7 | Original non-mutation proof | SafetyProof-Felder | Vorher/Nachher-Hash/Listing | Bridge bestätigt |
| 8 | Track-A regression | Protection gate | Protection gate | Protection gate |
| 9 | Full UI-v2 suite | nach Contract | nach Core-API | nach Wiring |

## Path safety tests

Bereits in Prompt 1 (`tests/test_ui_v2_core_dry_run_contract.py`):

- fehlende Input/Output → Reject
- gleicher Input/Output → Reject
- Desktop-/Invoice-/SOMAA-ähnliche Pfade → Reject
- optional `sandbox_root`: außerhalb → Reject

Prompt 2 muss ergänzen:

- kopierter tmp-Inbox unter Sandbox akzeptiert
- Original-Pfad (explizit gesetzt) nie als Input akzeptiert
- Symlink-/Resolve-Fälle, soweit sicher testbar ohne echte Privatordner

## Mutation prevention tests

Prompt 2 Pflicht:

1. Source-Listing vor/nach Dry-Run identisch (keine Moves/Renames/Deletes)
2. kein `<source>/archiv/...`-Eintrag
3. keine Schreibvorgänge außerhalb `output_dir` / erlaubter Sandbox-Artefaktzone
4. kein Application-Support-Run-Dir außerhalb Sandbox-Policy
5. `planned_destinations[*].applied is False`
6. Produktivflags bleiben `false`

## Result mapping tests

Prompt 1: Bucket-Shape (recognized / review / errors / planned_destinations / summary).

Prompt 2: Core liefert echte Bucket-Inhalte aus Sandbox-Kopien (ohne Fake-Zeilen in der Bridge).

Prompt 3: Bridge mappt auf `ProcessingRunState` / Export-Reporting ohne Erfindungen.

## Review / error separation tests

- Review-Items ≠ Error-Items ≠ Recognized
- Summary-Zähler stimmen mit Listenlängen überein
- `completed_with_review`, wenn Review > 0 und keine harten Failures den Lauf killen (Semantik Prompt 2 festlegen und testen)

## Output-only artifact tests

- erlaubte Dateien nur unter Sandbox-`output_dir`
- Source-Ordner unverändert
- keine stillen Writes in `~/Library/Application Support/KI-Rechnungen/...` außer explizit im Prompt-2-Contract erlaubt und getestet

## Original-folder non-mutation proof

Jeder „sichere“ Lauf muss `CoreDryRunSafetyProof` liefern mit:

- `no_original_mutation`
- `no_source_archive` / `no_source_rename` / `no_source_delete` / `no_source_move`
- `writes_confined_to_sandbox_output`
- `planned_destinations_not_applied`
- `evidence_notes` (mindestens technische Belegstrings)

Zusätzlich Prompt 2: Dateisystem-Beweis in Tests (Listing/Hash).

## Track-A regression tests

Immer:

```bash
.venv/bin/python -m pytest tests/test_track_a_internal_app_protection.py
```

Zusätzlich: keine Änderungen an geschützten Track-A-/Core-Dateien außer im explizit freigegebenen Prompt-2-Scope für Dry-Run-API.

## Full UI-v2 integration tests (nach Implementierung)

Nach Prompt 2 und erneut nach Prompt 3:

```bash
.venv/bin/python -m pytest \
  tests/test_ui_v2_core_dry_run_contract.py \
  tests/test_ui_v2_core_bridge_sandbox_dry_run_parity.py \
  tests/test_ui_v2_*.py \
  tests/test_saas_ui_v2_*.py \
  tests/test_track_a_internal_app_protection.py
```

Zusätzliche Prompt-2-Dateien (Namen vorschlagsweise):

- `tests/test_core_dry_run_no_mutation_fs_proof.py`
- `tests/test_core_dry_run_result_buckets.py`

## Prompt-1 Ist-Stand (dieser Task)

Ausgeführt / gefordert:

```bash
.venv/bin/python -m pytest \
  tests/test_ui_v2_core_dry_run_contract.py \
  tests/test_track_a_internal_app_protection.py

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py

git diff --check
```

Nicht ausführen in Prompt 1:

- GUI
- echte PDF-Verarbeitung
- OCR/AI
- Builds
- Originalordner-Scans
