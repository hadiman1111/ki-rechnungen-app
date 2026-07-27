# Track-B Filename Pattern Builder + Safe Editing — 2026-07-27

Task: `KI_RECHNUNGEN_TRACK_B_FILENAME_PATTERN_BUILDER_AND_SAFE_EDITING_01`

## Goal

Dateinamenmuster und geplante Dateinamen sind bausteinbasiert, validiert und
nicht beliebig zerstörbar.

## Changes

- Neuer Builder `filename_builder.py` + Hilfen `filename_pattern.py`
- Eigener Text als sicherer Segment-Baustein
- Plus/Dropdown zum Hinzufügen von Bausteinen
- Live-Vorschau: „So sieht der Dateiname mit Beispieldaten aus“
- Validierung: `_er_er_`-Doppelung, leerer/unsicherer Text, `.pdf`
- Auto-Strip von custom `er`, wenn Dokumentart bereits `er` liefert
- Prüfung: strukturierte Korrektur (Werte/Bausteine), kein Roh-Freitext-Destroy
- Speichern blockiert ungültige Kandidaten

## Safety

- Preview/planning only — kein final write
- Kein run_once / productive processing
- Keine Track-A / Core-Änderungen
- Release-Tags unverändert

## Classification

`TRACK_B_FILENAME_PATTERN_BUILDER_AND_SAFE_EDITING_READY_COMMITTED_AND_PUSHED`
(nach Commit/Push)
