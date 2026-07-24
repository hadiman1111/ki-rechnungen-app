# Track-B Review Accordion Layout (2026-07-24)

## Purpose

Die Track-B Simple-User-Review-Liste („Zur Prüfung“) als Inline-Akkordeon
strukturieren: kompakte Übersichtskarten zuerst, Details erst auf Klick
direkt unter dem jeweiligen Dokument.

## Previous list/detail problem

Bisher zeigte die Liste zu viele Sekundärfelder und die Detailansicht lag
nach der gesamten Dokumentliste. Nutzer mussten erst durch alle Einträge
scrollen, bevor die Details zum gewählten Beleg sichtbar wurden.

## New compact card behavior

Jede Karte zeigt zunächst nur:

- Dokumentname / Lieferant (oder Originaldateiname)
- Datum
- Betrag
- Aktion „Details öffnen“ / „Details schließen“

Keine Roh-Debug-Felder in der eingeklappten Übersicht.

## Accordion behavior

Single-open:

- Maximal ein Dokument gleichzeitig geöffnet
- Öffnen eines anderen Dokuments schließt das vorherige
- Zustand: `open_review_item_id` (UI-only, in-memory)

## Inline detail behavior

Geöffnete Details erscheinen unmittelbar unter der gewählten Karte und
wiederverwenden die Simple-User-Review-Abschnitte:

- Was wurde erkannt?
- Was ist unklar?
- Was schlägt die App vor?
- Was muss ich entscheiden?
- Finalisierung / Vorschau-Sicherheit
- Technische Details (eingeklappt)

## Active highlight result

Aktive/geöffnete Karten nutzen:

- dezenter Hintergrund (`COLOR_PRIMARY_SUBTLE`)
- stärkerer Rahmen / Akzentstreifen
- Marker: `review_card_active_highlight`

## Distinct detail background result

Der Detailbereich ist visuell abgesetzt:

- `COLOR_SURFACE_ALT`
- stärkerer Border
- Padding / Spacing / abgerundete Karte
- Marker: `detail_panel_distinct_background`, `inline_detail_under_selected_card`

## Safety result

- Kein produktives Processing
- Keine echten Rechnungsordner
- Kein `run_once`
- Kein Production-Final-Write
- Track A / Processing-Core unverändert
- Release-Tags unverändert
- Terminal-Oracle bleibt fachliches Regressionsgate

## Tests

`tests/test_track_b_review_accordion_layout.py` plus bestehende Polish-,
User-Mode-, Declutter-, Oracle- und Track-A-Suites.

## Oracle rerun

`KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python scripts/dev/track_b_automated_smoke_oracle.py`

## No productive processing

Nur UI-v2-Präsentation; Fachlogik unverändert.

## No real invoice folders

Keine Pfade zu echten Rechnungsordnern eingeführt.

## No Track A / Core changes

Geschützte Track-A-UI- und Processing-Core-Dateien wurden nicht geändert.

## Release tags unchanged

Keine Tag-Änderungen in diesem Schritt.

## Layout marker

`track_b_review_accordion_layout_v1`

## Next step

Live-GUI kurz visuell prüfen (Akkordeon, aktive Karte, abgesetzter Detailbereich),
danach nächster Track-B UX-/Produkt-Schritt gemäß PO.

## Product status after task

`TRACK_B_REVIEW_ACCORDION_LAYOUT_READY`
