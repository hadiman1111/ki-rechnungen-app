# Produktversion 1 — Release Notes (lokale Pilotversion)

Stand: 2026-07-22  
Klassifikation: **PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS**  
Tag (wenn gesetzt): `product-v1-local-pilot-2026-07-22`

## Kurzfassung

Track B (UI-v2) ist als **lokale Pilotversion mit Limitationen** freigegeben.  
Prompt 1–12 des Masterplans bis Produktversion 1 / lokale Pilotfähigkeit sind abgeschlossen.

Dies ist **keine** SaaS-Produktfreigabe und **keine** produktive Belegverarbeitung.

## Neue Track-B-Fähigkeiten (Masterplan-Ergebnis)

- Sandbox Processing Gate und Sandbox-Ausführungswerkzeuge
- Review-Workflow mit getrennten Buckets (Ergebnisse / Prüfung / Fehler)
- Profil-/Policy-Reife ohne private Defaults
- Export-/Reporting-Vorschau (kein Produktivexport)
- Track-A-Schutzgate und getrennte Einstiege
- Synthetic E2E und copied-realistic Sandbox-Validierung
- Packaging-/Onboarding-Status für lokale Pilotnutzung
- Formale Pilot-Abnahme und finaler Release-Gate mit Release-Matrix

## Lokale Pilotregeln

1. Nur kopierte Testdaten in der Sandbox verwenden.
2. Originalordner nicht als Eingang wählen.
3. Produktive Verarbeitung nicht erwarten und nicht erzwingen.
4. Exportvorschau nicht als DATEV-/Cloud-Produktivexport behandeln.
5. Unklare Fälle manuell prüfen.
6. Dateinamen nicht als Belegwahrheit nutzen.
7. Track A und Track B getrennt belassen.
8. Keine steuer-/rechtliche Abhängigkeit von dieser Version.

## Sicherheitswarnungen

- Originalordner bleiben geschützt und verboten.
- Kein Produktiv-Ausführungs-Schalter.
- Keine realen Rechnungsordner in diesem Release-Gate.
- Kein OCR/AI in diesem Release-Gate.
- Processing-Core unverändert; Track A unverändert.

## Non-Goals

- SaaS-Reife (Login, Mandant, Abrechnung, Cloud-Produkt)
- Produktive Originalordner-Verarbeitung
- DATEV-/Cloud-Produktivexport
- macOS-App-Build in diesem Task
- Steuer-/rechtliche Freigabe
- Garantie produktiver Belegklassifikation

## Known limitations

Details: `docs/KI_RECHNUNGEN_TRACK_B_PILOT_LIMITATIONS_2026-07-22.md`

## Explizite Nicht-Claims

- **Kein** SaaS-Ready-Claim
- **Kein** produktiver Verarbeitungs-Claim
- **Kein** DATEV-/Cloud-Produktivexport-Claim
- **Kein** Originalordner-Freigabe-Claim
