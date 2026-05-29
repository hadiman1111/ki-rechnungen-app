# UI Target Concept – PDF-Dokumentenwerkzeug

Stand: Mai 2026  
Status: Zieldokument – kein Implementierungsauftrag

---

## 1. Produkt-UI-Prinzip

### Von der Launcher-App zur erweiterbaren Dokumenten-Workbench

Das Produkt begann als einfacher Launcher für Rechnungsläufe: zwei Ordner auswählen,
einen Lauf starten, Ergebnis prüfen. Dieser Kern bleibt. Die Produktrichtung hat sich aber
weiterentwickelt: Das System soll langfristig **beliebige PDF-Dokumente** verarbeiten können –
Rechnungen sind der erste stabile Anwendungsfall, nicht das einzige Ziel.

Die UI muss diese Erweiterung **architektonisch vorbereiten**, ohne sie sofort zu bauen.
Das bedeutet: Die Oberfläche soll erweiterbar aussehen und sein, ohne heute mehr zu zeigen,
als tatsächlich funktioniert.

### Zentraler Benutzerfluss

Der Fluss **Eingang → Verarbeiten → Ausgang** ist das unveränderliche Kernprinzip:

```
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────────┐
│   EINGANG        │────▶│     VERARBEITEN      │────▶│   AUSGANG            │
│   Quellordner    │     │  Verarbeitungsprofil │     │  Ergebnisordner      │
│  (Originale,     │     │  Lauf starten        │     │  Report / Prüfbedarf │
│   unverändert)   │     │  Status anzeigen     │     │  Finder öffnen       │
└─────────────────┘     └─────────────────────┘     └──────────────────────┘
```

Dieser Fluss muss in der UI sichtbar und eindeutig sein – entweder als horizontale Schrittfolge
oder als klar benannte Bereiche auf einem Scrollscreen.

### Prinzip der gestaffelten Komplexität

Die UI bedient zwei Nutzertypen mit denselben Steuerelementen, aber unterschiedlicher Tiefe:

| Nutzertyp | Sieht | Tut |
|-----------|-------|-----|
| Einfacher Nutzer | Quellordner, Ausgabeordner, „Lauf starten", Statusanzeige | Lauf starten und Ergebnis prüfen |
| Erweiterter Nutzer | Zusätzlich: aktives Verarbeitungsprofil, Profilpfad, Preset-Name, Trace-Dateien | Profile konfigurieren, Reports analysieren, Profilpfad anpassen |

**Umsetzungsprinzip:** Profildetails, Trace-Links und erweiterte Einstellungen werden in
einklappbaren Bereichen oder einem separaten Screen zugänglich gemacht – nicht versteckt,
aber auch nicht im Vordergrund.

---

## 2. Aktueller MVP-UI-Umfang

Die folgenden Elemente sollten jetzt oder sehr bald in der UI unterstützt werden.
Sie spiegeln das wider, was in `gui.py` bereits vorhanden ist oder direkt ergänzt werden kann.

### 2.1 Quellordner (Eingang)

- Textfeld mit aktuell konfiguriertem Pfad (vorausgefüllt aus `invoice_config.json`)
- Ordnerauswahl-Button (Betriebssystem-Dialog)
- „Im Finder öffnen"-Aktion
- **Originalschutz-Hinweis** muss sichtbar bleiben (Originale werden nie verändert)

### 2.2 Ausgabeordner (Ausgang)

- Textfeld für den Basisordner für Laufunterordner
- Ordnerauswahl-Button
- „Im Finder öffnen"-Aktion (öffnet nach Lauf den letzten Run-Output-Ordner)

### 2.3 Lauf starten / Hauptaktion

- Primäre Schaltfläche, klar als Hauptaktion erkennbar
- Wird während des Laufs deaktiviert
- Läuft im Hintergrundthread; Status wird sofort angezeigt

### 2.4 Aktives Verarbeitungsprofil anzeigen

- Anzeige des aktiven Presets (Name aus `aktives_preset` in `invoice_config.json`)
- Anzeige des geladenen Profilpfads (`profile_config.local.json`)
- Grüne Farbe = Profil gefunden; Orange = kein Profil, nur Basisregeln
- Kein Editieren in dieser Ansicht (nur lesend)

### 2.5 Reportanzeige

