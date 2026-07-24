# Track B — Development Default Input/Output Folders (UI-v2 Manual Smoke)

**Task ID:** `KI_RECHNUNGEN_TRACK_B_DEV_DEFAULT_INPUT_OUTPUT_FOLDERS_01`  
**Date:** 2026-07-24  
**Product status (after this task):** `TRACK_B_DEV_DEFAULT_FOLDERS_READY_TO_RETRY_MANUAL_SMOKE`

## Purpose

Temporary **UI-v2 development-only** convenience for Track-B manual smoke: prefill controlled input/output folders so the product owner does not re-enter the same paths every launch.

This is **not** product behavior and **not** SaaS-ready.

## Exact default paths

| Role | Path |
|------|------|
| Input | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` |
| Output | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` |
| PayPal target helper | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/geplant/paypal` |

## Dev-only scope

- Lives in `invoice_tool/ui_v2/dev_defaults.py`
- Activated from `app_ui_v2.py` local entry and/or env:
  - `KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1` → on
  - `KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=0` → hard off
- When env unset, local `app_ui_v2.py` enables only for the `KI-Rechnungen-App` worktree
- Does **not** change Track A UI
- Does **not** change processing-core
- Does **not** become a generic product default for SaaS distribution

## UI behavior

- On UI-v2 start / workspace: if input/output empty → prefill controlled paths
- Existing user paths are never overwritten
- Visible note: `Entwicklungsmodus: kontrollierte Testordner sind vorbelegt.`
- If folders missing: clear message + optional button `Kontrollierte Testordner erstellen`
- Empty review help explains that folders are prefilled and a controlled Preview/Sandbox run must be started in the workspace
- Optional button `Kontrollierten Preview-Lauf starten` navigates to workspace (no auto-run)

## PayPal target helper

When creating a PayPal config from guidance and `proposed_condition` is `payment_field ist paypal`:

- Prefill destination with the controlled PayPal folder (if empty)
- Only under the controlled output root
- If folder missing: `Der kontrollierte PayPal-Zielordner fehlt. Bitte Testordner erstellen.`
- Never auto-saves a PayPal rule

## Folder creation behavior

Button may create **only**:

1. `.../KI-Rechnungen-Test/input`
2. `.../KI-Rechnungen-Test/output`
3. `.../KI-Rechnungen-Test/output/geplant/paypal`

Requires explicit click. Never creates or touches real invoice folders.

## Safety guarantees

- No auto-run
- No productive processing
- No `run_once`
- No production final-write (`final_write_allowed_for_production=false` remains)
- No real invoice folders
- No silent profile/config mutation
- All actions still require explicit clicks
- Temporary — can be removed later by deleting `dev_defaults.py` wiring and docs

## How to remove later

1. Remove calls from `app_ui_v2.py`, `app.py`, `workspace.py`, `review.py`, `configuration_rule_editor.py`
2. Delete `invoice_tool/ui_v2/dev_defaults.py`
3. Delete related tests/docs
4. Keep Track A / processing-core untouched

## Launch (manual smoke)

```bash
KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv-flet085/bin/python app_ui_v2.py
```

Or simply launch `app_ui_v2.py` from this worktree (local entry enables defaults unless env=`0`).

## Exact next manual smoke step

1. Start UI-v2 with the command above
2. Confirm Arbeitsbereich shows controlled input/output + the Entwicklungsmodus note
3. Start a controlled Preview/Sandbox run explicitly
4. Continue PayPal guidance → verify target prefilled under controlled output
5. Do **not** select real invoice folders; do **not** enable production final-write
