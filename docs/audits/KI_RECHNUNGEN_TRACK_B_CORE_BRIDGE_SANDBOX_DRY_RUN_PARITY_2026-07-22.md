# KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_SANDBOX_DRY_RUN_PARITY_2026-07-22

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_SANDBOX_DRY_RUN_PARITY_01`

## 2. User observation

Track-B UI-v2 workspace correctly showed after manual test:

- „Sandbox nicht verbunden: Die echte Verarbeitung ist in Track B noch nicht sicher angebunden.“
- Details: keine Originalordner, produktive Verarbeitung gesperrt, Export bleibt Vorschau, Core-Bridge fehlt, Konfiguration American Express

Configuration selection was already fixed; remaining blocker was the missing safe Core bridge.

## 3. Diagnosis

Track B already had:

- sandbox path gate
- sandbox execution boundary
- LocalProcessingAdapter with injectable runner
- workspace CTA feedback for unbound runner

Default runner was unbound on purpose. Processing-core entry point used by Track A / internal app is `invoice_tool.run.run_once(source, output, *, config_path, profile_path)`.

## 4. Internal processing entry points found

| Entry point | Role |
|---|---|
| `invoice_tool.run.run_once` | Primary API (Track A GUI + CLI) |
| `python -m invoice_tool.run` | Internal launcher subprocess |
| `InvoiceProcessor.process_all` | Low-level processor after run setup |
| `create_run_snapshot` | Copy PDFs into technical snapshot |

Track A (`invoice_tool.gui`) and the internal launcher both call `run_once` / CLI wrapping `run_once`.

## 5. Dry-run / no-mutation capability assessment

**Existing core does NOT support dry-run / no-mutation.**

Evidence:

- No `dry_run`, `preview`, `simulate`, or `apply` parameter on `run_once` / `InvoiceProcessor`
- Every run: creates App Support run dir, copies snapshot, writes outputs, may `shutil.move` source files into `<source>/archiv/<run-id>/`, persists state/mapping/logs
- Snapshot protects user originals only when `source` is already a copy; it does not provide a no-mutation preview mode
- Track-B `ProcessingRunRequest.dry_run=True` is adapter/gate semantics only — not passed to core

Additional blockers for a live Path-A wire without core change:

- SaaS `profile_id` / `configuration_id` ≠ core `profile_path` / `invoice_config.json`
- Technical artifacts land outside sandbox root (`~/Library/Application Support/KI-Rechnungen/runs/...`)
- OCR/AI side effects

## 6. Chosen implementation path

**Path B — CORE DRY-RUN CONTRACT REQUIRED**

Safe real core execution was not wired.

## 7. Path A (not chosen)

N/A — would have required a core dry/no-mutation or sandbox-confined API.

## 8. Path B — missing core contract

Exact missing contract:

```text
CORE_API_DRY_RUN_CONTRACT_REQUIRED

Needed (conceptual):
- dry_run / no-mutation mode OR dedicated run_preview / run_sandbox
- no archive moves of source PDFs
- no productive output mutation unless explicitly approved
- technical run artifacts confined under sandbox_root (or explicit opt-in)
- structured RunResult mapping (recognized / review / failed / planned destinations)
- profile/configuration resolution compatible with Track-B IDs or an explicit profile_path handoff
```

Why safe real execution was not wired:

Calling `run_once` today would mutate sandbox copies (archive), write outputs, and create App Support artifacts — without a dry-run guarantee and without a clean Track-B profile-path contract. Task rules forbid modifying processing-core in this task.

## 9. Workspace behavior after fix

After „Sandbox-Lauf starten“ (when folders/profile/config are ready):

1. Shows „Prüfung läuft …“
2. Sandbox gate approves copied input / explicit output
3. Core bridge validates sandbox-only request
4. Returns `requires_core_dry_run_contract` / `core_dry_run_contract_required`
5. UI shows compact:
   - Primary: „Sandbox nicht verbunden. Echte Verarbeitung benötigt noch eine sichere Dry-Run-Schnittstelle im Core.“
   - Details (≤5): keine Originalordner, produktiv gesperrt, keine Dateien verarbeitet, technischer Dry-Run-Blocker, Konfiguration
6. No fake result rows
7. Export/reporting stays preview/empty of invented documents

## 10. Tests run and results

Focused:

```bash
.venv/bin/python -m pytest \
  tests/test_ui_v2_core_bridge_sandbox_dry_run_parity.py \
  tests/test_ui_v2_workspace_configuration_selection.py \
  tests/test_ui_v2_start_button_noop_and_sandbox_wiring.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_export_reporting.py \
  tests/test_track_a_internal_app_protection.py
```

Result: **90 passed**

All Track-B UI-v2:

```bash
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Result: **480 passed, 44 skipped**

## 11. Confirmation: no Track A change

Track-A protected runtime files were not modified in this task. Known legacy dirty files remain unstaged:

- `invoice_tool/ui_profile_dialog.py`
- `invoice_tool/ui_document_rules.py`

## 12. Confirmation: no processing-core change

Unchanged:

- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`
- `invoice_tool/run.py`

## 13. Confirmation: no productive processing

Productive execution remains blocked (`dry_run` required, `productive_execution_allowed=False`, productive request rejected by adapter and bridge).

## 14. Confirmation: no original folders touched

Bridge rejects original-looking paths and refuses original-as-input/output. No core call is made; no PDF processing occurs.

## 15. Manual next test instruction

1. Launch Track-B UI-v2 only (`app_ui_v2.py`)
2. Select profile/configuration (e.g. American Express)
3. Choose copied sandbox input + explicit sandbox output
4. Click „Sandbox-Lauf starten“
5. Expect checking → compact dry-run-contract blocker (no fake results)
6. Confirm original invoice folders remain untouched

## 16. Exact next task recommendation

`KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`

Implement a processing-core dry-run / sandbox API (separate PO gate) that:

- accepts copied input + explicit output
- does not archive/mutate sources in dry-run
- confines technical artifacts or documents them as out-of-sandbox
- returns structured recognized/review/failed/planned destinations
- can then be safely bound from Track-B `core_bridge.py` (Path A)

## Files changed (this task)

- `invoice_tool/ui_v2/core_bridge.py` (new)
- `invoice_tool/ui_v2/sandbox_execution_boundary.py`
- `invoice_tool/ui_v2/workspace_configuration_selection.py`
- `invoice_tool/ui_v2/pages/workspace.py`
- `tests/test_ui_v2_core_bridge_sandbox_dry_run_parity.py` (new)
- `tests/test_ui_v2_manual_test_ux_dense_layout.py`
- `tests/test_track_a_internal_app_protection.py`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_SANDBOX_DRY_RUN_PARITY_2026-07-22.md`
