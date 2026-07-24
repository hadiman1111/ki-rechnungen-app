# Track-B Guided Review UX Cleanup (2026-07-24)

## Purpose

Die geöffnete Review-Detailansicht (Akkordeon) zu einem geführten
Prüfmodus machen: dokumentspezifische Gründe, Entscheidung zuerst,
Dateiname als Vorschau, Testwerkzeuge zurückgenommen.

## Screenshot-based issues

1. Detail wirkte zu technisch und visuell schwer.
2. Finalisierung / Dry-Run / Sandbox waren zu präsent.
3. Nutzerentscheidung war nicht dominant genug.
4. Dateiname erschien sofort als Editierfeld.
5. Böttcher-Kartenfall zeigte PayPal-Hinweise (Vertrauensbruch).

## Document-specific reason fix

`review_case_kind` + `derive_why_review_plain_german` leiten Gründe
ausschließlich aus den Feldern **dieses** Dokuments ab:

- PayPal-Hinweise nur bei `payment_field=paypal`
- Karten/AMEX nur bei Kartenzahlung
- fehlende Zahlungsart nur ohne Payment
- Storno nur bei Storno

Fremde `user_guidance`-Texte (z. B. PayPal auf Karte) werden nicht mehr
in die Nutzeroberfläche übernommen.

## Böttcher no-PayPal result

Böttcher/`card` zeigt:

- „Kartenzahlung erkannt, aber AMEX ist nicht belegt.“
- keine PayPal-Warnung

## Guided status panel

Oben im Detail: Status / Grund / Empfehlung in Klartext
(Marker `guided_status_panel_top`).

## Decision-first layout

Direkt danach: „Was muss ich entscheiden?“ mit Primary-/Secondary-Aktionen
(Marker `decision_first_panel`).

## Filename preview behavior

Standard: „Vorgeschlagener Dateiname“ + Text + Buttons
„Dateiname bearbeiten“ / „Dateiname kopieren“.

Editierfeld nur nach explizitem „Dateiname bearbeiten“.

## Test/tools collapse behavior

Dry-Run, Sandbox, Finalisierungsdetails und Dev-Tools unter
„Test & Nachweis“ (`initially_expanded=False`).

Sichtbare Safety-Zeile bleibt:

„Nur Vorschau — es wird nichts final geschrieben. Originale bleiben unverändert.“

## Safety result

- Kein produktives Processing
- Keine echten Rechnungsordner
- Kein `run_once`
- Kein Production-Final-Write
- Track A / Core unverändert
- Release-Tags unverändert
- Terminal-Oracle bleibt fachliches Regressionsgate

## Tests

`tests/test_track_b_guided_review_ux_cleanup.py` plus Accordion-, Polish-,
User-Mode-, Declutter-, Oracle- und Track-A-Suites.

## Oracle rerun

`KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python scripts/dev/track_b_automated_smoke_oracle.py`

## No productive processing / no real invoice folders

Nur UI/UX und nutzerseitige Begründungstexte.

## No Track A / Core changes

Geschützte Dateien unverändert.

## Release tags unchanged

Keine Tag-Änderungen.

## Next step

Live-GUI kurz prüfen (Böttcher ohne PayPal, Decision-first, Dateiname-Vorschau),
danach nächster Track-B Produkt-Schritt gemäß PO.

## Product status after task

`TRACK_B_GUIDED_REVIEW_UX_CLEANUP_READY`
