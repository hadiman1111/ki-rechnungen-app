# Track B — Local Pilot Acceptance Report

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_PILOT_READINESS_ACCEPTANCE_GATE_01`  
Masterplan: Prompt 11 of 12

## Acceptance decision

**ACCEPTED_LOCAL_PILOT** — Track B ist als lokale Pilotversion unter Sandbox-/Kopie-/Nicht-Produktiv-Grenzen abgenommen.

Produktstufe: lokale Pilotreife — nicht SaaS-bereit.  
Nicht abgenommen als SaaS-Produkt, nicht als produktive Belegverarbeitung, nicht als DATEV-/Cloud-Produktivexport.

## Accepted scope

1. Track-B-Einstieg getrennt von Track A (`app_ui_v2.py` vs. `app_main.py`).
2. Track-A-Schutztest besteht.
3. Sandbox-Gate blockiert unsichere/Originalpfade.
4. Sandbox-Ausführungsgrenze existiert.
5. Synthetischer E2E-Produktfluss besteht.
6. Copied-realistic Validation besteht.
7. Review-Workflow trennt Ergebnisse / Prüffälle / Fehler.
8. Profil-/Policy-Reife existiert (ohne private Defaults).
9. Export-/Reporting-Vorschau existiert.
10. Onboarding erklärt lokale Pilotversion / Sandbox only.
11. Produktive Verarbeitung bleibt blockiert.
12. Export ist Vorschau — kein DATEV-/Cloud-Produktivexport.
13. Kein SaaS-Ready-Claim.
14. Keine privaten Defaults.
15. Kein Processing-Core-Change in diesem Gate.
16. UI-v2-Testsuite als Abnahmebasis.

## Not accepted scope

1. Nicht SaaS-ready.
2. Kein Login / Mandant / Abrechnung.
3. Kein produktiver DATEV-/Cloud-Export.
4. Keine produktive Originalordner-Verarbeitung.
5. Keine echte OCR/AI-Validierung in diesem Gate.
6. Kein macOS-App-Build in diesem Task.
7. Keine steuer-/rechtliche Freigabe.
8. Keine Garantie für produktive Belegklassifikation.

## Safety boundaries

- Nur Sandbox mit kopierten Daten.
- Originalordner bleiben geschützt und getrennt.
- Keine produktive Verarbeitung, kein Produktiv-Toggle.
- Export nur als Vorschau.
- Keine privaten Mandanten-/Pfad-Defaults.
- Track A unverändert und getrennt.
- Processing-Core unberührt.
- Keine realen Rechnungen, kein OCR/AI in diesem Gate.

## Test basis

- `tests/test_ui_v2_pilot_acceptance_gate.py`
- `tests/test_ui_v2_onboarding_readiness.py`
- `tests/test_ui_v2_copied_real_data_validation.py`
- `tests/test_ui_v2_synthetic_e2e_product_flow.py`
- `tests/test_ui_v2_export_reporting.py`
- `tests/test_track_a_internal_app_protection.py`
- vollständige Track-B Suite: `tests/test_ui_v2_*.py`, `tests/test_saas_ui_v2_*.py`

Acceptance-Helfer: `invoice_tool/ui_v2/pilot_acceptance.py`

## Known limitations

Siehe `docs/KI_RECHNUNGEN_TRACK_B_PILOT_LIMITATIONS_2026-07-22.md`.

Kurz: lokale Pilotreife ≠ SaaS-Reife; Sandbox/Kopien only; Review für unklare Fälle erforderlich; keine steuerliche oder produktive Freigabe.

## Pilot user rules

1. Nur kopierte Testdaten verwenden.
2. Originalordner nicht als Eingang wählen.
3. Produktive Verarbeitung nicht erwarten und nicht erzwingen.
4. Exportvorschau nicht als DATEV-/Cloud-Produktivexport behandeln.
5. Unklare Fälle manuell prüfen.
6. Dateinamen nicht als Belegwahrheit nutzen.
7. Track A und Track B getrennt belassen.
8. Keine steuer-/rechtliche Abhängigkeit von dieser Pilotversion.

## Final release gate remaining

Verbleibend: Prompt 12 /  
`KI_RECHNUNGEN_PRODUCT_VERSION_1_FINALIZATION_AND_RELEASE_GATE_01`
