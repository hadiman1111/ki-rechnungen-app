# KI-Rechnungen Track B UI-v2 — Core Dry PO-Gate or Productive Execution Hold

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_CORE_DRY_PO_GATE_OR_PRODUCTIVE_EXECUTION_HOLD_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Core Dry Gate PO Decision

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_CORE_DRY_PO_GATE_OR_PRODUCTIVE_EXECUTION_HOLD_01`

## 2. Purpose

PO-gate / decision-prep only: document exactly what is missing for a safe dry/no-mutation execution path, compare hold vs. core dry-run vs. productive execution, and recommend the safest next step.

This task does **not**:

- implement Core dry-run
- enable productive processing
- process PDFs
- mutate real invoice folders
- touch Track A
- change processing-core

## 3. Current UI-v2 execution readiness

Track-B UI-v2 is structurally ready for **validation and honesty**, not for execution:

| Capability | Status |
|---|---|
| Honest empty states | present |
| Bounded Processing Service / State Contract | present |
| Policy-to-Runtime Bridge | present |
| Bounded LocalProcessingAdapter | present |
| Explicit input-folder state + picker UX | present (UI state only) |
| Explicit output-folder state + picker UX | present (UI state only) |
| Folders never defaulted | enforced |
| Folder create / scan / PDF processing | not done (by design) |
| Dry/no-mutation start | **blocked** — `unsupported_without_core_change` / `CORE_DRY_GATE_REQUIRES_CORE_CHANGE` |
| Productive start (`dry_run=False`) | **blocked** — `productive_blocked` / not PO-released |

`LocalProcessingAdapter.validate_request` can reach logical `ready` when source, input, output, profile, configuration, and policy intent are complete.  
`start_run` still refuses both dry and productive paths without importing or calling processing-core.

## 4. Current core dry-run finding

**Finding: `CORE_DRY_GATE_REQUIRES_CORE_CHANGE` / `unsupported_without_core_change`.**

Read-only inspection of `invoice_tool/run.py` and `invoice_tool/processing.py`:

### Callable entrypoint

- Primary programmatic entrypoint: `invoice_tool.run.run_once(source, output, *, config_path=None, rules_path=None, profile_path=None) -> Path`
- CLI: `python -m invoice_tool.run --source … --output …`
- Processor: `InvoiceProcessor.process_all()` after `run_once` constructs the processor

### Dry / no-mutation support

| Question | Answer |
|---|---|
| Existing core supports dry/no-mutation mode? | **No** — no `dry_run` / `no_mutation` parameter or flag in `run_once`, CLI, or `InvoiceProcessor` |
| Validate-only without move/copy/rename? | **No** as a public mode — preflight exists, but a full `run_once` always continues into snapshot + process |
| Result summary without writing output? | **No** — pipeline ends in publish/archive/mapping/report writes |
| Separated extract / classify / route / write effects? | **Partially at module level** (`classification.py`, `routing.py`, …) but **not** as a safe no-mutation orchestration path; write effects are embedded in `InvoiceProcessor` (`_write_active_output`, `_publish_and_archive`, archive/move, reports) |

### Why Track-B cannot wrap around this safely today

Calling `run_once` from UI-v2 would always:

1. discover source PDFs
2. create Application-Support run dirs + `input_snapshot` copies
3. mkdir output `documents` basis
4. run extraction + classification + routing
5. write renamed outputs, archive originals after success, flush mappings/traces/reports

A Track-B-only wrapper cannot turn that into a no-mutation dry-run without lying about results or mutating disks.

## 5. Missing no-mutation boundary

Missing core capability (must exist before UI-v2 may call core for dry-run):

1. Explicit `dry_run` / `no_mutation` API on a core entrypoint (or a dedicated dry entrypoint)
2. Guaranteed skip of all persistent side effects listed in §6
3. Optional in-memory / returned summary of intended classifications/routes without writing files
4. Tests proving Track-A / existing `run_once` productive behavior is unchanged when dry mode is off
5. Explicit contract that UI-v2 never invents fake result rows when core dry is unavailable

Until that boundary exists, adapter status remains:

- `core_dry_run_status` = `unsupported_without_core_change`
- dry start message = „Dry-Run ohne Dateiveränderung ist im lokalen Core noch nicht verfügbar.“

## 6. Side effects that must be blocked before dry-run / productive execution

For a safe dry/no-mutation path, **all** of the following must be blocked or redirected to non-persistent stubs:

| Side effect | Where observed (read-only) | Must block for dry-run |
|---|---|---|
| Output folder / `documents` creation | `run_once` → `documents_basis.mkdir` | yes |
| Input snapshot copy | `create_run_snapshot` → `shutil.copy2` | yes (or only ephemeral/temp with cleanup + never user folders) |
| File copy to output | `InvoiceProcessor._write_active_output` → `shutil.copy2` | yes |
| File move / archive of originals | `_publish_and_archive` / `_archive_original` / `archive_original_safely` → `shutil.move` | yes |
| Rename of outputs | publish path naming + write | yes |
| Report write | `run_logger.write_run_report`, duplicate/historical report `write_text` | yes |
| Mapping write | `OutputMappingStore.flush` / `_write_output_mapping` | yes |
| Runtime rules / profile snapshot write | `runtime_rules.json`, `profile_snapshot.json` under run support | yes for dry (or explicitly allow technical temp only under PO policy) |
| Trace / log persistence | `TraceWriter.flush`, log dirs under Application Support | treat as persistent; block or PO-scope as technical-only |
| Real invoice folder mutation | archive under `<input>/archiv/<run-id>/` | yes — never on real folders without productive PO gate |

Productive execution additionally requires backup/rollback policy and test-folder-only first runs — out of scope here.

## 7. Option A / B / C comparison

### OPTION A — PRODUCTIVE EXECUTION HOLD / CONTINUE UI READINESS

- Keep real execution blocked.
- Continue UI-v2 review/settings navigation, policy editor controls, real run result display shell.
- No processing-core changes.
- **Risk:** lowest.
- **Does not** make the app process documents yet.

### OPTION B — CORE DRY-RUN COMPATIBILITY SHIM

- Separate future task may add `dry_run` / `no_mutation` to processing-core.
- Must be explicitly PO-approved.
- Must not change existing Track A behavior when dry is off.
- Must be protected by tests proving no mutation in dry mode and unchanged productive path.
- **Risk:** medium — touches shared core used by Track A / CLI.

### OPTION C — PRODUCTIVE LOCAL EXECUTION GATE

- Later task may allow real local execution after explicit user confirmation.
- Requires PO approval.
- **Risk:** higher.
- Must define backup/rollback and test-folder-only first.
- **Not recommended** before a dry-run path exists.

## 8. Recommended option

**OPTION A — PRODUCTIVE EXECUTION HOLD / CONTINUE UI READINESS**

## 9. Reason for recommendation

Local inspection confirms:

1. No core dry/no-mutation flag exists today.
2. A Track-B-only wrapper around `run_once` cannot provide a safe no-mutation path.
3. A “small shim” is possible only as a **separate core change** (Option B), with medium risk to Track A and mandatory regression protection — not proven low-risk enough to prefer over hold.
4. Productive execution (Option C) without dry-run would expose real folders to copy/move/archive/report side effects.

Therefore the safest next step is to keep execution blocked and continue Track-B UI readiness without touching processing-core.

## 10. Product Owner decision required

**Yes.**

PO must explicitly choose:

- **A** continue UI readiness with execution hold (recommended), or
- **B** approve a separate processing-core dry/no-mutation compatibility task, or
- **C** later productive local execution gate (not recommended before dry-run)

This audit alone does **not** authorize Option B or C implementation.

## 11. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_REVIEW_AND_SETTINGS_NAVIGATION_READINESS_01`