- Statuszeile: „bereit" / „läuft …" / „fertig" / „Fehler"
- Lauf-Log (scrollbares Textfeld, mind. 10 Zeilen, read-only)
- Summary-Box mit Zahlen aus `report.json`:
  Processed, Documents, Duplicates, Unklar, Errors, System Fallbacks
- Volltext-Report aus `report.txt` (scrollbares read-only Textfeld)
- Hinweis auf Pfad des geladenen Reports

### 2.6 Prüfbedarf-Anzeige (Review Cases)

- Eigener roter Container, **immer oberhalb des Volltexts**
- Inhalt aus dem `PRÜFBEDARF:`-Block des Reports extrahiert
- Muss sofort auffallen – **darf nicht in einem langen Report versteckt werden**
- „PRÜFBEDARF: keiner" → Container ausgeblendet
- Enthält Prüfbedarf → Container sichtbar, rot umrandet

### 2.7 Letzten Report öffnen

- Schaltfläche „Letzten Report öffnen" → öffnet `report.txt` im System-Viewer

### 2.8 Status zurücksetzen

- Beim nächsten Laufstart wird der Report-Bereich automatisch geleert (implizit vorhanden)
- Kein expliziter Reset-Button aktuell notwendig, aber im Layout vorgesehen

### 2.9 Originalschutz-Hinweis

- Muss dauerhaft sichtbar sein – entweder als Label neben dem Quellordner-Feld
  oder als permanenter Hinweis-Text in der App
- Text: „Originaldateien werden nie verändert" oder ähnlich prägnant
- Aktuell nur im `hint_text` des Textfelds vorhanden – **sollte als permanenter Text ergänzt werden**

---

## 3. Zukünftiger UI-Umfang

Die folgenden Funktionen müssen vorbereitet, aber **nicht sofort implementiert** werden.
Sie werden erst sinnvoll, wenn die zugrundeliegende Backend-Logik end-to-end validiert ist.

### 3.1 Verarbeitungsprofile (Anzeige)

- Lesende Profilanzeige: welche Profil-Bereiche sind aktiv, welche Ordner/Konten/Adressen
  sind konfiguriert
- Nur anzeigen, kein Editieren (read-only Profilansicht)
- Vorbedingung: `document_profiles` end-to-end validiert

### 3.2 Dokumenttypen

- Anzeige aktiver Dokumenttyp-Profile (aus `document_profiles`)
- Welche Typen sind aktiv, welche Erkennungsmerkmale, welche Zielordner
- Nur wenn `document_profiles`-Compiler validiert ist

### 3.3 Ordner-Mapping pro Dokumenttyp

- Zeigt: „Rechnungen → /ai/, Verträge → /vertraege/"
- Lesend, aus `folders`-Konfiguration des Profils
- Kein Editor im MVP

### 3.4 Dateinamensschemas

- Anzeige des aktiven Templates pro Dokumenttyp
- Beispiel-Ausgabe für einen Musterdateinamen
- Kein Inline-Editor; Änderungen erfolgen über Profil-Datei

### 3.5 Prüfregeln / Schwellwerte

- Anzeige von `confidence_threshold` und `review_policy` pro Dokumenttyp
- Lesend; keine UI-Änderungen vor Validierung der Logik

### 3.6 Vorschau / Probelauf (Dry Run)

- **Darf nicht als Button vorhanden sein, solange kein funktionierender Dry-Run-Pfad existiert.**
- Wenn eine Vorschau-Funktion kommt: zeigt Dateinamen und Zielordner, ohne Dateien zu schreiben
- Muss explizit als „Vorschau – keine Änderungen" beschriftet sein
- Erst nach Implementierung des Dry-Run-Pfads in `run.py`

### 3.7 Profil-Import/Export

- Import: Profil aus Datei laden und aktivieren
- Export: aktuelles Profil + erzeugte Runtime-Regeln als Snapshot exportieren
- Erst sinnvoll wenn Profilpfad in der UI bearbeitbar ist

### 3.8 Trace/Report-Export

- Export von `decision_trace.jsonl`, `routing_summary.csv`, `report.json`
- Zugänglich über einen Drawer/Bereich nach dem Lauf
- Kein Editieren der Traces

---

## 4. Screen-Modell

Die App hat keine klassische Multi-Page-Navigation. Sie besteht aus einem Hauptscreen,
der zustandsbasiert verschiedene Inhalte zeigt.

### 4.1 Zustand: Start / Bereit

