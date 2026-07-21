# KI_RECHNUNGEN_LEGACY_UI_CLEANUP_OR_FREEZE_FOLLOWUP — 2026-07-21

**Task ID:** `KI_RECHNUNGEN_LEGACY_UI_CLEANUP_OR_FREEZE_FOLLOWUP_01`  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Repository Hygiene / Legacy UI and Freeze Decision  
**Classification:** `LEGACY_UI_CLEANUP_OR_FREEZE_READY`  
**Review only — no commit, no push, no destructive cleanup.**

## Preflight

| Check | Result |
|---|---|
| Worktree | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Branch | `main` |
| HEAD | `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1` |
| origin/main | `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1` |
| ahead/behind | `0 / 0` |
| Staged | none |
| Active Git op / locks | none |
| Processing/routing/classification dirty | no |
| `profile_config.local.json` in status | no |
| Real invoice folders in status | no |
| Initial classification | `READY_FOR_LEGACY_UI_CLEANUP_OR_FREEZE_REVIEW` |

## Legacy UI review

### `invoice_tool/ui_profile_dialog.py` (tracked, dirty)

| Question | Answer |
|---|---|
| Imported by committed app/navigation code? | **No** — `gui.py` (HEAD) has no import. Only committed test importability checks in `tests/test_profile_editor.py`. |
| Obsolete after Shell navigation? | **Yes** — module header marks LEGACY; production uses `ui_profiles.build_profiles_view`. |
| Useful generic code worth preserving? | Limited — dialog helpers / profile edit UX patterns; superseded by Shell pages. Not needed for freeze. |
| Private/local defaults? | **No hardcoded local paths.** Mentions `profile_config.local.json` only as path concept. Dirty diff = deprecation header + Flet 0.85 API (`ft.Border` / `ft.Padding`). |
| Decision | **Leave dirty.** Revert or delete later in a dedicated cleanup task — do not mix into freeze. |

### `invoice_tool/ui_document_rules.py` (untracked)

| Question | Answer |
|---|---|
| Imported by committed app code? | **No** |
| Obsolete/legacy? | **Yes** — full-page pre-shell config view; production uses `ui_configurations`. |
| Useful generic code? | Small helpers (`human_filename_example`, `has_legacy_destinations`) exist, but module is legacy shell. |
| Depends on old architecture? | **Yes** — `target_routing` + token extensions (`SP_32` etc.). |
| Decision | **Leave untracked.** Delete later only with explicit file list — do not commit into freeze. |

## Remaining tests decision

| Test | Decision |
|---|---|
| `tests/test_gui_startup.py` (untracked) | Mixed / partly obsolete for Shell; many cases `@requires_flet_085`. Keep local until Flet-0.85 gate env; do not freeze-commit. |
| `tests/test_flet085_ui_shell_gate.py` (untracked) | Useful as isolation gate (asserts no legacy imports in nav), but **unsafe in default `.venv`** (needs Flet ≥ 0.85). Keep local. |
| `tests/test_ui_document_rules.py` (untracked) | Obsolete with legacy module; Flet view-build tests. Keep local or delete later with module. |
| `tests/test_cfg_001_profile_ui_runtime_integration.py` (untracked) | Useful integration idea, but calls `run_once` (synthetic PDF + stubs). Not a freeze blocker; keep local; do not run in freeze review. |
| `tests/test_internal_launcher_folder_picker.py` (untracked) | Needs Flet 0.85 FilePicker API; related live/visual scripts are unsafe for freeze. Keep local. |
| `tests/test_ui_v2_ux_control_interactions.py` (untracked) | UI-v2 WIP — keep out of freeze. |
| Committed shell/launcher/path/build tests | Remain the freeze validation baseline. |

**Unsafe / skip for freeze review:** Flet 0.85 GUI windows, macOS live/visual picker scripts, real profiles, productive PDF processing.

## Remaining dirty-state buckets

### A. COMMIT_LATER_DOCS_DESIGN
- Untracked `docs/audits/*.md` (incl. SOMAA/UI-v2 history), `docs/design/`, `docs/design-references/`, `docs/tasks/`
- **Redact local paths / private context before any commit.**

### B. COMMIT_LATER_SCRIPTS_TOOLS
- Untracked `scripts/audit_ui_v2_*`, `check_ui_v2_*`, `run_ui_v2_*`, `run_flet085_*`, e2e/verify helpers
- Do **not** mix into freeze commit; evaluate per tool later.

### C. KEEP_LOCAL_ONLY
- `.venv-flet085/`
- `AGENTS.md` (local agent notes unless intentionally productized)
- Untracked legacy UI modules/tests above
- `testing/**` (411 PDFs observed — local/fixtures; never blind-delete)

### D. SAFE_DELETE_LATER_WITH_EXPLICIT_LIST
- Only after PO-approved explicit paths: obsolete UI-v2 gate scripts, orphan legacy tests **after** deciding module fate
- **Never** blind-delete `testing/**` PDFs

### E. MUST_NOT_TOUCH
- Processing/routing/classification core, `app_main.py`, `startup_log.py`, `pyproject.toml`, `scripts/build_macos_app.sh`
- `resources/standalone/**`, `docs/audits/evidence/**`, `diagnostics/**`
- `.venv*`, `profile_config.local.json`, real invoice folders, PDFs

### F. FREEZE_CAN_IGNORE
- Entire current dirty/untracked set above for purposes of freezing validated HEAD

## Freeze decision

| Question | Answer |
|---|---|
| Freeze possible without resolving every dirty file? | **Yes** |
| Validated freeze point | `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1` (`origin/main`) |
| Good freeze candidate? | **Yes** — matches pushed main; prior validations include FULL_250, GUI shell splits, launcher safe tests, build foundation |
| Clean worktree required? | **No** |
| Remaining WIP | **Leave dirty, document in freeze** — no destructive cleanup |
| macOS build timing | **After freeze** (separate post-freeze build task; not a freeze prerequisite) |
| Manual GUI smoke timing | **After freeze** (validates frozen artifact; prior boundary already `GUI_SHELL_RUNTIME_SMOKE_BUILD_BOUNDARY_READY`) |
| What freeze must document | Freeze SHA; validation list; dirty-state buckets A–F; legacy leave-dirty decisions; out-of-scope (no PDF/processing/profile commits) |

## Safe tests run (this review)

```text
.venv/bin/python -m pytest \
  tests/test_gui_startup.py \
  tests/test_navigation_regression_gate.py \
  tests/test_ui_architecture_repair.py \
  tests/test_ui_design_system.py \
  tests/test_profile_configuration_architecture.py \
  tests/test_internal_launcher_startup.py \
  tests/test_internal_launcher_run_controller.py \
  tests/test_internal_launcher_path_validation.py \
  tests/test_internal_launcher_result_reader.py \
  tests/test_app_paths.py \
  tests/test_build_macos_cleanup.py
```

**Result:** `77 passed, 35 skipped` (skips largely Flet &lt; 0.85 in default `.venv`).

## Exact next task

`KI_RECHNUNGEN_INTERNAL_WORKING_VERSION_FREEZE`

Document freeze at `51fbf11…` with remaining dirty-state inventory; no revert/delete/commit of legacy UI; no macOS build or productive processing inside the freeze documentation task unless PO expands scope.

## Confirmations

- No productive processing
- No real invoice changes
- No staged files / commit / push from this review
- Only optional new untracked audit: this file
