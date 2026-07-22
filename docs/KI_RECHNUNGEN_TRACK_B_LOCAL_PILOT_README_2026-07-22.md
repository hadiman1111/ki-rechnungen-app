# Track B — Lokale Pilotversion (README)

Stand: 2026-07-22  
Track: B (UI-v2)  
Produktstufe: lokale Pilotreife / Sandbox mit kopierten Daten — **nicht** SaaS-bereit.

## Was diese Version ist

Track B ist die getrennte UI-v2-Oberfläche für die lokale Pilotnutzung.  
Sie hilft, Sandbox-Läufe mit **kopierten** Testdaten zu verstehen, Prüffälle zu trennen und Exportvorschauen zu lesen.

Sie ist **keine** fertige Cloud-/SaaS-Produktversion und **keine** produktive Belegverarbeitung.

## Was sie kann

- Sandbox-Gate und Sandbox-Ausführungsgrenze gegen kopierte Testdaten vorbereiten
- Profile/Policy im Readiness-Rahmen bearbeiten (ohne private Defaults)
- Review-Workflow für unklare Fälle anzeigen (manuelle Prüfung, keine Buchungsfreigabe)
- Export-/Reporting-**Vorschau** aus echten Laufergebnissen erzeugen (lokal, JSON/CSV-Bericht)
- Ergebnisse, Prüffälle und Fehler getrennt darstellen
- Klar kommunizieren: Sandbox, Originalschutz, Produktivsperre, Nicht-SaaS

## Was sie nicht kann

- Produktive Verarbeitung von Originalbelegen
- Produktiven DATEV- oder Cloud-Export
- SaaS-Login, Mandanten, Abrechnung
- Automatische Ordner-Scans oder private Pfad-Defaults
- Dateinamen als Belegwahrheit verwenden
- Track A ersetzen oder ändern
- Processing-Core ändern

## Sicherheitsregeln

1. Nur kopierte Testdaten verwenden.
2. Originalordner bleiben geschützt und getrennt.
3. Produktive Verarbeitung ist nicht freigegeben.
4. Keine privaten Mandanten-/Pfad-Defaults.
5. Kein OCR/AI-Produktivlauf über diese Pilot-Oberfläche.
6. Track A und Track B bleiben getrennte Einstiege.

## Sandbox / Copy-only Workflow

1. Profil wählen oder vorbereiten.
2. Kopierte Testdaten bereitstellen (keine Originale als Eingang).
3. Originalordner getrennt halten.
4. Sandbox-Validierung ausführen.
5. Unklare Fälle im Prüfbereich lesen.
6. Exportvorschau lesen — nicht als produktiven Export behandeln.

## Ergebnisse / Prüfung / Fehler

| Bucket | Bedeutung |
|--------|-----------|
| Ergebnisse | Erkannte / zugeordnete Fälle aus dem Lauf |
| Prüffälle | Unklare Fälle zur **manuellen** Kontrolle |
| Fehler | Fehlgeschlagene Fälle, getrennt von Prüffällen |

Unklare Fälle bleiben zur Prüfung. Dateinamen sind keine Belegwahrheit.

## Exportvorschau

Export ist eine **Vorschau**, kein produktiver DATEV-/Cloud-Export.  
Berichte nutzen nur echte Laufergebnisse — ohne erfundene Produktivdaten und ohne Originalmutation.

## Track-A-Trennung

- Track A = interne/legacy App (`app_main.py` / Legacy-UI) — unverändert geschützt.
- Track B = UI-v2 (`app_ui_v2.py`) — parallele Pilotoberfläche.
- Einstiege und Verhalten bleiben getrennt.

## Bekannte Grenzen

- Lokale Pilotreife, nicht SaaS-Ready.
- Produktive Verarbeitung blockiert.
- Dry-Run ohne Dateiveränderung im lokalen Core ggf. weiterhin nicht verfügbar.
- Pilot-Acceptance-Gate und Final Release Gate stehen noch aus.

## Nächste Schritte

1. Pilot-Acceptance-Gate (`KI_RECHNUNGEN_PILOT_READINESS_ACCEPTANCE_GATE_01`)
2. Finaler Release-/Pilotfähigkeits-Gate (Prompt 12)

Keine realen Rechnungsordner, keine produktive Freigabe, kein SaaS-Claim in diesem Stand.
