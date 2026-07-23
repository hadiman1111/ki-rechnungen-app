# Audit — Track-B GUI Visual Smoke Blank-Window Triage

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_AND_BLANK_WINDOW_TRIAGE_01`
2. **Masterplan position:** Prompt 13/34
3. **HEAD before:** `d2b53206d3934485aed52e0981f110e22bbba753`  
   **HEAD after:** *(gesetzt nach Commit)*
4. **User evidence:** UI-v2 via `.venv/bin/python app_ui_v2.py` öffnete leeres weiß/bläuliches Fenster; kein Workspace, keine Ordnerwahl, kein Sandbox-CTA, keine Counts/Export/Safety; kein sichtbarer Terminal-Traceback; kein Sandbox-/Produktivlauf; Input 5 PDFs / Output 0 im kontrollierten Testordner.
5. **GUI smoke classification:** `GUI_VISUAL_SMOKE_BLOCKED` (vor Repair); nach Repair bereit für Rerun mit Flet 0.85.
6. **Diagnosis:** `build_ui_v2` hängt Shell/Workspace korrekt ein und ruft `page.update()`; unter Flet 0.28 (`.venv`) scheitert Workspace-Build an `ft.Padding.symmetric` → Exception vor `page.add` → leeres Fenster mit Canvas-Hintergrund.
7. **Root cause:** Flet-Version-Mismatch — UI-v2 erfordert Flet ≥ 0.85 (`.venv-flet085`); beobachteter Start nutzte Flet 0.28.3 (`.venv`).
8. **Files changed:**
   - `app_ui_v2.py`
   - `invoice_tool/ui_v2/startup_diagnostics.py` *(neu)*
   - `tests/test_track_b_gui_visual_smoke_blank_window_triage.py` *(neu)*
   - `docs/KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_AND_BLANK_WINDOW_TRIAGE_2026-07-22.md` *(neu)*
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_AND_BLANK_WINDOW_TRIAGE_2026-07-22.md` *(neu)*
9. **Repair summary:** `start_ui_v2()` prüft Flet-Version, mountet Workspace oder sichtbare Diagnostik, loggt Startup-Fehler auf stderr; verhindert leeres Startfenster.
10. **Tests run/results:**
    - Focused: `test_track_b_gui_visual_smoke_blank_window_triage.py` + guided docs + sandbox path policy + controlled copied smoke + Track-A protection → **61 passed**
    - UI-v2 / SaaS: `tests/test_ui_v2_*.py` + `tests/test_saas_ui_v2_*.py` → **576 passed, 44 skipped**
    - `git diff --check` (changed files) → clean
11. **No productive processing:** ja
12. **No real invoice folders:** ja
13. **No release tag changes:** ja
14. **Product status after task:** `TRACK_B_GUI_VISUAL_SMOKE_BLANK_WINDOW_REPAIRED_READY_FOR_RERUN`
15. **Remaining prompts:** 21
16. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_RERUN_01`
