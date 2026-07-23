# Audit — Track-B Invoice Total, Art and Configuration Matching Repair

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_INVOICE_TOTAL_ART_AND_CONFIGURATION_MATCHING_REPAIR_01`
2. **Masterplan position:** Prompt 21/34
3. **HEAD before:** `515a8403c957e808264229af989168fd0ca022ad`  
   **HEAD after:** `c7f3c17188b156f36a3b633a785d71bb0a03e020`
4. **User manual evidence:** Preview-Export mit LUMITOP 500,00 / Bootshop 80,55 / Storno ohne art=storno / alle Unklar.
5. **Baseline:** Prompt 20 configuration filename pattern bridge ready; Beträge/Payment noch heuristisch falsch.
6. **Files changed:**
   - `invoice_tool/ui_v2/invoice_field_candidates.py` (neu)
   - `invoice_tool/ui_v2/extraction_mapping.py`
   - `invoice_tool/ui_v2/configuration_matching.py`
   - `invoice_tool/ui_v2/configuration_filename_renderer.py`
   - `invoice_tool/ui_v2/suggested_filename_mapping.py`
   - `invoice_tool/ui_v2/processing_state.py`
   - `invoice_tool/ui_v2/preview_export.py`
   - `invoice_tool/ui_v2/review_workflow.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `tests/test_track_b_invoice_total_art_and_configuration_matching_repair.py` (neu)
   - `docs/KI_RECHNUNGEN_TRACK_B_INVOICE_TOTAL_ART_AND_CONFIGURATION_MATCHING_REPAIR_2026-07-23.md`
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_INVOICE_TOTAL_ART_AND_CONFIGURATION_MATCHING_REPAIR_2026-07-23.md`
7. **Amount selection result:** LUMITOP 476,00; Bootshop 105,75; Böttcher 84,39; Luxvenum 154,95; Storno 68,94.
8. **Payment field result:** paypal / card (nicht amex) / fehlend mit Begründung.
9. **Document art result:** Storno → `art=storno` + Ambiguity; Rechnung → `er`.
10. **Configuration matching result:** Unklar mit präziser Reason; card matched nie AMEX; PayPal ohne Config → Unklar (partial).
11. **Controlled 5-PDF result:** korrigierte Beträge/Payments/Art; Input unverändert.
12. **Preview export result:** Komma-Beträge; Storno im art-Platzhalter; Manifest-Candidate-Felder.
13. **Tests run/results:** focused **248 passed**; UI-v2/SaaS **576 passed, 44 skipped**.
14. **No productive processing:** ja
15. **No real invoice folders:** ja
16. **No release tag changes:** ja
17. **Product status after task:** `TRACK_B_AMOUNT_AND_PAYMENT_REPAIRED_CONFIGURATION_MATCHING_PARTIAL`
18. **Remaining prompts:** 13
19. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_MATCHING_REPAIR_01`
