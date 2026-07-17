# KI-Rechnungen — FletView Assets.car Icon Branding Fix (2026-07-17)

Task: `KI_RECHNUNGEN_MACOS_FLETVIEW_ASSETSCAR_ICON_BRANDING_FIX_01`

## Ursache

`CFBundleIconName=AppIcon` lädt den Icon-Katalog aus `Assets.car`. Nur `AppIcon.icns` zu tauschen reichte nicht; der Flet-Fisch blieb im Katalog.

## Fix

`scripts/build_macos_dock_app.sh`:

1. `resources/app_icon.png` → alle Größen in `AppIcon.appiconset`
2. `actool` kompiliert neuen `Assets.car`
3. Gebrandeter `Assets.car` ersetzt den Flet-Katalog in der gebündelten FletView

## Nachweis

| Check | Ergebnis |
|---|---|
| Alter Fisch-MD5 | `07fbc7eb0c46c8b37922b3f33514d079` |
| Neuer Assets.car MD5 | `7d9eca2300b1dd475e64d19f5803e78c` |
| Dock-relevante Renditions (≥256) | SHA ≠ Fisch |
| actool-AppIcon.icns aus Katalog | Dokument-Icon (kein Fisch) |
| Laufender Prozess | `de.kirechnungen.view` / `ki-rechnungen-app` |
| Auto-Verarbeitung | nein |
| `/Users/hadi_neu/Desktop/RECHNUNGEN` | unverändert |

## PO-Hinweis Dock-Cache

Falls das Dock noch das alte Icon zeigt: App aus Dock entfernen, neu vom Desktop hineinziehen; optional `killall Dock`.
