# Track-B Startup / Review / Configuration UX Hotfix — 2026-07-27

## Scope

UI-v2-only hotfix:

- No blank startup root (loading surface)
- Sensible initial/min window size
- OK status markers right-aligned
- Planned filename ≠ fully reviewed
- Clear card-unclear copy
- Plain-German Prüfung header
- Robust review top-focus
- Configurations: full-width active profile, create button own row, equal list/detail height
- Filename pattern without `_er_er_`; clear block reorder

No Track-A changes, no processing-core changes, no productive run, no real invoice folders, no release-tag changes.

## Key helpers

- `document_has_open_review_need` / `resolve_document_ui_status`
- `review_header_status_text`
- Startup: `_mount_startup_loading_surface`, `_apply_startup_window_geometry`

## Tests

- `tests/test_track_b_startup_window_and_no_blank.py`
- `tests/test_track_b_review_focus_and_status_colors.py`
- `tests/test_track_b_configuration_layout_and_pattern_cleanup.py`
