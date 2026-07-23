# Audit — Track-B Extraction and Suggested Filename Mapping Repair

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_REPAIR_01`
2. **Masterplan position:** Prompt 18/34
3. **HEAD before:** `333872a93219402eea5ee1ee6eaa1d75598c72d7`  
   **HEAD after:** `6d8dd654f6d212d0b6c5d9447044cf043beb41b5`
4. **Baseline:** Prompt 17 — Preview-Export Filename Quality improved; 5 Real-PDFs ohne sinnvolle Vorschläge
5. **Internal app naming diagnosis:** AI/OCR-Extraktion + Template-Filename + produktiver Write/Archive-Pfad; Core-Dry-Run absichtlich ohne OCR/AI
6. **Track-B gap diagnosis:** fehlende Extraktionsfelder im Sandbox-Pfad; Preview-Export war vorbereitet, Mapping/Bridge fehlte
7. **Files changed:**  
   - `invoice_tool/ui_v2/suggested_filename_mapping.py` (neu)  
   - `invoice_tool/ui_v2/extraction_mapping.py` (neu)  
   - `invoice_tool/ui_v2/processing_state.py`  
   - `invoice_tool/ui_v2/sandbox_execution_boundary.py`  
   - `invoice_tool/ui_v2/preview_export.py`  
   - `invoice_tool/ui_v2/review_workflow.py`  
   - `invoice_tool/ui_v2/pages/review.py`  
   - `tests/test_track_b_extraction_and_suggested_filename_mapping_repair.py` (neu)  
   - docs + audit
8. **Mapping/bridge result:** lokale Texttextextraktion + Suggested-Filename-Mapping verdrahtet; kein `run_once`, kein Core-Write
9. **Controlled 5-PDF verification result:** ≥1 (tatsächlich 5/5) sinnvolle Vorschlagsnamen; Input unverändert
10. **Suggested filename result:** Muster `{invoice_date}_{supplier}_{amount}.pdf` mit Sanitize; Review bleibt erforderlich
11. **Preview export result:** `REVIEW_REQUIRED__SUGGESTED__…` wenn Vorschlag vorhanden; Manifest mit Naming-/Extraktionsfeldern
12. **Tests run/results:**  
    - focused Track-B suite: **174 passed**  
    - `tests/test_ui_v2_*.py` + `tests/test_saas_ui_v2_*.py`: **576 passed, 44 skipped**  
    - `git diff --check`: clean  
    - controlled 5-PDF verify: **5/5** suggested filenames; input unchanged; preview-export under controlled output
13. **No productive processing:** yes
14. **No real invoice folders:** yes
15. **No release tag changes:** yes
16. **Product status after task:** `TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_READY`
17. **Remaining prompts:** 16
18. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_SUGGESTED_FILENAME_PREVIEW_EXPORT_GUI_SMOKE_01`

Explizit: nicht SaaS-ready, nicht production-ready.
