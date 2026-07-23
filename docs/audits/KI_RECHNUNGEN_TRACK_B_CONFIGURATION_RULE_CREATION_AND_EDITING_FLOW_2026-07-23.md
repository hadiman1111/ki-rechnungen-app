# Audit — Track-B Configuration Rule Creation and Editing Flow

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_01`
2. **Masterplan position:** Prompt 26/34
3. **HEAD before/after:** before `8d035dbd0b1ea6b7dfbaed7c96eedee8a6949033` / after (commit on main after this task)
4. **Baseline:** Prompt-25 GUI-smoke pass with config coverage gaps; PayPal/card Unklar because no active matching config; missing payment_field Unklar with guidance
5. **Files changed:**
   - `invoice_tool/ui_v2/configuration_rule_draft.py` (new)
   - `invoice_tool/ui_v2/configuration_rule_editor.py` (new)
   - `invoice_tool/ui_v2/state.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `tests/test_track_b_configuration_rule_creation_and_editing_flow.py` (new)
   - `docs/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_2026-07-23.md` (new)
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_2026-07-23.md` (new)
6. **Rule draft model result:** `ConfigurationRuleDraft` with create/edit/manual types, evidence, warnings, confirmation flag, unsaved-by-default
7. **PayPal draft result:** name PayPal, condition `payment_field ist paypal`, no business category, requires confirmation
8. **Generic-card draft result:** name `Kreditkarte / Nicht-AMEX-Karte`, condition `payment_field ist card`, not AMEX
9. **Missing-payment-field result:** `manual_review_only`, no automatic payment rule, manual/alternative criterion guidance
10. **UI action result:** Review exposes create / edit existing / manual keep Unklar; draft panel with save/cancel
11. **Save behavior result:** explicit confirmation required; persists via UI-v2 `configuration_write_adapter` only; no run_once / input mutation / final PDFs
12. **Tests run/results:**
    - Focused Prompt-26 + related Track-B + Track-A protection: **138 passed**
    - UI-v2 / SaaS: **576 passed, 44 skipped**
    - `git diff --check`: clean
13. **No productive processing:** yes
14. **No real invoice folders:** yes
15. **No release tag changes:** yes
16. **Product status after task:** `TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_READY`
17. **Remaining prompts:** 8
18. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_01`

Explizit: nicht SaaS-ready, nicht production-ready.
