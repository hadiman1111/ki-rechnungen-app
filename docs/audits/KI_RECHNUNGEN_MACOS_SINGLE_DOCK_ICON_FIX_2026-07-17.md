# KI-Rechnungen — macOS Single Dock Icon Fix

**Task ID:** `KI_RECHNUNGEN_MACOS_SINGLE_DOCK_ICON_FIX_01`  
**Datum:** 2026-07-17

## Ursache des Fisch-Symbols

Beim Start von `KI-Rechnungen.app` startet der native Stub den Python-/Flet-Launcher.
Flet 0.85 öffnet danach einen separaten Desktop-Client per `open … -n`.

Priorität der Client-Auflösung:

1. `build/macos/*.app` im Projektverzeichnis
2. `FLET_VIEW_PATH`
3. Cache `~/.flet/client/.../Flet.app` (`com.appveyor.flet`)

Im aktuellen Worktree gewann `build/macos/ki-rechnungen-app.app`:
Name „KI-Rechnungen“, aber **Icon = Flet-Fisch**. Dadurch erschien ein zweites
Dock-Symbol mit Fisch-Grafik neben dem Wrapper.

## Warum der vorherige LSUIElement/FletView-Ansatz scheiterte

Commit `5f2e065` setzte `LSUIElement=true` am **View-Client** und signierte ad-hoc
ohne übernommene Entitlements. Folgen:

- Fenster-/Dock-Verhalten unzuverlässig („App startet scheinbar nicht“)
- File-Picker: `ENTITLEMENT_NOT_FOUND`
- intermittierende TCC-/Desktop-Zugriffsprobleme

## Gewählter Fix

1. Gebündelter Client unter `Contents/Resources/FletView/KI-Rechnungen.app`
2. Branding: Name/Icon/Bundle `de.kirechnungen.view`, **kein** LSUIElement am View
3. Entitlements der Quelle beim Re-Signieren erhalten
4. Äußerer Wrapper: `LSUIElement=true` (Stub bleibt dock-unsichtbar)
5. Stub setzt `FLET_VIEW_PATH`; Entry bevorzugt ihn gegenüber `build/macos`
6. Startmodell bleibt `execl` (wie nach dem erfolgreichen Rollback)

Akzeptiertes Modell: Das sichtbare Dock-Icon ist der gebrandete Flet-View
namens „KI-Rechnungen“, nicht der Stub.

## Build

```bash
COPY_TO_DESKTOP=1 ./scripts/build_macos_dock_app.sh
```
