# Audit — Track-B Configuration Coverage and User Guidance

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_COVERAGE_AND_USER_GUIDANCE_01`
2. **Masterplan position:** Prompt 23/34
3. **HEAD before:** `01c0716a28d11efe40ea15a538434327ce6eae3c`  
   **HEAD after:** 
4. **Baseline:** Prompt 22 matching ready; coverage gaps disclosed; Unklar with precise reasons but weak user guidance.
5. **Files changed:**
   - `invoice_tool/ui_v2/configuration_guidance.py` (new)
   - `invoice_tool/ui_v2/configuration_matching.py`
   - `invoice_tool/ui_v2/suggested_filename_mapping.py`
   - `invoice_tool/ui_v2/extraction_mapping.py`
   - `invoice_tool/ui_v2/processing_state.py`
   - `invoice_tool/ui_v2/preview_export.py`
   - `invoice_tool/ui_v2/review_workflow.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `tests/test_track_b_configuration_coverage_and_user_guidance.py` (new)
   - `docs/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_COVERAGE_AND_USER_GUIDANCE_2026-07-23.md` (new)
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_COVERAGE_AND_USER_GUIDANCE_2026-07-23.md` (new)
6. **Guidance model result:** `derive_configuration_coverage_guidance` liefert Status/Typ/Hinweis/Aktion/Severity; Propagierung in Manifest/UI.
7. **PayPal guidance result:** `missing_config_for_detected_payment` + deutscher Hinweis ohne Auto-Mapping.
8. **Generic card guidance result:** `no_safe_card_configuration`; AMEX nicht belegt; keine AMEX-Match-Empfehlung.
9. **Missing payment field guidance result:** `missing_payment_field` + Zahlungsfeld-Hinweis.
10. **Controlled 5-PDF result:** LUMITOP/Bootshop → PayPal-Guidance; Böttcher card → generic-card; Luxvenum/Storno → missing-payment-field.
11. **Preview export result:** neue Felder in manifest.json/csv/review-items.md/README.
12. **Tests run/results:**
    - Focused Track-B + Protection: 296 passed
    - UI-v2/SaaS: 576 passed, 44 skipped
    - `git diff --check`: clean
13. **No productive processing:** yes
14. **No real invoice folders:** yes
15. **No release tag changes:** yes (`internal-working-version-2026-07-21`, `product-v1-local-pilot-2026-07-22` unverändert)
16. **Product status after task:** `TRACK_B_CONFIGURATION_COVERAGE_AND_USER_GUIDANCE_READY`
17. **Remaining prompts:** 11
18. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_01`
