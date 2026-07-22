# Product Packaging and Onboarding Readiness

## 1. Task ID

`KI_RECHNUNGEN_PRODUCT_PACKAGING_AND_ONBOARDING_READINESS_01`

## 2. Masterplan position

Prompt 10 of 12 bis Produktversion 1 / lokale Pilotfähigkeit.

## 3. Purpose

Track-B UI-v2 aus Nutzersicht pilotfähig machen: lokale Produktkommunikation und Onboarding, ohne distributables Binary, ohne SaaS-Claim, ohne produktive Verarbeitung.

## 4. What changed

- Neu: `invoice_tool/ui_v2/onboarding.py` (ProductReadinessStage, Checklist, Capability Matrix, LocalPilotReadinessViewModel).
- Workspace: Onboarding-/Status-Panel mit Pflichttexten, Checkliste und Next-Step.
- Settings: Capability Matrix + ehrliche Produktstatus-Zeilen (lokal/pilot, nicht SaaS).
- Docs: Local Pilot README + Onboarding Notes.
- Tests: `tests/test_ui_v2_onboarding_readiness.py` plus Anpassungen an Quality/Settings/Workspace-Contract.

## 5. Onboarding model behavior

- Stage = `local_pilot_readiness` (nicht SaaS-ready).
- Statuslinien: lokale Pilotversion / Sandbox mit kopierten Daten, Produktivsperre, Originalschutz, Exportvorschau, SaaS nicht enthalten.
- Checkliste: Profil, kopierte Daten, Originale getrennt, Sandbox-Validierung, Review, Exportvorschau.
- Next step: Pilot-Acceptance-Gate steht noch aus.
- Kein Produktiv-Toggle, keine privaten Defaults, Dateiname nicht Source of Truth.

## 6. Workspace onboarding behavior

- Abschnitt „Lokale Pilotversion / Onboarding“ oberhalb der Ordnerauswahl.
- Zeigt die fünf Pflichtstatuslinien, die sechs Checklistenpunkte und den Next-Step.
- Impliziert weder SaaS-Ready noch produktiven Export.

## 7. Settings/status behavior

Capability Matrix:

| Fähigkeit | Status |
|-----------|--------|
| Sandbox-Gate | bereit |
| Sandbox-Ausführungsgrenze | bereit |
| Prüfungs-Workflow | bereit |
| Profil-/Policy-Reife | bereit |
| Export-/Reporting-Vorschau | Vorschau bereit |
| Track-A-Schutz | verifiziert |
| Produktive Verarbeitung | blockiert |
| SaaS Login/Mandant/Abrechnung | nicht enthalten |

Kein Produktiv-Toggle, kein SaaS-Ready-Claim, kein DATEV-Produktiv-Claim.

## 8. Documentation created

- `docs/KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_README_2026-07-22.md`
- `docs/KI_RECHNUNGEN_TRACK_B_ONBOARDING_NOTES_2026-07-22.md`
- dieses Audit

## 9. Local pilot capability matrix

Siehe Abschnitt 7. Produktstufe: lokale Pilotreife — nicht SaaS-bereit.

## 10. Explicit non-goals

- no SaaS readiness
- no productive processing
- no productive DATEV/cloud export
- no original folder use
- no macOS app build
- no OCR/AI
- no processing-core change
- no Track-A behavior change

## 11. Why this does not process original real PDFs

Nur Copy-/View-Model-/Doc-/Test-Änderungen in UI-v2. Keine Live-Core-Calls, kein OCR/AI, keine PDF-IO außerhalb bestehender Stub-/tmp_path-Pfade.

## 12. Why this does not touch real invoice folders

Keine Pfad-Defaults, kein Ordner-Scan, keine Writes außerhalb pytest `tmp_path`. Originalordner bleiben geschützt kommuniziert.

## 13. Why this does not touch Track A

Keine Änderungen an `app_main.py`, Legacy-UI oder Internal Launcher. Track-A-Protection-Tests bleiben grün.

## 14. Why this does not touch processing-core

Keine Imports/Änderungen an `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, `run.py`.

## 15. Tests added/updated

Hinzugefügt:

- `tests/test_ui_v2_onboarding_readiness.py`

Aktualisiert:

- `tests/test_ui_v2_quality_after_sandbox_validation.py`
- `tests/test_ui_v2_settings_navigation.py`
- `tests/test_ui_v2_workspace_processing_contract.py`

## 16. Tests run and results

Focused:

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_onboarding_readiness.py \
  tests/test_ui_v2_quality_after_sandbox_validation.py \
  tests/test_ui_v2_copied_real_data_validation.py \
  tests/test_ui_v2_export_reporting.py \
  tests/test_track_a_internal_app_protection.py
```

Ergebnis: 67 passed.

All Track-B UI-v2:

```text
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Ergebnis: 380 passed, 44 skipped.

## 17. Generalization confirmation

- lokale Pilot-/Sandbox-Kommunikation, nicht SaaS-ready
- keine privaten Tokens (Hadi/SOMAA/Bismarck/AMEX/voba/Desktop/`/Users`)
- kein Produktiv-Toggle
- kein DATEV-/Cloud-Produktiv-Claim
- kein Filename-as-Truth
- kein Folder-Scan / keine Originalmutation
- Track A und Processing-Core unberührt

## 18. Current progress

- Prompt 10/12 complete: **yes**
- Remaining prompts: **2**

## 19. Remaining gaps

- pilot acceptance
- final release gate

## 20. Exact next task recommendation

`KI_RECHNUNGEN_PILOT_READINESS_ACCEPTANCE_GATE_01`
