# KI-Rechnungen — macOS Dock-Identity Fix (zurückgenommen)

**Task ID (Fix):** `KI_RECHNUNGEN_MACOS_DOCK_IDENTITY_FIX_01`  
**Task ID (Repair/Rollback):** `KI_RECHNUNGEN_MACOS_DOCK_IDENTITY_FIX_REPAIR_OR_SAFE_ROLLBACK_01`  
**Datum:** 2026-07-17

## Status

**ZURÜCKGENOMMEN / SAFE ROLLBACK** — App-Start hat Vorrang vor Single-Dock-Icon.

## Ursprüngliche Diagnose (Fix)

Der Dock-Wrapper (`scripts/macos_dock_launcher.c`) startete per `execl` den
Python-/Flet-Launcher. Flet 0.85 öffnet danach einen separaten Desktop-Client
(`Flet.app`, Bundle-ID `com.appveyor.flet`, Fisch-Icon) über `open … -n`.

Dadurch entstanden zwei Dock-Identitäten:

1. `KI-Rechnungen.app` (Wrapper / angepinntes Icon)
2. `Flet.app` (sichtbares Fenster, Fisch-Symbol)

## Was der Fix versuchte

1. Wrapper behält Dock-Identität (`fork`/`waitpid`)
2. Gebündelter Flet-View unter `Contents/Resources/FletView/`
3. `LSUIElement=true` am View-Client
4. `FLET_VIEW_PATH` vom Stub gesetzt
5. Entry-Patch in `app_internal_launcher.py` für Flet-Pfad-Priorität

## Warum zurückgenommen

Nach dem Fix startete die lokale App laut PO nicht mehr sichtbar („gar nichts“).
Log-/Diagnose-Befunde:

- Intermittierende TCC-/Desktop-Zugriffsfehler (`pyvenv.cfg` PermissionError,
  `app_internal_launcher.py nicht lesbar`)
- Gebündelter Flet-Client ohne nötige File-Picker-Entitlements
  (`ENTITLEMENT_NOT_FOUND`)
- `LSUIElement=true` machte das Fensterverhalten unzuverlässig / unsichtbar

Ein sicherer Schnellfix war in diesem Task nicht gegeben. Packaging-Verhalten
wurde auf den zuletzt funktionierenden Stand aus `origin/main` / `3fb70ca`
zurückgesetzt.

## Bewusst akzeptierter Zwischenstand

- App startet wieder über den einfachen Dock-Stub (`execl` → Python-Entry)
- Zusätzliches Flet-/Fisch-Symbol im Dock kann wieder auftreten
- Vollständige Single-Dock-Icon-Lösung bleibt späteres Standalone-Packaging-Ziel

## Build

```bash
COPY_TO_DESKTOP=1 ./scripts/build_macos_dock_app.sh
# oder
./build_macos_app.sh
```
