# Track-B Simple User Review UI Polish (2026-07-24)

## Purpose

Nach dem Simple User Review Mode die Detailansicht visuell klarer machen:
Abschnitte besser trennen und den editierbaren Vorschau-Dateinamen vollständig lesbar machen.

## Screenshot issue

In der Live-GUI war die Review-Detailseite besser, aber:

1. Abschnitte wie „Was wurde erkannt?“, „Was schlägt die App vor?“, „Was muss ich entscheiden?“ wirkten noch zu wenig getrennt.
2. Das editierbare Vorschau-Dateiname-Feld war zu klein; lange Namen (z. B. `2026-05-23_er_Böttcher_AG_84,39_card.pdf`) wurden abgeschnitten.

## Section separation result

Detail-Abschnitte nutzen jetzt `review_section` / `review_card`:

- stärkerer Abstand
- Kartenrand + dezenter Hintergrund
- klarere Überschriften
- ruhigeres Scan-Layout

Betroffene Abschnitte:

- Was wurde erkannt?
- Was ist unklar?
- Was schlägt die App vor?
- Was muss ich entscheiden?
- Finalisierung / Vorschau-Sicherheit
- Technische Details (weiterhin eingeklappt)

## Filename field result

- Label oberhalb: **Vorschau-Dateiname** / **Dateiname bearbeiten**
- Vollbreite, mehrzeilig, ohne Clipping
- Helper: „Nur Vorschau — noch keine finale Datei geschrieben.“
- Optional: „Dateiname kopieren“
- Marker: `track_b_preview_filename_full_width_no_clip_v1`

## Safety result

- Kein produktives Processing
- Keine echten Rechnungsordner
- Kein `run_once`
- Kein Production-Final-Write
- Track A / Processing-Core unverändert
- Release-Tags unverändert
- Terminal-Oracle bleibt fachliches Regressionsgate

## Tests

`tests/test_track_b_simple_user_review_ui_polish.py` plus bestehende User-Mode-, Declutter-, Oracle- und Track-A-Suites.

## Oracle rerun

`KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python scripts/dev/track_b_automated_smoke_oracle.py`

## Layout marker

`track_b_simple_user_review_ui_polish_v1`

## Next step

Live-GUI kurz visuell prüfen (Abschnittskarten + langer Dateiname), danach nächster Track-B UX-/Produkt-Schritt gemäß PO.

## Product status after task

`TRACK_B_SIMPLE_USER_REVIEW_UI_POLISH_READY`
