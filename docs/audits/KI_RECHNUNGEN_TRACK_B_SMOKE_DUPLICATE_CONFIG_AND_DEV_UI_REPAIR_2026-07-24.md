# Audit — Track-B Smoke Duplicate Config + Dev UI Repair (2026-07-24)

1. **Task ID:** TRACK_B_SMOKE_DUPLICATE_CONFIG_AND_DEV_UI_REPAIR_2026-07-24

2. **HEAD before/after**
   - before: `15a2bfb465df146bbc682c44e5689cdcbdad46d5`
   - after: *(filled after commit)*

3. **Baseline**
   - branch: `main`
   - origin/main aligned (0 ahead / 0 behind at start)
   - no staged files, no git locks, no active git operation
   - Track-A protected dirty (unstaged legacy only): `invoice_tool/ui_profile_dialog.py`
   - processing-core clean
   - Prompt-34 / SaaS readiness final audit docs: present
   - controlled input/output: present
   - production final-write: disabled (`final_write_allowed_for_production=false`)

4. **Files changed**
   - `invoice_tool/ui_v2/configuration_duplicate_remediation.py` (new)
   - `invoice_tool/ui_v2/track_b_smoke_debug_copy.py` (new)
   - `invoice_tool/ui_v2/adapters/configuration_write_adapter.py`
   - `invoice_tool/ui_v2/configuration_rule_draft.py`
   - `invoice_tool/ui_v2/configuration_rule_editor.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `invoice_tool/ui_v2/state.py`
   - `tests/test_track_b_smoke_duplicate_config_and_dev_ui_repair.py` (new)
   - `docs/KI_RECHNUNGEN_TRACK_B_SMOKE_DUPLICATE_CONFIG_AND_DEV_UI_REPAIR_2026-07-24.md` (new)
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_SMOKE_DUPLICATE_CONFIG_AND_DEV_UI_REPAIR_2026-07-24.md` (new)

5. **Duplicate config result**
   - Root cause: Privat self-alias collision (`privat`/`Privat`) falsely blocked bundle save
   - Exact duplicate detection by stable key implemented
   - Unrelated Privat alias noise no longer blocks PayPal draft save
   - Exact duplicates remain blocking until explicit remediation

6. **PayPal smoke action result**
   - Action available: „PayPal-Regel speichern und Matching neu berechnen“
   - Requires confirmation + controlled target
   - Preview-only rematch; LUMITOP / 1A-Bootshop → PayPal; card not AMEX; missing field → Unklar

7. **Dev UI layout result**
   - Label-above fields, wider inputs, sticky action rows
   - Layout marker `track_b_smoke_dev_ui_layout_v1_no_overlap`

8. **Copy-text result**
   - „Prüffall als Text kopieren“ / „Diagnose kopieren“
   - Includes PayPal guidance + safety flags

9. **Safety result**
   - no productive processing
   - no real invoice folders
   - no production final-write
   - no Track-A/core/tag changes

10. **Tests run/results**
    - focused suite: 141 passed
    - UI-v2 / SaaS suite: 576 passed, 44 skipped
    - `git diff --check`: clean (exit 0)

11. **No productive processing:** yes

12. **No real invoice folders:** yes

13. **No release tag changes:** yes

14. **Product status after task:** `TRACK_B_MANUAL_SMOKE_BLOCKER_REPAIRED_READY_TO_RETRY`

15. **Exact next step**
    Open FA011466 in UI-v2 Review, set PayPal target to
    `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/geplant/paypal`,
    click „PayPal-Regel speichern und Matching neu berechnen“, verify LUMITOP +
    1A-Bootshop match PayPal, then continue dry-run package + sandbox final-write.
