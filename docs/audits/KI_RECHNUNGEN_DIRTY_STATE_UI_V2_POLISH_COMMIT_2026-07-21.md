# KI_RECHNUNGEN_DIRTY_STATE_UI_V2_POLISH_COMMIT — 2026-07-21

Task ID: `KI_RECHNUNGEN_DIRTY_STATE_UI_V2_POLISH_COMMIT_01`

## 1. Purpose

Commit only small, generic UI-v2 polish that is independent from GUI/Shell WIP, internal launcher, build/standalone, and private/local SOMAA defaults. Preserve the two-product-track separation:

- A. Internal local app for Hadi
- B. General product / UI-v2 / later SaaS

## 2. Files reviewed

Allowed candidates inspected via `git diff` / new-file review:

- `invoice_tool/ui_v2/app.py` — window resize refresh so list/detail panels recompute height
- `invoice_tool/ui_v2/config_edit_components.py` — wider/full-width field shells, dropdown kwargs, button height alignment
- `invoice_tool/ui_v2/theme.py` — re-export `LIST_DETAIL_MAX_HEIGHT`
- `invoice_tool/ui_v2/tokens.py` — `LIST_DETAIL_MAX_HEIGHT`, denser `INPUT_CONTROL_HEIGHT` 34→40
- `invoice_tool/ui_v2/validation.py` — generic filename-pattern repair + token validation hooks
- `tests/test_ui_v2_ux_control_interactions.py` — reviewed, **not committed** (depends on uncommitted `scripts/run_ui_v2_ux_interaction_gate.py`)

## 3. Why generic

Changes are layout/control polish and generic filename-pattern validation helpers. No profile IDs, no vendor account defaults, no customer-specific paths, no product-track A wiring.

## 4. Why not Hadi/SOMAA-specific

- No SOMAA/Hadi/Bismarck defaults added
- No AMEX/vobaai/vobaep defaults introduced (pre-existing hint text `z.B. amex` unchanged and not part of this diff)
- No private/local path defaults
- No dependency on `profile_config.local.json`

## 5. Why no processing-core risk

- No changes to OCR, routing, classification, file lifecycle moves, or productive processing entrypoints
- Validation only reuses already-present `repair_filename_pattern` / `validate_filename_pattern_tokens` from `configuration_model`
- UI-v2 modules stay within `invoice_tool.ui_v2.*` + existing domain helpers

## 6. Tests run

```bash
.venv/bin/python -m pytest \
  tests/test_saas_ui_v2_classification_policy.py \
  tests/test_ui_v2_ux_control_interactions.py

.venv/bin/python - <<'PY'
from invoice_tool.ui_v2 import app, config_edit_components, theme, tokens, validation
print("UI_V2_IMPORT_OK")
PY
```

## 7. Test result

- Import check: `UI_V2_IMPORT_OK`
- Pytest: `11 passed`
- Note: UX interaction test passed locally because the untracked gate script exists in the dirty worktree; the test file itself was **omitted from the commit** to avoid shipping a test that depends on uncommitted `scripts/**`.

## 8. Explicitly not included

- GUI/Shell WIP (`invoice_tool/gui.py`, `ui_*.py` shell modules, etc.)
- Internal launcher (`app_main.py`, `startup_log.py`, launcher tests)
- Build/Standalone (`pyproject.toml`, `scripts/build_macos_app.sh`, `scripts/**`, `resources/standalone/**`)
- diagnostics / evidence / tmp / cache
- PDFs
- real invoices / real invoice folders
- `.venv*` / `.venv-flet085/`
- `profile_config.local.json`
- `tests/test_ui_v2_ux_control_interactions.py` (deferred; script dependency)

## 9. Remaining dirty-state summary

After this commit, expected remaining dirty/untracked WIP includes:

- GUI/Shell modules and related architecture tests
- Internal launcher + build/standalone scripts and resources
- Various untracked audits/design refs/tasks
- `.venv-flet085/`, `testing/`, other local tooling

These remain intentionally uncommitted to keep product-track separation intact.

## 10. Next task recommendation

`KI_RECHNUNGEN_DIRTY_STATE_GUI_SHELL_WIP_TRIAGE` — classify remaining GUI/Shell vs launcher/build vs local-only artifacts into safe commit slices without mixing product tracks.
