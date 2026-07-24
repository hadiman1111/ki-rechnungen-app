# Audit — Track-B Filename Pattern Simplification (2026-07-24)

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_FILENAME_PATTERN_SIMPLIFICATION_2026-07-24`
2. **HEAD before:** `94421d2f664c605796217369d34c13f61b6301cf`  
   **HEAD after:** commit `fix: vereinfache Track-B Dateinamensmuster` on `main` (see `git log -1 --grep='vereinfache Track-B Dateinamensmuster'`)
3. **Files changed:**
   - `invoice_tool/ui_v2/configuration_rule_draft.py`
   - `invoice_tool/ui_v2/configuration_rule_apply_preview.py`
   - `invoice_tool/ui_v2/configuration_matching.py`
   - `invoice_tool/ui_v2/automated_smoke_oracle.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `tests/test_track_b_filename_pattern_simplification.py` *(new)*
   - `tests/test_track_b_automated_smoke_oracle.py`
   - `tests/test_track_b_review_surface_declutter.py`
   - `docs/KI_RECHNUNGEN_TRACK_B_FILENAME_PATTERN_SIMPLIFICATION_2026-07-24.md` *(new)*
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_FILENAME_PATTERN_SIMPLIFICATION_2026-07-24.md` *(new)*
4. **Old/new pattern:**
   - Old: `{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf`
   - New: `{invoice_date}_{art}_{supplier}_{amount}_{payment_field}.pdf`
5. **Per-document filename result:**
   - LUMITOP → `2026-05-11_er_LUMITOP_476,00_paypal.pdf`
   - 1A-Bootshop → `2026-05-15_er_1A-Bootshop.de_105,75_paypal.pdf`
   - Böttcher card → `2026-05-23_er_Böttcher_AG_84,39_card.pdf`
   - Luxvenum → `2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf`
   - Böttcher Storno → `2026-06-18_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf`
6. **Oracle rerun result:** `TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS` (all 5 documents PASS; paypal_ok=true; hashes_unchanged=true)
7. **Safety result:** originals unchanged; no run_once; no production final-write; no real invoice folders; Track A / processing-core untouched; release tags unchanged
8. **Tests run/results:**
   - focused: 106 passed (`test_track_b_filename_pattern_simplification`, automated_smoke_oracle, review_surface_declutter, dev_default_folders, track_a_protection)
   - UI-v2/SaaS: 576 passed, 44 skipped
   - `git diff --check`: clean on task files
9. **No productive processing:** yes
10. **No real invoice folders:** yes
11. **No release tag changes:** yes (`internal-working-version-2026-07-21`, `product-v1-local-pilot-2026-07-22` unchanged)
12. **Product status after task:** `TRACK_B_FILENAME_PATTERN_SIMPLIFIED_READY`
13. **Exact next step:** Track-B Review-UX weiter glätten (optional); Terminal-Oracle als Regressionsgate behalten; keine produktive Freigabe.
