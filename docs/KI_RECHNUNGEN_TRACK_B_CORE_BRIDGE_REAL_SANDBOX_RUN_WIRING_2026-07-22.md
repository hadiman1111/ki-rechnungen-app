# Track-B Core Bridge Real Sandbox Run Wiring

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01`  
Masterplan: Prompt **3/34**  
Produktstatus nach diesem Task: `CORE_DRY_RUN_WIRED_IN_TRACK_B_PENDING_RESULT_MAPPING_GATE`  
Nächster Task: `KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_01`

## Purpose

Verdrahtet die Track-B UI-v2 Core Bridge mit der sicheren Core-Dry-Run-API aus Prompt 2/34, sodass „Sandbox-Lauf starten“ echte Dry-Run-Ergebnisse liefert — ohne Originalmutation und ohne produktive Verarbeitung.

## What changed

- `core_bridge.py` ruft `run_core_dry_run_sandbox(CoreDryRunRequest)` auf
- `sandbox_execution_boundary.py` mappt Bridge-Ergebnisse inkl. Counts/Warnings/Safety
- `local_processing_adapter.py` meldet `dry_run_available`
- Workspace zeigt „Prüfung läuft …“ und echte Abschluss-/Prüf-/Fehlerstatus
- Export/Reporting bleibt Preview-only, kann aber echte Dry-Run-States spiegeln

## Bridge behavior

Pfad:

```text
Workspace CTA
  → LocalProcessingAdapter.start_run
  → sandbox gate
  → sandbox_core_runner
  → run_core_bridge_sandbox_dry_run
  → run_core_dry_run_sandbox
  → ProcessingRunState
```

## Request construction

`CoreDryRunRequest` aus validierter Bridge-Anfrage:

| Feld | Wert |
|------|------|
| `input_dir` / `output_dir` | kopierter Sandbox-Eingang / expliziter Sandbox-Ausgang |
| `profile_id` / `configuration_id` | aufgelöste Workspace-Auswahl |
| `dry_run` | `true` |
| `no_mutation` | `true` |
| `copied_data_confirmation` | `true` nur nach Sandbox-/Copy-Policy |
| `original_folder_exclusion_confirmation` | `true` nur nach Boundary/Gate |
| `productive_mode_requested` | `false` |
| `run_id` | optional generiert |

## Safety gates

Vor dem Core-Aufruf:

- Input/Output müssen existieren und Ordner sein
- gleicher Input/Output → Blocker
- originalähnliche Pfade → Blocker
- fehlendes Profil/Konfiguration → Blocker
- Produktivmodus → Blocker
- außerhalb Sandbox-Root → Blocker

Bei Ablehnung: kein Core-Call, kompakter Blocker, keine Fake-Ergebnisse.

## Result mapping

`CoreDryRunResult` → `CoreBridgeResult` → `ProcessingRunState`:

- Status, Run-ID
- recognized / review / error counts
- planned destinations (data-only)
- warnings
- Safety-Proof-Compact: `Originale unverändert · Produktiv gesperrt · Export Vorschau`

Keine erfundenen Erkennungszeilen. PDFs ohne OCR/AI bleiben ehrlich in Prüfung.

## Workspace behavior

Nach Klick:

1. „Prüfung läuft …“
2. sicherer Bridge-Call
3. final: abgeschlossen / mit Prüffällen / fehlgeschlagen / kompakter Blocker
4. Counts + Safety-Proof
5. kein Fake-Success

## Export/reporting limitation

Export bleibt Preview-only (`preview=true`, kein DATEV/Cloud).  
Wenn ein realer Dry-Run-State vorliegt, kann die Vorschau ihn spiegeln (`sourced_from_real_dry_run`).  
Tiefere Export-Parity → Prompt 5/34.

## What remains for Prompt 4/34 and Prompt 5/34

- Prompt 4/34: tieferes Result-Mapping und Review-Flow
- Prompt 5/34: Export/Reporting-Parity
- Prompt 6/34: Local-Pilot Acceptance Gate (`LOCAL_PILOT_READY`)

## Why local pilot is still pending acceptance

Core-Dry-Run ist in Track B verdrahtet, aber Review-UX, Export-Parity und Acceptance-Gate stehen noch aus. Kein Anspruch auf Local-Pilot-Ready oder SaaS-Ready.

## Tests

Neu: `tests/test_ui_v2_core_bridge_real_sandbox_run_wiring.py`  
Aktualisiert: Parity-, Workspace-, Adapter-, Start-Button- und Gate-Tests.

Focused + full UI-v2 Suite grün; `git diff --check` clean.
