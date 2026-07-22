# Pilot Readiness Acceptance Gate

## 1. Task ID

`KI_RECHNUNGEN_PILOT_READINESS_ACCEPTANCE_GATE_01`

## 2. Masterplan position

Prompt 11 of 12 bis Produktversion 1 / lokale Pilotfähigkeit.

## 3. Purpose

Formale Abnahme der lokalen Track-B-Pilotreife unter dokumentierten Sandbox-/Kopie-/Nicht-Produktiv-Grenzen — lokale Pilotreife, nicht SaaS-bereit; ohne produktive Verarbeitung, ohne Originalordner, ohne OCR/AI.

## 4. Acceptance decision

**ACCEPTED_LOCAL_PILOT**

Track B ist als lokale Pilotversion abgenommen.  
Nicht abgenommen: SaaS-Reife, produktive Verarbeitung, DATEV-/Cloud-Produktivexport, Originalordner-Nutzung.

## 5. Acceptance matrix

| Key | Art | Status |
|-----|-----|--------|
| track_b_entry_separate | accepted_required | met |
| track_a_protection_passes | accepted_required | met |
| sandbox_gate_blocks_unsafe | accepted_required | met |
| sandbox_execution_boundary_exists | accepted_required | met |
| synthetic_e2e_passes | accepted_required | met |
| copied_realistic_validation_passes | accepted_required | met |
| review_workflow_separates_buckets | accepted_required | met |
| profile_policy_readiness_exists | accepted_required | met |
| export_reporting_preview_exists | accepted_required | met |
| onboarding_local_pilot_sandbox_only | accepted_required | met |
| productive_processing_blocked | accepted_required | met |
| export_preview_only | accepted_required | met |
| no_saas_ready_claim | accepted_required | met |
| no_private_defaults | accepted_required | met |
| no_processing_core_change | accepted_required | met |
| full_ui_v2_suite_passes | accepted_required | met |
| not_saas_ready | explicit_non_goal | met |
| no_login_tenant_billing | explicit_non_goal | met |
| no_productive_datev_cloud_export | explicit_non_goal | met |
| no_productive_original_folder_processing | explicit_non_goal | met |
| no_real_ocr_ai_validation_in_gate | explicit_non_goal | met |
| no_macos_packaged_app_build | explicit_non_goal | met |
| no_legal_tax_approval | explicit_non_goal | met |
| no_production_classification_guarantee | explicit_non_goal | met |

Helfer: `invoice_tool/ui_v2/pilot_acceptance.py`

## 6. Accepted scope

Lokale Pilotversion mit Sandbox-Gate, Ausführungsgrenze, Synthetic E2E, copied-realistic Validation, Review-Workflow, Profil-/Policy-Reife, Exportvorschau, Onboarding und Track-A-Trennung — unter expliziter Produktivsperre.

## 7. Explicit non-goals

- nicht SaaS-bereit
- kein Login/Mandant/Abrechnung
- kein produktiver DATEV-/Cloud-Export
- keine produktive Originalordner-Verarbeitung
- keine echte OCR/AI-Validierung in diesem Gate
- kein macOS-App-Build
- keine steuer-/rechtliche Freigabe
- keine Produktionsgarantie für Klassifikation

## 8. Safety boundaries

- keine realen Rechnungen
- keine Originalordner
- keine produktive Verarbeitung
- kein OCR/AI
- kein Track-A-Behavior-Change
- kein Processing-Core-Change
- keine privaten Defaults
- keine SaaS-/DATEV-Produktiv-Claims

## 9. Test basis

Fokussiert:

- `tests/test_ui_v2_pilot_acceptance_gate.py`
- `tests/test_ui_v2_onboarding_readiness.py`
- `tests/test_ui_v2_copied_real_data_validation.py`
- `tests/test_ui_v2_synthetic_e2e_product_flow.py`
- `tests/test_ui_v2_export_reporting.py`
- `tests/test_track_a_internal_app_protection.py`

Vollständig Track B:

- `tests/test_ui_v2_*.py`
- `tests/test_saas_ui_v2_*.py`

## 10. Documentation created

- `docs/KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_ACCEPTANCE_REPORT_2026-07-22.md`
- `docs/KI_RECHNUNGEN_TRACK_B_PILOT_LIMITATIONS_2026-07-22.md`
- dieses Audit

## 11. Why this does not process original real PDFs

Nur reine Acceptance-/Onboarding-/Doc-/Test-Artefakte in UI-v2. Kein PDF-IO, kein OCR/AI, keine Live-Core-Verarbeitung.

## 12. Why this does not touch real invoice folders

Keine Pfad-Defaults, kein Ordner-Scan, keine Writes außerhalb pytest `tmp_path`. Originalordner bleiben in Matrix und Docs als verboten markiert.

## 13. Why this does not touch Track A

Keine Änderungen an `app_main.py`, Legacy-UI oder Internal Launcher. Track-A-Protection-Tests bleiben Teil der Abnahmebasis.

## 14. Why this does not touch processing-core

Keine Imports/Änderungen an `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, `run.py`.

## 15. Tests added/updated

Hinzugefügt:

- `tests/test_ui_v2_pilot_acceptance_gate.py`

Aktualisiert:

- `tests/test_ui_v2_onboarding_readiness.py` (Next-Step = Final Release Gate)

Code:

- `invoice_tool/ui_v2/pilot_acceptance.py` (neu)
- `invoice_tool/ui_v2/onboarding.py` (Next-Step / Acceptance-Done)
- `invoice_tool/ui_v2/pages/workspace.py` (Next-Step-Bindung)

## 16. Tests run and results

Focused:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_pilot_acceptance_gate.py \
  tests/test_ui_v2_onboarding_readiness.py \
  tests/test_ui_v2_copied_real_data_validation.py \
  tests/test_ui_v2_synthetic_e2e_product_flow.py \
  tests/test_ui_v2_export_reporting.py \
  tests/test_track_a_internal_app_protection.py
```

Ergebnis: **85 passed**.

Vollständig Track B:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Ergebnis: **394 passed, 44 skipped**.

## 17. Generalization confirmation

- lokale Pilotabnahme, nicht SaaS-ready
- Sandbox/Kopien only
- produktive Verarbeitung blockiert
- Exportvorschau only
- kein DATEV-/Cloud-Produktivclaim
- Originalordner verboten
- keine privaten Defaults
- Track A getrennt
- Processing-Core unberührt

## 18. Current progress

- Prompt 11/12 complete: yes (nach erfolgreichem Commit/Push)
- Remaining prompts: 1

## 19. Remaining gap

Finaler Release-Gate (Produktversion-1-Finalisierung).

## 20. Exact next task recommendation

`KI_RECHNUNGEN_PRODUCT_VERSION_1_FINALIZATION_AND_RELEASE_GATE_01`
