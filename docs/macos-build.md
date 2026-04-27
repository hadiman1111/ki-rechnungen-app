# macOS-Build der KI-Rechnungen-App

## Was das Skript macht

Das Skript `scripts/build_macos_app.sh` prüft vor dem Build:

- ob du im richtigen Projekt bist
- ob die Desktop-UI-Datei vorhanden ist
- ob die virtuelle Umgebung `.venv` vorhanden ist
- ob `flet` in der virtuellen Umgebung verfügbar ist
- ob Xcode installiert ist
- ob `xcode-select` korrekt auf Xcode zeigt
- ob CocoaPods installiert ist

Wenn alle Voraussetzungen erfüllt sind, startet das Skript direkt den macOS-Build der Flet-App und sucht danach die erzeugte `.app`.

## Start

Im Projektordner ausführen:

```bash
bash scripts/build_macos_app.sh
```

Optional vorher ausführbar machen:

```bash
chmod +x scripts/build_macos_app.sh
./scripts/build_macos_app.sh
```

## Manuelle Voraussetzungen

Diese Punkte müssen vorher auf dem Mac grundsätzlich erfüllt sein:

1. Xcode ist installiert
2. `xcode-select` zeigt auf Xcode
3. CocoaPods ist installiert
4. Die Projekt-`.venv` existiert
5. Flet ist in der `.venv` installiert

## Typische Fehler

### Xcode fehlt

Meldung:

```text
Xcode ist nicht installiert. Bitte im App Store installieren.
```

Lösung:

- Xcode im App Store installieren
- danach Xcode einmal öffnen und die Zusatzkomponenten abschließen lassen

### xcode-select ist falsch gesetzt

Meldung:

```text
Der aktive Developer-Pfad ist nicht korrekt gesetzt.
```

Lösung:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

Danach das Skript erneut starten.

### CocoaPods fehlt

Meldung:

```text
CocoaPods fehlt. Installiere es z. B. mit: brew install cocoapods
```

Lösung:

```bash
brew install cocoapods
```

Danach das Skript erneut starten.

## Ergebnis

Nach erfolgreichem Build zeigt das Skript den Pfad zur erzeugten `.app` klar an.
