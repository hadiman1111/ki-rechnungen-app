# Produktversion 1 — Release Report (lokale Pilotversion)

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_PRODUCT_VERSION_1_FINALIZATION_AND_RELEASE_GATE_01`  
Masterplan: Prompt 12 of 12

## Release classification

**PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS**

Produktversion 1 ist als lokale Track-B-Pilotversion mit dokumentierten Limitationen freigegeben.  
Nicht freigegeben: SaaS-Reife, produktive Verarbeitung, DATEV-/Cloud-Produktivexport, Originalordner-Nutzung.

## Final commit

Finaler Release-Kandidat: der Prompt-12-Commit auf `main`, der dieses Release-Gate, die Release-Matrix (`invoice_tool/ui_v2/release_gate.py`), die zugehörigen Tests und diese Dokumentation enthält.

Basis vor dem Gate: `3c104b0d66dc289a8c996ca1300c4ae847819d48` (Pilot-Acceptance committed/pushed).

Release-Tag (wenn Gates bestehen): `product-v1-local-pilot-2026-07-22`.

## Accepted scope

1. Prompt 1–11 dokumentiert abgeschlossen; Prompt 12 schließt den Masterplan.
2. Pilot-Abnahme `ACCEPTED_LOCAL_PILOT` bleibt gültig.
3. Track-B-Einstieg getrennt von Track A.
4. Track-A-Schutz aktiv und Tests bestehen.
5. Processing-Core unberührt.
6. Sandbox-Gate und Sandbox-Ausführungsgrenze aktiv.
7. Synthetic E2E und copied-realistic Validation bestehen.
8. Review-Workflow, Profil-/Policy-Reife, Export-/Reporting-Vorschau bestehen.
9. Onboarding- und Limitations-Dokumentation vorhanden.
10. UI-v2-Testsuite als Freigabebasis.
11. Explizite Sperren: produktiv, Originalordner, SaaS, DATEV-/Cloud-Produktivexport, private Defaults.

## Safety boundaries

- Nur Sandbox mit kopierten Daten.
- Originalordner verboten/geschützt.
- Keine produktive Verarbeitung, kein Produktiv-Toggle.
- Export nur als Vorschau.
- Keine privaten Mandanten-/Pfad-Defaults.
- Track A unverändert und getrennt.
- Processing-Core unberührt.
- Keine realen Rechnungen, kein OCR/AI in diesem Gate.
- Kein SaaS-Ready-Claim, kein DATEV-/Cloud-Produktivexport-Claim.

## Test basis

Fokussiert:

- `tests/test_ui_v2_product_v1_release_gate.py`
- `tests/test_ui_v2_pilot_acceptance_gate.py`
- `tests/test_ui_v2_onboarding_readiness.py`
- `tests/test_ui_v2_copied_real_data_validation.py`
- `tests/test_ui_v2_synthetic_e2e_product_flow.py`
- `tests/test_ui_v2_export_reporting.py`
- `tests/test_track_a_internal_app_protection.py`

Vollständig Track B:

- `tests/test_ui_v2_*.py`
- `tests/test_saas_ui_v2_*.py`

Release-Helfer: `invoice_tool/ui_v2/release_gate.py`

## Prompt 1–12 completion table

| Prompt | Titel | Status |
|--------|-------|--------|
| 1 | Sandbox Processing Run Gate | complete |
| 2 | Sandbox Execution Wiring | complete |
| 3 | Review Workflow Completion | complete |
| 4 | Profile Policy Completion | complete |
| 5 | Export / Reporting Completion | complete |
| 6 | Track A Internal App Regression and Protection Gate | complete |
| 7 | Synthetic Track-B E2E Product Flow | complete |
| 8 | Sandbox Copied Real Data Validation | complete |
| 9 | Quality Fixes after Sandbox Validation | complete |
| 10 | Product Packaging and Onboarding Readiness | complete |
| 11 | Pilot Readiness Acceptance Gate | complete |
| 12 | Product Version 1 Finalization and Release Gate | complete |

Remaining prompts: **0**

## What Product Version 1 can do

- Lokale Track-B-Pilotnutzung unter Sandbox-/Kopie-Grenzen
- Sandbox-Gate und Ausführungsgrenze gegen unsichere/Originalpfade
- Synthetic E2E und copied-realistic Validierung (ohne reale Originale)
- Review-Workflow (Ergebnisse / Prüffälle / Fehler)
- Profil-/Policy-Reife ohne private Defaults
- Export-/Reporting-**Vorschau**
- Onboarding und ehrliche Statuskommunikation (nicht SaaS-bereit)
- Getrennten Track-B-Einstieg neben geschütztem Track A

## What Product Version 1 cannot do

- Produktive Verarbeitung von Originalbelegen
- Originalordner als Eingang nutzen, scannen oder mutieren
- SaaS-Login, Mandanten, Abrechnung
- Produktiven DATEV- oder Cloud-Export
- OCR/AI-Produktivlauf über dieses Gate
- Track A ersetzen oder ändern
- Processing-Core ändern
- Steuer-/rechtliche Freigabe ersetzen
- Produktionsgarantie für Belegklassifikation geben

## Track A protection status

Geschützt und getrennt. Track-A-Protection-Tests bleiben Teil der Freigabebasis.  
Keine Änderungen an Track-A-Einstieg oder Legacy-UI in diesem Gate.

## Processing-core status

Unberührt. Keine Änderungen an `processing`, `routing`, `routing_guards`, `classification`, `target_routing`, `run`.

## Known limitations

Siehe `docs/KI_RECHNUNGEN_TRACK_B_PILOT_LIMITATIONS_2026-07-22.md`.

Kurz: lokale Pilotreife ≠ SaaS-Reife; Sandbox/Kopien only; Review erforderlich; kein DATEV-/Cloud-Produktivexport; keine steuerliche Freigabe.

## Next phase

Siehe `docs/KI_RECHNUNGEN_NEXT_PHASE_AFTER_LOCAL_PILOT_2026-07-22.md`.

Empfohlener nächster Fokus nach dem Masterplan: kontrollierte echte OCR/AI-Sandbox-Validierung mit kopierten Daten — separat freizugeben, ohne Originalordner und ohne Produktivfreigabe.