Scope:

- wire Review and Settings pages into UI-v2 navigation
- no processing-core change
- no PDF processing
- no productive execution
- prepare visible queue/results shell

## 12. Track A separation confirmation

Confirmed:

- `app_main.py` = Track A internal local app / package path — **not modified**
- `app_ui_v2.py` = Track B newest general product UI / UI-v2 — **not modified in this task**
- Known local Legacy-UI dirty files remain unstaged and out of scope:
  - `invoice_tool/ui_profile_dialog.py` (modified, unstaged)
  - `invoice_tool/ui_document_rules.py` (untracked)

## 13. Processing-core untouched confirmation

Read-only inspection only of:

- `invoice_tool/processing.py`
- `invoice_tool/run.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`

No edits. Git status shows these files clean (not dirty).

## 14. No productive processing confirmation

No `run_once` / `InvoiceProcessor` calls. Adapter dry/productive gates remain blocked. No PDF pipeline executed.

## 15. No real invoice changes confirmation

No folder create/scan/write. No archive/move/copy against real invoice folders. Workspace folder state remains UI strings only.

## 16. Tests run and results

Optional safe non-GUI suite:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_local_processing_adapter.py \
  tests/test_ui_v2_workspace_folder_selection.py \
  tests/test_ui_v2_processing_contract.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_policy_runtime_bridge.py
```

**Result: 79 passed** (no GUI, no build, no PDF processing).

## 17. Commit / push status

- Allowed change: this audit document only
- Commit message: `docs: klaere UI-v2 Core-Dry-Gate`
- Push: only if safe gates pass after commit (`main`, behind=0, exactly one commit ahead, payload = this doc only)

## Appendix — Dry-run addition classification (no implementation)

| Path | Feasible? | Notes |
|---|---|---|
| A. Track-B wrapper only | **No** | `run_once` always mutates; wrapper cannot strip side effects |
| B. Small processing-core compatibility shim | **Possible later** | Needs PO-approved Option B; preserve Track A; heavy tests |
| C. Larger core refactor | **Possible later** | Cleaner separation of extract/classify/route vs write effects; higher scope |

## Appendix — Preflight snapshot (this task)

- Worktree: `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App`
- Branch: `main`
- HEAD / origin/main (before): `b37781b800698c9d618a2249346b7b804d75ddc9`
- Initial classification: `READY_FOR_TRACK_B_UI_V2_CORE_DRY_PO_GATE_OR_HOLD`
