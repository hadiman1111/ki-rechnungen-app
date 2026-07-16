# KI-Rechnungen — macOS Dock-App Packaging

**Task ID:** `KI_RECHNUNGEN_MACOS_DOCK_APP_PACKAGING_01`  
**Datum:** 2026-07-16

## Ziel

Lokale macOS-App mit Dock-Namen „KI-Rechnungen“, die den bestehenden internen Launcher öffnet — ohne Terminalpflicht und ohne automatischen Verarbeitungslauf.

## Gewählter Weg

**C — Minimaler nativer macOS-App-Wrapper**

- `scripts/build_macos_dock_app.sh` erzeugt `dist/KI-Rechnungen.app`
- Native Stub: `scripts/macos_dock_launcher.c` (Mach-O arm64)
- Entry: `.venv-flet085/bin/python` → `app_internal_launcher.py`
  (gleiche Entry-Kette wie `scripts/run_internal_launcher_flet085.sh`)
- Icon: `resources/app_icon.icns` / `resources/app_icon.png`
- Log: `~/Library/Logs/KI-Rechnungen/dock-app.log`

Nicht gewählt:

- Voller Flet-Standalone-Build (`scripts/build_macos_app.sh`) — zielt auf `app_main`/UI-v2, schwer, nicht Launcher-fokussiert
- PyInstaller — nicht installiert; Package-Install wäre GATE

## Build

```bash
cd "/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
./build_macos_app.sh
# optional Desktop-Kopie:
COPY_TO_DESKTOP=1 ./scripts/build_macos_dock_app.sh
```

## Smoke

- `open dist/KI-Rechnungen.app` → Prozess `app_internal_launcher.py` gestartet
- Kein Auto-Processing
- Keine Änderung produktiver Rechnungsordner im Rahmen dieses Tasks

## Grenzen

- Wrapper bindet absolute Projektpfade ein (Rebuild nötig nach Verschieben)
- `.venv-flet085` muss lokal vorhanden sein
- Beim ersten Start kann macOS Desktop-Zugriff anfordern (Projekt liegt auf dem Desktop)
- Generiertes `dist/*.app` wird nicht committed (`dist/` in `.gitignore`)