```
App-Titel
─────────────────────────────────────────
Profil-Info-Box (Preset + Profilpfad)
─────────────────────────────────────────
Quellordner-Zeile     [Ordner wählen] [Finder]
Ausgabeordner-Zeile   [Ordner wählen] [Finder]
─────────────────────────────────────────
[Lauf starten]    [Letzten Report öffnen]
─────────────────────────────────────────
Status: bereit  (blau)
─────────────────────────────────────────
Log: (leer)
─────────────────────────────────────────
Report: (leer)
```

**Originalschutz-Hinweis dauerhaft sichtbar.**

### 4.2 Zustand: Verarbeitung läuft

```
Status: läuft …  (orange)
[Lauf starten] – deaktiviert
Log: wächst mit jeder Zeile
Report: wird nach Abschluss befüllt
```

Keine Spinner-Animation erforderlich (Status-Text genügt für MVP).

### 4.3 Zustand: Abgeschlossen – kein Prüfbedarf

```
Status: fertig  (grün)
[Lauf starten] – wieder aktiv
Log: vollständige Ausgabe
Prüfbedarf: (nicht sichtbar)
Summary-Box: Zahlen aus report.json
Report-Text: vollständiger report.txt-Inhalt
[Letzten Report öffnen] – aktiv
```

### 4.4 Zustand: Abgeschlossen – mit Prüfbedarf

```
Status: fertig  (grün)
[Lauf starten] – wieder aktiv
─────────────────────────────────────────
PRÜFBEDARF                    ← roter Container, prominent
  [Liste der Prüffälle]
─────────────────────────────────────────
Summary-Box
Report-Text (vollständig, scrollbar)
```

Der Prüfbedarf-Container muss **vor** dem Summary und Report-Volltext stehen,
damit er nicht übersehen wird.

### 4.5 Zustand: Fehler

```
Status: Fehler  (rot)
[Lauf starten] – wieder aktiv
Log: Fehlermeldung sichtbar
Report: leer oder Teilbericht
```

Fehler werden im Log angezeigt. Kein Modal-Dialog notwendig.

### 4.6 Zukünftiger Screen: Profil lesen (read-only)

```
[← Zurück]
Verarbeitungsprofil: [Profilname]
─────────────────────────────────
Kategorien / Ordner
Konten & Zahlungswege
Dokumenttypen
Adressregeln
─────────────────────────────────
[Profil-Datei im Editor öffnen]
```

Nur lesend. Kein Formular, kein Speichern.  
Navigierbar über einen Informations-Button auf dem Hauptscreen.

### 4.7 Zukünftiger Screen: Profil bearbeiten (editierbar)

Erst implementieren, wenn das Profil-Datenmodell end-to-end validiert ist.  
Kein Freitexteditor für JSON – strukturiertes Formular mit validierten Feldern.  
Speichern nur auf explizite Nutzeraktion, mit Bestätigung.

### 4.8 Zukünftiger Bereich: Report/Trace-Drawer

Nach einem Lauf zugänglich. Zeigt:
- Pfad zu `report.txt`, `report.json`
- Pfad zu `decision_trace.jsonl`, `routing_summary.csv`
- Export-Aktion für Trace-Dateien

---

## 5. Design-System

> Dieser Abschnitt definiert Design-Tokens als Konzept.
> Nichts davon ist implementiert. Die Flet-UI verwendet derzeit
> `ft.ThemeMode.LIGHT` mit Material-Standard-Farben.

### 5.1 Farben

Farben dienen als **Orientierungs- und Statussignal**, nicht als dekorative Flächen.

| Token | Zweck | Orientierungswert |
|-------|-------|-------------------|
| `color.status.ready` | Status „bereit" | Blau (BLUE_700) |
| `color.status.running` | Status „läuft" | Orange (ORANGE_700) |
| `color.status.done` | Status „fertig" | Grün (GREEN_700) |
| `color.status.error` | Status „Fehler" | Rot (RED_700) |
| `color.review.background` | Prüfbedarf-Container Hintergrund | Hellrot (RED_50) |
| `color.review.border` | Prüfbedarf-Container Rahmen | Rot (RED_200) |
| `color.review.title` | Prüfbedarf-Überschrift | Rot (RED_700) |
| `color.profile.found` | Profil gefunden | Grün (GREEN_700) |
| `color.profile.missing` | Kein Profil | Orange (ORANGE_700) |
| `color.surface.info` | Info-Boxen (Preset, Summary) | Blau-Grau (BLUE_GREY_50) |
| `color.surface.info.border` | Rahmen für Info-Boxen | Blau-Grau (BLUE_GREY_100) |

