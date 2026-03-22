## KI-Rechnungen-App

Diese Version verarbeitet PDFs aus einem konfigurierten Eingangsordner, nutzt OpenAI Vision als primaere Extraktion, faellt bei technischem oder strukturellem Fehlschlag auf Tesseract zurueck, trennt strikt zwischen `invoice` und `document`, archiviert Originale nur im Eingangsordner und steuert Klassifikation, Business-Kontext, Payment-Erkennung, Final Assignment und Duplikatbehandlung vollstaendig ueber Presets.

## Start

1. Python 3.9+ verwenden.
2. Abhaengigkeiten installieren:

```bash
python3 -m pip install -e ".[dev]"
```

3. Tesseract lokal installieren und im `PATH` verfuegbar machen.
4. API-Key-Datei am Standardpfad hinterlegen:

```text
$HOME/Library/Application Support/KI-Rechnungen-Umbenennen/.env
```

Dateiinhalt:

```text
OPENAI_API_KEY=...
```

5. Konfiguration in `invoice_config.json` anpassen.
6. Tool starten:

```bash
python3 -m invoice_tool
```

## Konfigurationsdatei

Die Laufzeitkonfiguration liegt in `invoice_config.json` und wird bei jedem Start neu geladen. Pflichtfelder:

```json
{
  "eingangsordner": "./testing/input",
  "ausgangsordner": "./testing/output",
  "api_key_pfad": "$HOME/Library/Application Support/KI-Rechnungen-Umbenennen/.env",
  "archiv_aktiv": true,
  "regeln_datei": "./office_rules.json",
  "aktives_preset": "office_default",
  "openai_model": "gpt-4.1-mini",
  "stale_lock_seconds": 21600,
  "runtime_ordner": "./runtime",
  "log_ordner": "./logs",
  "zielgroesse_kb": 200
}
```

## Regeldatei

Die geschaeftsrelevanten Regeln liegen separat in `office_rules.json` und sind mehrpresetfaehig:

- `active_preset`
- `presets.<name>.dateiname_schema`
- `presets.<name>.invoice_fallbacks`
- `presets.<name>.classification`
- `presets.<name>.routing`
- `presets.<name>.archivierung`
- `presets.<name>.dokumente`
- `presets.<name>.duplicate_handling`
- `presets.<name>.supplier_cleaning`

Dadurch koennen spaeter UI oder Konfigurationseditor die Regeln aendern, ohne die Engine umzubauen.

## Archivierung

Nach erfolgreicher Verarbeitung passiert in dieser Reihenfolge:

1. Datei als `invoice` oder `document` klassifizieren
2. Genau eine Ziel-PDF schreiben
3. Original-PDF aus dem Eingangsordner nach `eingangsordner/archiv/jjmmtt_archiv`, `jjmmtt_archiv2`, ... verschieben

Wichtig:

- Rechnungen gehen nur nach `ausgangsordner/<zielordner>/`
- Unklare Rechnungen liegen nur in `ausgangsordner/unklar/`
- Dokumente gehen nur nach `documents_base_path`
- Im Output gibt es kein Archiv
- Das Ausgabe-PDF bleibt immer eine vollstaendige Kopie der Original-PDF

## Klassifikation

Die Reihenfolge ist regelgetrieben:

1. Dokument-Indikatoren haben Vorrang
2. Interne Belege koennen als Rechnungen erzwungen werden
3. Invoice-Indikatoren wie `Rechnung`, `Invoice` oder Rechnungsnummer klassifizieren als `invoice`

Wichtig:

- `supplier + date + amount` allein erzwingt keine Rechnung
- Rechnungen bleiben Rechnungen, auch wenn spaeter nur unklare Payment-Zuordnung moeglich ist

## Finales Feldmodell

Rechnungen werden intern auf diese Felder abgebildet:

- `art`: `ai`, `ep`, `private`
- `konto`: `vobaai`, `vobaep`, `null`
- `payment_field`: `vobaai`, `vobaep`, `bar`, `paypal-unklar`, `private`, `unklar`

Das Default-Dateinamenschema nutzt aktuell:

```text
jjmmtt_er_[art]_[supplier]_[amount]_[payment_field].pdf
```

## Entscheidungslogik

Die Engine trennt:

1. AI-Extraktion
2. Normalisierung
3. Business-Kontext
4. Payment-Erkennung
5. Final Assignment
6. Output-Routing

Beispiele aus dem Default-Preset:

- `SOMAA Event & Production -> art=ep`
- `SOMAA Architektur & Innenarchitektur -> art=ai`
- `SOMAA unspezifiziert -> art=ai`
- `kein SOMAA -> art=private`
- `PayPal -> payment_field=paypal-unklar`
- `bar -> payment_field=bar`
- `card/transfer + ai -> vobaai`
- `card/transfer + ep -> vobaep`

## Dokumente

Dokumente werden nicht im Output gespeichert, sondern nur unter `documents_base_path`.

Standard-Dateinamenschema:

```text
jjmmtt_d_<description>_vn.pdf
```

## Duplikate und Reprocessing

- Dateien im Top-Level-Input werden verarbeitet
- Archiv-Unterordner werden nicht gescannt
- Historischer State blockiert neue Inhalte nicht
- Gleicher Dateiname mit neuem Inhalt wird erneut verarbeitet
- Gleicher Inhalt unter anderem Namen erzeugt keinen zweiten PDF-Output, sondern einen Textreport in `output/_duplicate_reports/`

## Logging

Jeder Lauf schreibt nach:

```text
logs/run_YYYYMMDD_HHMMSS.log
```

Pro Datei werden mindestens geloggt:

- Dateiname
- Typ (`invoice` oder `document`)
- Lieferant
- Datum
- Betrag
- Konto
- Payment-Feld
- Strasse
- Routing-Entscheidung
- Speicherpfad
- Archivpfad
- Fallback-Nutzung
- Preset
- Status
- Fehler

## Verifikation

Syntax und lokale Regeln lassen sich pruefen mit:

```bash
python3 -m compileall invoice_tool tests
pytest
python3 -m invoice_tool
```
