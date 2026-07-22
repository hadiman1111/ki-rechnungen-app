# Track B — Onboarding Notes (lokale Pilotversion)

Stand: 2026-07-22  
Geltungsbereich: Track-B UI-v2, lokale Pilotreife.

## Onboarding-Checkliste

1. Profil wählen oder vorbereiten.
2. Kopierte Testdaten verwenden.
3. Originalordner getrennt halten.
4. Sandbox-Validierung ausführen.
5. Unklare Fälle prüfen.
6. Exportvorschau lesen.

Nächster Schritt nach dieser Checkliste: **Pilot-Acceptance-Gate steht noch aus.**

## Safe First-Run Erklärung

Beim ersten Einstieg in den Arbeitsbereich gilt:

- „Lokale Pilotversion: Sandbox mit kopierten Daten.“
- „Produktive Verarbeitung ist noch nicht freigegeben.“
- „Originalordner bleiben geschützt.“
- „Export ist eine Vorschau, kein produktiver DATEV-/Cloud-Export.“
- „SaaS-Funktionen wie Login, Mandanten und Abrechnung sind nicht Teil dieser lokalen Pilotversion.“

Es gibt keinen Produktiv-Ausführungs-Schalter.  
Es gibt keinen automatischen Ordner-Scan.  
Es werden keine privaten Standardpfade gesetzt.

## Pilot-User Warning Text

Diese lokale Pilotversion dient der sicheren Orientierung und Sandbox-Validierung mit kopierten Daten.  
Sie ist **nicht** für produktive Belegverarbeitung, **nicht** für DATEV-/Cloud-Produktivexport und **nicht** als SaaS-Produktfreigabe gedacht.

## Forbidden Original-Folder Usage

- Originalordner nicht als Eingang wählen.
- Originale nicht scannen oder mutieren.
- Sandbox-Eingang und -Ausgabe unter einer expliziten Sandbox-Wurzel mit kopierten Daten halten.
- Originalordner bleiben geschützt und getrennt.

## Expected Review Behavior

- Prüfung ist ein manueller Kontrollfluss.
- Keine automatische Buchungsfreigabe.
- Unklare Fälle bleiben zur Prüfung.
- Ergebnisse, Prüffälle und Fehler bleiben getrennt.
- Dateinamen sind keine Belegwahrheit.

## Product Status Wording

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

Produktstufe: **Lokale Pilotreife — nicht SaaS-bereit.**

Keine privaten Daten, keine realen lokalen Pfade und keine nicht verifizierbaren Claims in diesen Notes.
