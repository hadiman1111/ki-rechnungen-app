# KI-Rechnungen — macOS Dock-Relaunch Blank Window Fix (2026-07-17)

## Task

`KI_RECHNUNGEN_MACOS_DOCK_RELAUNCH_BLANK_WINDOW_FIX_01`

## Symptom

App öffnet beim ersten Start korrekt. Nach Beenden mit Dock-Icon im Dock
führt ein erneuter Dock-Klick zu einem hellblauen leeren Fenster.

## Ursache

1. Äußerer Wrapper (`de.kirechnungen.internal-launcher`) ist `LSUIElement=true`
   und erscheint nicht im Dock.
2. Sichtbares Dock-Icon ist die gebündelte FletView (`de.kirechnungen.view`).
3. Dock-Klick startet nur die FletView ohne Python/`app_internal_launcher.py`.
4. Ohne laufenden Flet-Server zeigt der Client ein leeres hellblaues Fenster.
5. `dock-app.log` erhält bei diesem Kaltstart keinen Outer-Stub-Eintrag.

## Fix (Strategie B)

`scripts/macos_fletview_bootstrap.c` als Executable der FletView:

- **Warm-Start** (`argc >= 3`; Flet 0.85 übergibt oft Temp-Pfade unter
  `/var/folders`, nicht `http://`): `execv` auf `ki-rechnungen-app.real`.
- **Kaltstart** (Dock/Finder, `argc == 1`): `open` der Outer-App
  → nativer Stub → Python → `app_internal_launcher.py` → FletView mit Args.

Build-Integration in `scripts/build_macos_dock_app.sh`:

1. Echtes Binary nach `*.real` umbenennen
2. Bootstrap als `CFBundleExecutable` kompilieren
3. Entitlements/Codesign wie zuvor

## Grenzen

- Kein Standalone-Build; weiterhin lokaler Wrapper + `.venv-flet085`
- Echte Dock-Interaktion (Pin behalten) erfordert manuelle PO-Prüfung
- Kein automatischer Verarbeitungslauf; keine Änderung realer Rechnungsordner

## Verifikation

- Erster Start über Desktop-`KI-Rechnungen.app`
- Simulierter zweiter Start über innere FletView (Dock-Äquivalent)
- Fokussierte Packaging-/Routing-Tests