**Wichtig:** Keine großen farbigen Hintergrundflächen für Layoutbereiche.
Farbe wird gezielt auf Statustexte, kleine Badges und Container-Ränder angewendet.

### 5.2 Typografie

| Anwendungsfall | Stil |
|---------------|------|
| App-Titel | Groß, Bold (size 30) |
| Abschnittsüberschriften | Medium, SemiBold (size 18) |
| Labeltexte | Normal, SemiBold (W_600) |
| Statustext | Normal, SemiBold (size 16, W_600) |
| Log/Report | Monospace oder festes Textfeld, read-only |
| Dateinamen / Pfade | Monospace, selektierbar |
| Zusammenfassung | Normal, kein Bold |
| Prüfbedarf-Überschrift | Bold, Rot (W_700) |

**Dateinamen und Pfade immer in Monospace** – sie werden kopiert und verglichen.

### 5.3 Abstände

| Ebene | Wert |
|-------|------|
| Seiten-Padding | 16 px |
| Zeilen-/Elementabstand | 10 px (Column spacing) |
| Innenabstand in Containern | 12 px |
| Innenabstand in Prüfbedarf-Box | 12 px |

### 5.4 Button-Hierarchie

| Ebene | Typ | Einsatz |
|-------|-----|---------|
| 1 – Primär | `ElevatedButton` | Lauf starten (einzige Primäraktion) |
| 2 – Sekundär | `OutlinedButton` | Finder öffnen, Report öffnen |
| 3 – Icon | `IconButton` | Ordner auswählen (Dateiauswahl) |
| 4 – Deaktiviert | `ElevatedButton` (disabled=True) | Lauf starten während des Laufs |

Nur eine Primäraktion pro Screen. Sekundäre Aktionen sind weniger prominent.

### 5.5 Container / Karten

| Typ | Einsatz |
|-----|---------|
| Info-Box (blau-grau) | Preset/Profil-Anzeige, Summary-Zahlen |
| Review-Box (rot) | Prüfbedarf – nur bei Prüffällen sichtbar |
| Scrollbares Textfeld | Log, Report-Volltext |
| Kein Card-Overlay | Kein visuelles „Karten-Stapel"-Layout im MVP |

### 5.6 Status-Badges

Für zukünftige Verwendung in Profil-Screens:

| Badge-Typ | Bedeutung |
|-----------|-----------|
| Grüner Badge | Profil aktiv / Feature implementiert |
| Orange Badge | Warnung / Fallback / Profil fehlt |
| Roter Badge | Fehler / Prüfbedarf |
| Grauer Badge | Deaktiviert / Feature noch nicht verfügbar |
| Blau-Grau Label | Informationstext ohne Zustandsbewertung |

### 5.7 Prüfbedarf / Fallback-Warnungen

- Der Prüfbedarf-Block ist **immer vor dem Volltextreport** positioniert
- Fallback-Pfade in Logs erscheinen als plain text im Log-Bereich
- Zukünftig: Fallback-Warnungen in einem eigenen Status-Badge oder einer Warning-Box
  (orange, analog zur Review-Box)

### 5.8 Dateinamen und Pfade

- Alle Pfadanzeigen: selektierbar (`selectable=True`)
- Alle Pfadanzeigen: Monospace-Schrift (zukünftig explizit als Token)
- Aktuell: `ft.Text(..., selectable=True)` – kein explizites Monospace-Styling

---

## 6. Terminologie

### 6.1 „Verarbeitungsprofil" – präziser deutscher Begriff

| Kontext | Begriff |
|---------|---------|
| Vollständige Bezeichnung | **Verarbeitungsprofil** |
| Kurz in der UI (Platzmangel) | **Profil** |
| Technisch im Code | `profile_config` / `DocumentProfile` |
| Im Dateinamen | `profile_config.local.json` |

**„Verarbeitungsprofil"** beschreibt präzise, was gemeint ist: ein Konfigurationsprofil,
das steuert, wie Dokumente verarbeitet werden (erkannt, umbenannt, sortiert).

### 6.2 Was „Profil" nicht bedeutet

