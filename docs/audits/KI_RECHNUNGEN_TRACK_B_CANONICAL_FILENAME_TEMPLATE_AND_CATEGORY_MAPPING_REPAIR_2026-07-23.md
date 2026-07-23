# Audit — Track-B Canonical Filename Template and Category Mapping Repair

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_REPAIR_01`
2. **Masterplan position:** Prompt 19/34
3. **HEAD before:** `6efa0a955d1d9fc7eba183200a8e82986d3962f4`  
   **HEAD after:** *(filled after commit/push)*
4. **User observation:** Prompt-18-Namen ohne Rechnungsart/Zuordnung (z. B. `260523_Böttcher_AG_84.39.pdf`).
5. **Baseline:** Prompt 18 extraction/suggested-filename mapping ready; Muster `{date}_{supplier}_{amount}`.
6. **Required pattern:** `<YYMMDD>_<DOCUMENT_DIRECTION>_<BUSINESS_CATEGORY>_<COUNTERPARTY_NAME>_<AMOUNT>.pdf`
7. **Files changed:**
   - `invoice_tool/ui_v2/canonical_filename_template.py` (neu)
   - `invoice_tool/ui_v2/suggested_filename_mapping.py`
   - `invoice_tool/ui_v2/extraction_mapping.py`
   - `invoice_tool/ui_v2/processing_state.py`
   - `invoice_tool/ui_v2/preview_export.py`
   - `invoice_tool/ui_v2/review_workflow.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `tests/test_track_b_canonical_filename_template_and_category_mapping_repair.py` (neu)
   - `tests/test_track_b_extraction_and_suggested_filename_mapping_repair.py` (Erwartung angepasst)
   - `docs/KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_REPAIR_2026-07-23.md`
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_REPAIR_2026-07-23.md`
8. **Canonical template result:** feste 5-Komponenten-Reihenfolge, Version `track_b_canonical_v1`
9. **Direction result:** externe Lieferanten-PDFs → `Eingangsrechnung`; unsicher → `Unklare_Rechnungsart`
10. **Category result:** Mapping-Schicht vorhanden; ohne Routing-Label → `Unklare_Zuordnung` (kein Architektur-Default)
11. **Controlled 5-PDF verification result:** kanonische Preview-Namen für 5/5; Input unverändert
12. **Preview export result:** `REVIEW_REQUIRED__SUGGESTED__<canonical>.pdf` + Manifest-Felder
13. **Tests run/results:**
    - Focused Prompt-19 suite + Prompt-18/17/15 angrenzend + Track-A protection: **199 passed**
    - `tests/test_ui_v2_*.py` + `tests/test_saas_ui_v2_*.py`: **576 passed, 44 skipped**
    - `git diff --check` on touched files: clean
    - Controlled preview-export: `preview-export-prompt19-verify-20260723T102349292335Z` — 5/5 kanonische Namen, Input unverändert
14. **No productive processing:** yes
15. **No real invoice folders:** yes
16. **No release tag changes:** yes (`product-v1-local-pilot-2026-07-22` / `internal-working-version-2026-07-21` unverändert)
17. **Product status after task:** `TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_READY`
18. **Remaining prompts:** 15
19. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_PREVIEW_EXPORT_GUI_SMOKE_01`

nicht SaaS-ready · nicht production-ready
