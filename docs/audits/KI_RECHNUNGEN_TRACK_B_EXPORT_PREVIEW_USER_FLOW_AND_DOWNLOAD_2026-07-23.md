# Audit — Track-B Export Preview User Flow and Download

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_01`
2. **Masterplan position:** Prompt 16/34
3. **HEAD before:** `eda4b73e466a32e560ef16a77728e503feb42c3d`  
   **HEAD after:** *(set after commit)*
4. **Baseline:** Prompt 15 `TRACK_B_REVIEW_BUCKET_USABILITY_AND_ACTIONS_READY` — Review-Bucket nutzbar, Output leer (Preview-only), kein sichtbares Export-Paket.
5. **Files changed:**
   - `invoice_tool/ui_v2/preview_export.py` (neu)
   - `invoice_tool/ui_v2/pages/workspace.py`
   - `invoice_tool/ui_v2/state.py`
   - `tests/test_track_b_export_preview_user_flow_and_download.py` (neu)
   - `docs/KI_RECHNUNGEN_TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_2026-07-23.md` (neu)
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_2026-07-23.md` (neu)
6. **Preview export writer result:** Writer erzeugt `preview-export-<run-id>-<stamp>/` unter kontrolliertem Output mit README, manifest.json/csv, review-items.md und byte-identischen Preview-PDFs unter `files/`; Review-Dateien mit `REVIEW_REQUIRED__`.
7. **UI integration result:** CTA „Preview-Export in Output-Ordner schreiben“ nur nach erfolgreichem Sandbox-Result (`status=completed`); Safety-Copy sichtbar; kein produktiver Final-Export-CTA.
8. **Output folder structure:** `README_PREVIEW_EXPORT.md`, `manifest.json`, `manifest.csv`, `review-items.md`, `files/*.pdf` unter kontrolliertem Test-Output.
9. **Safety result:** Pfadpolitik blockiert Produktiv/Outside; Input unverändert; kein `run_once`; kein final write/move/archive/delete; keine realen Rechnungsordner; Track A/Core unberührt.
10. **Tests run/results:** focused Export-/Protection-/Smoke-Suite grün; UI-v2/SaaS-Suite + `git diff --check` (siehe Final Report).
11. **No productive processing:** ja
12. **No real invoice folders:** ja
13. **No release tag changes:** ja
14. **Product status after task:** `TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_READY`
15. **Remaining prompts:** 18
16. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_GUI_MANUAL_SMOKE_01`
