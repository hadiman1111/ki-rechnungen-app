# Track-B Review Focus & Status Colors — 2026-07-27

## Scope

UI-v2-only UX hotfix:

- Status colors (OK green check / open soft-red)
- Success message „Alle Prüfungen erfolgreich.“
- Prüfung list shows decision-needed files only
- Top-focus selected file + detail at the visible top

No Track-A changes, no processing-core changes, no productive run, no real invoice folders.

## Status mapping

Shared helpers in `track_b_smoke_debug_copy.py`:

- `map_output_status_to_ui_kind` → `ok` | `needs_review` | `neutral`
- `review_item_needs_open_decision` → conservative primary-list filter
- `document_status_marker` in `components.py` → non-interactive green check / red marker (no Checkbox)

Workspace file-pair rows and Prüfung cards reuse this mapping.

## Prüfung top-focus

Selecting a file renders:

1. Top-focus block with selected file card
2. Detail panel directly underneath
3. Remaining open files listed below (selected file omitted to avoid duplication)

Filename edit stays inside the top-focus detail panel.

## Success empty state

When no open decision items remain after a run:

- Prüfung shows „Alle Prüfungen erfolgreich.“
- No technical/oracle empty-state text in that branch
