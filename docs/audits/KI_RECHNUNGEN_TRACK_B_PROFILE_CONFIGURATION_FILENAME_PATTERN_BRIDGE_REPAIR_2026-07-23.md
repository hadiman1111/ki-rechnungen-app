# Audit — Track-B Profile Configuration Filename Pattern Bridge Repair

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_REPAIR_01`
2. **Masterplan position:** Prompt 20/34
3. **HEAD before:** `01859687051aa72b09352db0fea385f667334563`  
   **HEAD after:** `5dcfb1caeb8623163c121183601bf8818bba4379`
4. **User correction:** Konfigurations-Dateinamensmuster ist Source of Truth; kein paralleles kanonisches Naming; Beträge mit Dezimal-Komma.
5. **Baseline:** Prompt 19 canonical template ready; Preview-Namen mit Punkt-Beträgen und generischem Muster.
6. **Existing pattern source of truth:** aktives Profil → Konfigurationen (American Express, Event Production, Architektur & Innenarchitektur, Privat, Unklar) mit `{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf`.
7. **Files changed:**
   - `invoice_tool/ui_v2/configuration_matching.py` (neu)
   - `invoice_tool/ui_v2/configuration_filename_renderer.py` (neu)
   - `invoice_tool/ui_v2/suggested_filename_mapping.py`
   - `invoice_tool/ui_v2/canonical_filename_template.py` (demoted docstring)
   - `invoice_tool/ui_v2/extraction_mapping.py`
   - `invoice_tool/ui_v2/processing_state.py`
   - `invoice_tool/ui_v2/preview_export.py`
   - `invoice_tool/ui_v2/review_workflow.py`
   - `invoice_tool/ui_v2/pages/review.py`
   - `tests/test_track_b_profile_configuration_filename_pattern_bridge_repair.py` (neu)
   - `tests/test_track_b_canonical_filename_template_and_category_mapping_repair.py` (Anpassung)
   - `tests/test_track_b_extraction_and_suggested_filename_mapping_repair.py` (Anpassung)
   - `docs/KI_RECHNUNGEN_TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_REPAIR_2026-07-23.md`
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_REPAIR_2026-07-23.md`
8. **Configuration matching result:** Bridge lädt aktive Konfigurationen; payment_field-Free-Text deaktiviert; Unklar-Fallback bei Unsicherheit.
9. **Pattern rendering result:** konfigurierte Reihenfolge + Literale `_er_`; fehlende Tokens als `FEHLT_*`.
10. **Amount format result:** `decimal_comma_2` (`84,39`); keine Dot-Decimal-Namen im Controlled Export.
11. **Generic canonical fallback result:** nur wenn kein Konfigurationsmuster; `filename_source=canonical_fallback_no_configuration_pattern`.
12. **Controlled 5-PDF verification result:** 5/5 Preview-Namen nach Konfigurationsmuster (Unklar); Input unverändert.
13. **Preview export result:** `REVIEW_REQUIRED__SUGGESTED__…` bzw. `…__INCOMPLETE__…` mit Komma-Beträgen.
14. **Tests run/results:** focused Track-B **218 passed**; UI-v2/SaaS **576 passed, 44 skipped** (nach UX-Gate-Allowlist für Naming-Module).
15. **No productive processing:** ja
16. **No real invoice folders:** ja
17. **No release tag changes:** ja (`internal-working-version-2026-07-21`, `product-v1-local-pilot-2026-07-22` unverändert)
18. **Product status after task:** `TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_READY`
19. **Remaining prompts:** 14
20. **Exact next task:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_01`
