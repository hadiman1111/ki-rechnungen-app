# Audit — Track-B Preview Export State Freshness Repair

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_REPAIR_01`
2. **Masterplan position:** Prompt 24/34
3. **HEAD before:** `9b10343946e89533278dd538b68412093277cc55`  
   **HEAD after:** *(gesetzt nach Commit)*
4. **User manual evidence:** Review-UI zeigte aktuelle Werte (LUMITOP 476,00 / Bootshop 105,75 / Storno er_storno); neuester Export-Ordner `preview-export-track-b-dry-a9609610b265-20260723T105958144956Z` enthielt noch 500,00 / 80,55 / er_er.
5. **Baseline:** Prompt 23 Configuration Coverage Guidance ready; HEAD `9b10343946e89533278dd538b68412093277cc55`.
6. **Files changed:**
   - `invoice_tool/ui_v2/preview_export.py`
   - `invoice_tool/ui_v2/processing_state.py`
   - `tests/test_track_b_preview_export_state_freshness_repair.py` (new)
   - `docs/KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_REPAIR_2026-07-23.md` (new)
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_REPAIR_2026-07-23.md` (new)
7. **Root cause:** Export serialisierte Run-State ohne Refresh der aktuellen Sandbox-Enrichment-Daten und ohne Freshness-Abgleich mit dem Review-UI-Naming-Snapshot; stale Pre-Prompt-21-Werte konnten geschrieben werden.
8. **State freshness guard result:** `validate_export_state_freshness` + interne Storno/`er_er`-Prüfung; Mismatch → `PREVIEW_EXPORT_STALE_STATE_BLOCKED`.
9. **Current-state export result:** Workspace-Export refreshed `planned_destinations` aus kontrolliertem Input und schreibt nur den aktuellen State; `exported_from_current_state=true`, `previous_export_reused=false`.
10. **Controlled 5-PDF result:** LUMITOP 476,00; Bootshop 105,75; Böttcher 84,39; Luxvenum 154,95; Storno 68,94 mit `er_storno`.
11. **Preview export examples after repair:**
    - `REVIEW_REQUIRED__SUGGESTED__2026-05-11_er_er_LUMITOP_476,00_paypal.pdf`
    - `REVIEW_REQUIRED__SUGGESTED__2026-05-15_er_er_1A-Bootshop.de_105,75_paypal.pdf`
    - `REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_er_Böttcher_AG_84,39_card.pdf`
    - `REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf`
    - `REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-06-18_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf`
12. **Tests run/results:**
    - Focused Track-B + Protection: 323 passed
    - UI-v2/SaaS: 576 passed, 44 skipped
    - `git diff --check`: clean
    - Controlled verify export from intentionally stale state → current filenames (476,00 / 105,75 / er_storno)
13. **No productive processing:** yes
14. **No real invoice folders:** yes
15. **No release tag changes:** yes (`internal-working-version-2026-07-21`, `product-v1-local-pilot-2026-07-22` unverändert)
16. **Product status after task:** `TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_READY`
17. **Remaining prompts:** 10
18. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_01`
