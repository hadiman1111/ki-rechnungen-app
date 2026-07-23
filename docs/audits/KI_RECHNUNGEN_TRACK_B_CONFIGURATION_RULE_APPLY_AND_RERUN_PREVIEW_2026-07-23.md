# Audit — Track-B Configuration Rule Apply and Rerun Preview

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_01`
2. **Masterplan position:** Prompt 27/34
3. **HEAD before/after:** before `994ca4f678dace6b69682ff05ef22a6767d8206c` / after (commit on main after this task)
4. **Baseline:** Prompt-26 rule creation/editing flow ready; save via UI-v2 adapter; no automatic preview rerun yet
5. **Files changed:**
   - `invoice_tool/ui_v2/configuration_rule_apply_preview.py` (new)
   - `invoice_tool/ui_v2/configuration_rule_editor.py`
   - `invoice_tool/ui_v2/processing_state.py`
   - `invoice_tool/ui_v2/state.py`
   - `invoice_tool/ui_v2/review_workflow.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `invoice_tool/ui_v2/preview_export.py`
   - `tests/test_track_b_configuration_rule_apply_and_rerun_preview.py` (new)
   - `docs/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_2026-07-23.md` (new)
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_2026-07-23.md` (new)
6. **Rule apply result:** After explicit save, preview-only apply/rerun is exposed; matching re-evaluates planned destinations against updated UI-v2 active configs
7. **PayPal rerun result:** LUMITOP + 1A-Bootshop Unklar → PayPal; card/missing payment remain Unklar; no silent business category
8. **Generic-card rerun result:** card item → `Kreditkarte / Nicht-AMEX-Karte`; AMEX still requires explicit AMEX evidence
9. **Preview export after rerun result:** Manifest/review-items include `rule_applied`, `applied_configuration_*`, `rerun_preview_after_rule_change`, previous/new matched configuration; export uses updated matched state
10. **Safety result:** no run_once, no input mutation, no final PDFs, no real invoice folders, Track A/core untouched, tags unchanged
11. **Tests run/results:** see final report (focused + UI-v2/SaaS + `git diff --check`)
12. **No productive processing:** yes
13. **No real invoice folders:** yes
14. **No release tag changes:** yes
15. **Product status after task:** `TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_READY`
16. **Remaining prompts:** 7
17. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_01`

Explizit: nicht SaaS-ready, nicht production-ready.
