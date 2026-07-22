# Track B — Pilot Limitations (lokale Pilotversion)

Stand: 2026-07-22  
Geltungsbereich: Track-B UI-v2 nach Pilot-Readiness-Acceptance-Gate.

## Nicht SaaS-ready

Diese Version ist eine lokale Pilotversion.  
Login, Mandanten, Abrechnung und Cloud-Produktfunktionen sind nicht enthalten und nicht freigegeben.

## Keine produktive Verarbeitung

Produktive Belegverarbeitung ist blockiert.  
Es gibt keinen Produktiv-Ausführungs-Schalter und keine Produktivfreigabe über Track B.

## Keine Originalordner-Nutzung

Originalordner dürfen nicht als Eingang verwendet, gescannt oder mutiert werden.  
Erlaubt sind nur Sandbox-Pfade mit kopierten Testdaten.

## Kein DATEV-/Cloud-Produktivexport

Export ist eine Vorschau aus echten Laufergebnissen.  
Kein produktiver DATEV-Export, kein Cloud-Produktivexport, keine buchhalterische Freigabe.

## Review für unklare Fälle erforderlich

Unklare Fälle bleiben zur manuellen Prüfung.  
Prüfung ist kein automatischer Buchungsfreigabe-Schritt.  
Dateinamen sind keine Belegwahrheit.

## Track A getrennt

Track A (interne/legacy App) bleibt getrennt und unverändert geschützt.  
Track B ersetzt Track A nicht.

## Processing-Core unberührt

`processing`, `routing`, `routing_guards`, `classification`, `target_routing` und `run` wurden in diesem Gate nicht geändert.

## Nur Sandbox / Kopien

- Sandbox-Gate und Sandbox-Ausführungsgrenze gelten.
- Copied-realistic Validation und Synthetic E2E decken den Pilotfluss ab.
- Keine realen Rechnungsordner, kein OCR/AI in der Abnahmebasis dieses Gates.

## Keine steuer-/rechtliche Abhängigkeit

Diese Pilotversion ersetzt keine steuerliche, rechtliche oder buchhalterische Prüfung.  
Keine Garantie für produktive Belegklassifikation.

## Verbleibender Schritt

Finaler Release-Gate:  
`KI_RECHNUNGEN_PRODUCT_VERSION_1_FINALIZATION_AND_RELEASE_GATE_01`