- Kein Nutzerprofil im Sinne von Konto/Login
- Kein Benutzerprofil wie in Cloud-Diensten
- Kein „Account" oder „Session"
- Das Profil beschreibt **Dokumentverarbeitungsregeln**, nicht eine Person

**Konsequenz für die UI:** Keine Icons mit Personensilhouette oder Nutzer-Avatar für Profile.
Ein Einstellungsrad (⚙) oder Dokumentenstapel-Icon ist passender.

### 6.3 Weitere Begriffe

| Begriff | Bedeutung | Hinweis |
|---------|-----------|---------|
| Lauf | Einzelner Verarbeitungsdurchlauf | Eindeutige run_id (Timestamp) |
| Eingang | Quellordner mit Original-PDFs | Originale bleiben unverändert |
| Ausgang | Ausgabeordner / Run-Output-Ordner | Laufbezogene Unterordner |
| Prüfbedarf | Dokumente, die manuell geprüft werden müssen | Roter Container in der UI |
| Basisregeln | `office_rules.json` – systemseitig, stabil | Nicht durch Profil überschrieben |
| Laufregeln | `runtime_rules.json` – pro Lauf generiert | Nur für diesen Lauf gültig |
| Snapshot | Arbeitskopie der Originaldateien für diesen Lauf | Originale nie anfassen |

---

## 7. Implementierungs-Leitplanken

Die folgenden Regeln gelten für alle zukünftigen UI-Entwicklungsschritte:

### 7.1 Kein vollständiges UI-Redesign vor Backend-Validierung

> **Regel:** Kein vollständiger UI-Umbau, bevor `document_profiles` end-to-end validiert ist
> (Compiler → Runtime Rules → Verarbeitung → Report).

Begründung: Die UI muss reale Daten anzeigen. Solange die Backend-Logik noch nicht
end-to-end läuft, führt ein aufwändiges UI-Design zu Dead Code und Frustration.

### 7.2 Keine prominent platzierten nicht-verfügbaren Aktionen

> **Regel:** Buttons oder Aktionen, die noch nicht funktionieren, dürfen nicht prominent
> in der Hauptansicht erscheinen.

Erlaubte Ausnahmen:
- Deaktivierter Button mit erklärendem Tooltip: `"Vorschau – noch nicht verfügbar"`
- Greyed-out Element in einer Sekundäransicht
- Kein Platzhalter-Button im primären Aktionsbereich

### 7.3 Kein Vorschau-Button ohne funktionierenden Dry-Run-Pfad

> **Regel:** Es darf keinen „Vorschau"-Button geben, solange kein implementierter
> Dry-Run-Pfad in `run.py` existiert.

Begründung: Ein nicht-funktionaler Vorschau-Button verwirrt Nutzer und suggeriert
eine Sicherheitsfunktion, die es nicht gibt.

Erst wenn ein echter Dry-Run-Pfad implementiert ist:
- Button erscheint aktiv
- Button muss klar als „Vorschau – keine Änderungen" beschriftet sein
- Muss von „Lauf starten" visuell klar unterschieden sein

### 7.4 Prüfbedarf darf nicht versteckt werden

> **Regel:** Prüfbedarf-Fälle dürfen niemals im Volltextreport vergraben sein.

Umsetzung:
- Prüfbedarf-Container immer **oberhalb** des Report-Volltexts
- Roter Container auch bei nur einem Prüffall sichtbar
- Kein Einklappen oder Zusammenfalten des Prüfbedarf-Blocks im MVP

### 7.5 Originalschutz dauerhaft sichtbar

> **Regel:** Der Hinweis, dass Originaldateien niemals verändert werden, muss dauerhaft
> in der UI sichtbar sein.

Aktuell: Nur als `hint_text` im Textfeld – wird beim Eingeben verdeckt.  
Empfehlung: Permanenter Hinweis-Text unterhalb oder neben dem Quellordner-Feld.  
Dieser Hinweis ist ein Vertrauenselement, kein Kleingedrucktes.

---

## 8. Lückenanalyse: Konzept vs. aktuelle Implementierung

Geprüfte Datei: `invoice_tool/gui.py` (449 Zeilen, Stand Mai 2026)

### 8.1 Bereits vorhanden

