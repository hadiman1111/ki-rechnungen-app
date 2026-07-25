# Audit: Track-B UI-v2 Product UX Audit and Workspace Cleanup

1. **Task ID:** `TRACK_B_UI_V2_PRODUCT_UX_AUDIT_AND_WORKSPACE_CLEANUP_2026-07-25`

2. **HEAD before:** `573fc839507ff363fd8e73940a094045d016c598`  
   **HEAD after:** _(filled after commit)_

3. **Files changed (expected):**
   - `invoice_tool/ui_v2/track_b_smoke_debug_copy.py`
   - `invoice_tool/ui_v2/workspace_file_pairs.py`
   - `invoice_tool/ui_v2/pages/workspace.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `invoice_tool/ui_v2/pages/settings.py`
   - `invoice_tool/ui_v2/shell.py`
   - `tests/test_track_b_workspace_product_cleanup.py`
   - `docs/KI_RECHNUNGEN_TRACK_B_UI_V2_PRODUCT_UX_AUDIT_AND_WORKSPACE_CLEANUP_2026-07-25.md`
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_PRODUCT_UX_AUDIT_AND_WORKSPACE_CLEANUP_2026-07-25.md`

4. **Workspace scope result:** Primary flow = header → breadcrumb → profile/config → folders/file pairs → CTA → compact status. Dev/test/evidence gated by `show_dev_surfaces`.

5. **Developer/test/evidence result:** Not primary. Rendered only when Track-B dev defaults are active.

6. **Letzte Ergebnisse result:** Removed from primary; compact status line instead (`WORKSPACE_COMPACT_STATUS_MARKER`).

7. **Configuration-details result:** Detailed lists not primary; summary + Bearbeiten only. Destination tabs under advanced/dev.

8. **Output clickability result:** Placeholders non-clickable (`OUTPUT_ROW_PLACEHOLDER_MARKER`); actionable only with valid target (`OUTPUT_ROW_ACTIONABLE_MARKER`).

9. **Output action icon result:** Right-aligned `FACT_CHECK_OUTLINED` only when actionable; tooltips Vorschlag ansehen / Zur Prüfung öffnen / Datei anzeigen.

10. **Filename edit focus result:** In-place TextField with `autofocus=True` and `FILENAME_EDIT_FOCUS_MARKER` in same detail section.

11. **Settings/dev diagnosis result:** Labeled „Entwickler / Diagnose“; collapsed sidebar; not „Erweiterte Einstellungen“.

12. **UX audit summary:** Product workspace decluttered; clickability and edit focus fixed; remaining Sandbox copy / stricter nav gating as follow-up.

13. **Follow-up issues:**
    - Residual Sandbox status strings outside primary CTA
    - Optional stricter ADMIN_NAV hide behind env flag
    - Live GUI hover/autofocus verification across Flet builds

14. **Tests run/results:** 271 passed  
    (`test_track_b_workspace_product_cleanup.py` + live file pairs + second UX + IA cleanup + review clarification + guided review + accordion + Track-A protection)

15. **Oracle result if run:** `TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS`  
    (`KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python scripts/dev/track_b_automated_smoke_oracle.py`)

16. **Safety result:** No productive processing; no run_once; no real invoice folders; Track A/Core untouched; tags unchanged.

17. **No productive processing:** Confirmed.

18. **No real invoice folders:** Confirmed.

19. **No release tag changes:** Confirmed (`product-v1-local-pilot-2026-07-22` unchanged).

20. **Product status after task:** `TRACK_B_UI_V2_PRODUCT_UX_AUDIT_AND_WORKSPACE_CLEANUP_READY`

21. **Exact next step:** Product-owner live GUI verification of Arbeitsbereich declutter + output placeholders + filename edit focus.
