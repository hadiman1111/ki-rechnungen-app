# Audit — Track-B Preview Export Filename Quality and Recognition Triage

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_AND_RECOGNITION_TRIAGE_01`
2. **Masterplan position:** Prompt 17/34
3. **HEAD before:** `70fc810535287ca2d1776784de9a76d38ad6d42e`  
   **HEAD after:** `0844d053490fd45060b13e486d0f07f6ef90ec80`
4. **User observation:** Alle Preview-PDFs heißen `REVIEW_REQUIRED__<original>`; Nutzer erwartet sinnvolle System-Vorschläge wie in der internen App.
5. **Baseline:** Prompt 16 — Preview-Export-Paket mit byte-identischen PDFs unter kontrolliertem Output; Review-Prefix; keine Produktivwrites.
6. **Latest preview export inspected:**  
   `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/preview-export-manual-verify-16-20260723T071458840917Z`
7. **Manifest naming evidence (Prompt-16 package):**
   - Alle 5 Items: `review_required=true`, status `unklar`
   - `planned_target=preview/<original>` (Basename = Source)
   - Kein `suggested_filename` / `filename_source` / `naming_reason` (vor diesem Task)
   - Keine Extraktionsfelder supplier/date/amount
8. **Why REVIEW_REQUIRED:** Dry-Run `all_review`; Export markiert Prüffälle bewusst; zusätzlich fehlten abweichende Vorschlagsnamen (Recognition/Mapping-Lücke).
9. **Files changed:**
   - `invoice_tool/ui_v2/preview_export.py`
   - `invoice_tool/ui_v2/pages/workspace.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `invoice_tool/ui_v2/review_preview_state.py`
   - `tests/test_track_b_preview_export_filename_quality_and_recognition_triage.py`
   - `docs/KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_AND_RECOGNITION_TRIAGE_2026-07-23.md`
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_AND_RECOGNITION_TRIAGE_2026-07-23.md`
10. **Naming improvement result:** Export nutzt bei abweichendem geplanten Basename `REVIEW_REQUIRED__SUGGESTED__<safe>.pdf`; sonst Original-Fallback; Manifest/Report erklären Quelle und Grund. Aktuelle 5 Real-PDFs bleiben Fallback, bis Extraction/Mapping liefert.
11. **Remaining extraction/routing gap:** Track-B liefert keine sinnvollen Umbenennungsnamen / Extraktionsdaten für die Sandbox-PDFs; interne App-Logik nicht in Track-B verdrahtet.
12. **Tests run/results:** focused 155 passed; UI-v2/SaaS 576 passed, 44 skipped; `git diff --check` clean.
13. **No productive processing:** yes
14. **No real invoice folders:** yes
15. **No release tag changes:** yes (`product-v1-local-pilot-2026-07-22`, `internal-working-version-2026-07-21` unverändert)
16. **Product status after task:** `TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_IMPROVED`
17. **Remaining prompts:** 17
18. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_REPAIR_01`

Explizit: nicht SaaS-ready, nicht production-ready, keine produktive Verarbeitung.