| Konzept-Element | Status | Details |
|-----------------|--------|---------|
| Quellordner-Feld | ✅ vorhanden | `source_field`, FilePicker, Finder-Button |
| Ausgabeordner-Feld | ✅ vorhanden | `output_field`, FilePicker, Finder-Button |
| Lauf starten | ✅ vorhanden | `ElevatedButton` „Lauf starten", im Thread |
| Profil-Info-Box | ✅ vorhanden | Preset-Name + Profilpfad, grün/orange |
| Status-Anzeige | ✅ vorhanden | blau/orange/grün/rot |
| Lauf-Log | ✅ vorhanden | Scrollbares read-only Textfeld |
| Summary-Box | ✅ vorhanden | Zahlen aus `report.json` |
| Prüfbedarf-Container | ✅ vorhanden | Roter Container, vor Report-Text positioniert |
| Report-Volltext | ✅ vorhanden | Scrollbares read-only Textfeld |
| Letzten Report öffnen | ✅ vorhanden | `OutlinedButton` öffnet `report.txt` |
| Profil-Farbe (vorhanden/fehlend) | ✅ vorhanden | Grün / Orange |
| Prüfbedarf: kein → unsichtbar | ✅ vorhanden | `pruefbedarf_box.visible = False` |
| Prüfbedarf: vorhanden → sichtbar | ✅ vorhanden | Rot, extrahiert aus `report.txt` |
| Lauf deaktiviert während Lauf | ✅ vorhanden | `start_button.disabled = True` |

### 8.2 Fehlend – sollte bald ergänzt werden (low risk)

| Fehlendes Element | Risiko | Empfehlung |
|------------------|--------|------------|
| Originalschutz als permanenter Text | Niedrig | `ft.Text("Originaldateien werden nie verändert", ...)` neben Quellordner |
| Pfade in Monospace-Schrift | Niedrig | `font_family="monospace"` für `profile_label`, `latest_report_hint` |
| Vorschau des aktiven Profil-Namens (nicht nur Pfad) | Niedrig | `profile_label` zeigt Pfad; `preset_label` zeigt Preset – ausreichend für MVP |
| Klare Trennung Eingang/Verarbeiten/Ausgang | Niedrig | Abschnittstrenner oder Überschriften im Layout |
| Status „Fehler" mit Fallback-Hinweis | Niedrig | Roter Hinweistext im Log-Bereich ergänzen |

### 8.3 Fehlend – muss warten (abhängig von Backend)

| Fehlendes Element | Abhängigkeit | Warten auf |
|------------------|-------------|------------|
| Vorschau / Dry Run | `run.py` Dry-Run-Pfad | Implementierung in run.py |
| Profil-Anzeige-Screen (read-only) | Profil-Datenmodell stabil | document_profiles E2E |
| Dokumenttyp-Anzeige | `document_profiles` Compiler | document_profiles E2E |
| Ordner-Mapping pro Dokumenttyp | Compiler + Runtime | document_profiles E2E |
| Prüfregeln / Schwellwerte | Compiler + Runtime | document_profiles E2E |
| Profil-Import/Export in UI | Profilpfad-Wechsel | Nach E2E-Validierung |
| Trace/Report-Drawer | Trace-Daten normiert | Erst wenn trace nützlich für Nutzer |
| Profil-Editor (editierbar) | Vollständiges Formularkonzept | Weit nach E2E |
| Nutzerverständlicher Report | Trace-Aufbereitung | Weit nach E2E |

### 8.4 Kann als Low-Risk UI-Only-Verbesserung später ergänzt werden

| Verbesserung | Beschreibung |
|-------------|--------------|
| Permanenter Originalschutz-Hinweis | Ein `ft.Text`-Element; keine Logikänderung |
| Monospace für Pfade | `font_family`-Attribut; keine Logikänderung |
| Abschnittstrenner (Eingang/Ausgang/Bericht) | `ft.Divider()` + Überschriften; kein Logikeingriff |
| Status-Badge als farbiger Container statt Text | Rein visuell; keine Logikänderung |
| Tooltip für Profil-Info-Box | `tooltip=`-Attribut; keine Logikänderung |
| Window-Titel nach Lauf aktualisieren | `page.title = f"Fertig – {run_id}"` |
| Letzten Run-Ordner-Pfad als Hinweis anzeigen | `ft.Text` nach dem Lauf; keine Logikänderung |

---

## 9. Abschlussbericht

### A. Kurzfazit

