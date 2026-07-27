# Track B — UI-v2 Blank Blue Window Hotfix (2026-07-27)

## Symptom

Nach dem dreiteiligen Product-UX-Plan öffnete sich UI-v2 beim Start nur als
leeres hellblaues Fenster (keine Navigation, kein Arbeitsbereich).

## Ursachen

1. **Falsche Flet-Runtime:** Start mit `.venv` / System-Python (Flet 0.28)
   öffnete den gebündelten Flet-0.85-Client (`build/macos/ki-rechnungen-app.app`).
   Ohne kompatiblen Server bleibt der Client hellblau leer. Die In-Page-Diagnostik
   war dann nicht sichtbar.
2. **Shell-Stack-Layout:** `ft.Stack` mit absolut positionierten Kindern
   (`left`/`top`/`right`/`bottom`) kann in Flet 0.85 auf Größe 0 kollabieren —
   sichtbar bleibt nur der leere Client-Hintergrund.
3. **Lückenhafte Tests:** Bestehende Startup-Tests prüften Labels im Control-Tree,
   aber nicht zuverlässig „nicht-leeres `page.controls` + sichtbare Produkt-Navigation
   + Arbeitsbereich-Inhalt“ unter `DEV_DEFAULTS=1`.

## Fix

- `app_ui_v2.py`: Flet-Version **vor** `ft.run` prüfen; bei Flet < 0.85 sofort
  abbrechen (kein Fenster, kein leeres Blau).
- `shell.py`: Sidebar + Content als `ft.Row` (statt Stack+absolute).
- `app.py`: Nach Mount sichtbare Produkt-Shell asserten (Controls, Nav, Default-Seite).
- `tests/test_gui_startup.py`: Startup-/Render-Gate verschärft.

## Nicht geändert

Track A, Processing Core, `run_once`, reale Rechnungsordner, Release-Tags,
Produktivverarbeitung. Dev-Surfaces bleiben nur mit
`KI_RECHNUNGEN_UI_V2_SHOW_DEV_SURFACES=1` sichtbar.
