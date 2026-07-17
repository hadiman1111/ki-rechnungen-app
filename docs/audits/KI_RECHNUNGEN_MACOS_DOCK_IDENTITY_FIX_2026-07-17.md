# KI-Rechnungen — macOS Dock-Identity Fix

**Task ID:** `KI_RECHNUNGEN_MACOS_DOCK_IDENTITY_FIX_01`  
**Datum:** 2026-07-17

## Diagnose

Der Dock-Wrapper (`scripts/macos_dock_launcher.c`) startete bisher per `execl` den
Python-/Flet-Launcher. Flet 0.85 öffnet danach einen separaten Desktop-Client
(`Flet.app`, Bundle-ID `com.appveyor.flet`, Fisch-Icon) über `open … -n`.

Dadurch entstanden zwei Dock-Identitäten:

1. `KI-Rechnungen.app` (Wrapper / angepinntes Icon)
2. `Flet.app` (sichtbares Fenster, Fisch-Symbol)

## Fix (kleinster stabiler Eingriff)

1. **Wrapper behält Dock-Identität:** Stub `fork`/`waitpid` statt Prozessersatz
   durch `execl` im Parent.
2. **Gebündelter Flet-View:** Build kopiert den Flet-0.85-Client nach
   `Contents/Resources/FletView/Flet.app`.
3. **Kein zweites Dock-Icon:** View-`Info.plist` setzt `LSUIElement=true`,
   Name/Identifier auf KI-Rechnungen-View, Icon ersetzt.
4. **`FLET_VIEW_PATH`:** Stub setzt zur Laufzeit den View-Pfad relativ zum
   laufenden `.app`-Executable (gilt auch für Desktop-Kopie).
5. **Entry-Patch:** `app_internal_launcher.py` lässt `FLET_VIEW_PATH` vor einem
   vorhandenen `build/macos/*.app` gewinnen (Flet-Default-Reihenfolge sonst
   umgekehrt — das war die konkrete Ursache des Fisch-Icons bei vorhandenem
   `build/macos`).

Entry bleibt `app_internal_launcher.py` / interner Launcher — kein Auto-Lauf,
keine Routing-/Profiländerung.

## Grenzen

- Kein vollständiger `flet build`/PyInstaller-Standalone; Python kommt weiter aus
  `.venv-flet085`.
- Dock-Identität des Fensters hängt an LSUIElement des View-Clients; bei
  macOS-/LaunchServices-Regressionen ggf. manueller Check nötig.
- Für eine echte Single-Binary-App wäre ein voller Flet-macOS-Build der nächste
  Schritt.

## Build

```bash
COPY_TO_DESKTOP=1 ./scripts/build_macos_dock_app.sh
# oder
./build_macos_app.sh
```