Die aktuelle `gui.py` deckt den MVP-Kern vollständig ab: Ordnerauswahl, Lauf starten,
Status, Log, Prüfbedarf, Summary und Report sind vorhanden und korrekt implementiert.
Das Konzept der gestaffelten Komplexität ist im Grundsatz bereits umgesetzt (Profil-Info
ist vorhanden, aber nicht aufdringlich). Sieben kleine Low-Risk-Verbesserungen können ohne
Logikeingriff ergänzt werden. Alles Erweiterte (Profile-Screens, Dokumenttypen,
Vorschau) muss auf die Validierung von `document_profiles` end-to-end warten.

### B. Geprüfte Dateien

| Datei | Zweck |
|-------|-------|
| `invoice_tool/gui.py` | Flet-UI – vollständig analysiert |
| `invoice_tool/models.py` | `DocumentProfileRule`-Dataclass |
| `invoice_tool/config.py` | Profil-Loader |
| `invoice_tool/profile_compiler.py` | Compiler-Architektur |
| `invoice_tool/run.py` | Run Manager (Referenz) |
| `docs/MASTERPLAN_PDF_DOCUMENT_TOOL.md` | Strategischer Plan |
| `docs/roadmap/DOCUMENT_PROFILES_ARCHITECTURE.md` | Architekturbeziehungen |
| `profile_config.schema.json` | Schema-Überblick |
| `invoice_config.json` | App-Konfiguration |
| `pyproject.toml` | Paket-Struktur |

### C. Geänderte Dateien

Keine. Dieses Dokument dokumentiert das Zielkonzept ohne Codeänderungen.

### D. Wo das UI-Zielkonzept dokumentiert wurde

`docs/roadmap/UI_TARGET_CONCEPT.md` (diese Datei)

### E. Konflikte und Risiken

| Konflikt / Risiko | Bewertung |
|-------------------|-----------|
| `document_profiles`-Compiler in `profile_compiler.py` implementiert, aber in `MASTERPLAN` als noch nicht implementiert markiert | **Inkonsistenz in der Doku** – Masterplan (Zeile 357) und DOCUMENT_PROFILES_ARCHITECTURE.md (Zeile 194) sagen „Compiler noch nicht implementiert", während `profile_compiler.py` und `processing.py` bereits Compiler-Logik enthalten. Klärung empfohlen. |
| Vorschau-Button: Masterplan erwähnt Preview-Skript (`scripts/preview_profile_runtime_rules.py`) | Das ist ein CLI-Skript, kein UI-Pfad. Ein Vorschau-Button in der UI ist nicht erlaubt, bis ein UI-seitiger Dry-Run-Pfad existiert. |
| `profile_config.local.json` enthält aktuell keine `document_profiles`-Einträge | Kein Risiko – System verhält sich korrekt (leeres Array = Fallback auf Rechnungspfad). |
| `MASTERPLAN` beschreibt UI-Entwicklung als Schritt 7 – nach Run Manager, Runtime Rules, Preview, Compiler | Das stimmt mit dieser Konzeptdokumentation überein: UI-Erweiterungen warten auf Backend-Validierung. |

### F. Empfohlener nächster Implementierungsschritt

**Nächster Schritt: Sieben Low-Risk UI-Verbesserungen ohne Logikeingriff**

Reihenfolge nach Priorität:

1. **Permanenter Originalschutz-Hinweis** – `ft.Text("Originaldateien werden nie verändert", ...)` neben oder unterhalb des Quellordner-Felds
2. **Abschnittstrenner** – `ft.Divider()` und Überschriften zwischen Eingang / Verarbeiten / Ausgang / Bericht
3. **Monospace für Pfade** – `font_family="monospace"` (oder `ft.Text` mit Code-Stil) für `profile_label` und `latest_report_hint`
4. **Run-Ordner-Pfad-Hinweis** – nach dem Lauf den letzten Run-Ordner als selektierbaren Text anzeigen
5. **Window-Titel aktualisieren** – nach Lauf `page.title` auf Status aktualisieren
6. **Tooltip für Profil-Info-Box** – erklärt kurz, was Preset vs. Profil bedeutet
7. **Status-Badge visuell verbessern** – farbige Kapsel statt plain Text für Statusanzeige

**Erst danach:** Warten auf `document_profiles` end-to-end Validierung,
dann read-only Profilansicht implementieren.

---

*Dieses Dokument ist ein Zieldokument ohne Implementierungsauftrag.*  
*Es darf als Grundlage für spätere UI-Entwicklungstasks verwendet werden.*  
*Letzter Stand: Mai 2026.*
