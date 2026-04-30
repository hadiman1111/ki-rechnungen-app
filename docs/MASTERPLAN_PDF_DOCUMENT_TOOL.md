# Masterplan – Allgemeines PDF-Dokumentenwerkzeug

Stand: April 2026  
Status: lebendiges Dokument – wird mit jedem Architekturentscheid aktualisiert

---

## 1. Ausgangspunkt

Das Projekt startete als **KI-Rechnungen-App** mit dem Ziel, Rechnungs-PDFs automatisch zu
erkennen, zu kategorisieren, umzubenennen und zu archivieren.

### Bereits vorhandene Grundlagen

Der erste stabile Anwendungsfall – Rechnungsrouting – ist realisiert und produktiv nutzbar.
Folgende Kernkomponenten existieren:

| Komponente | Beschreibung |
|---|---|
| PDF-Verarbeitung | Rendern, OCR (Tesseract-Fallback), OpenAI-Vision |
| Extraktion | Datum, Lieferant, Betrag, Zahlungsweg, IBAN, Karte |
| Routing | Business-Kontext, Konten/IBAN/Karte, Straßenerkennung, Prioritätsregeln |
| Dateinamenslogik | Schema-basiert, konfigurierbares Trennzeichen und Feldfolge |
| decision_trace.jsonl | Vollständige Entscheidungsspur pro Datei |
| routing_summary.csv | Tabellarische Laufübersicht |
| report.txt + report.json | Lesbare Laufberichte |
| Run-Logger | Eindeutige run_id (YYYYMMDD_HHMMSS), Logs pro Lauf |
| InvoiceProcessor | Kernverarbeitung, Archivierung, State-Persistenz |
| Profile Compiler MVP | address_profiles → routing.strassen + prioritaetsregeln |
| Testsuite | >220 Unit-Tests, schema-validiert |

### Technische Bezeichnungen

- Paketname: `invoice_tool` – **darf vorerst bestehen bleiben**, soll aber langfristig nicht die
  Produktgrenze definieren.
- Repository: KI-Rechnungen-App – ebenfalls eine Übergangsbenennung.

Die interne Bezeichnung „invoice" beschreibt den **ersten Anwendungsfall**, nicht das
langfristige Produktziel.

---

## 2. Strategisches Ziel

Das System soll langfristig **beliebige PDF-Dokumente** verarbeiten können – nicht nur Rechnungen.

### Kernfähigkeiten (Zielbild)

Das System soll PDFs anhand nutzerdefinierter Profile:

1. **erkennen** – Dokumenttyp bestimmen (Rechnung, Bestellung, Vertrag, Bescheid…)
2. **klassifizieren** – Kategorie, Zugehörigkeit, Zahlungsweg, Kontext
3. **relevante Metadaten extrahieren** – Datum, Aussteller, Betrag, Referenznummer, Thema
4. **nach Regeln umbenennen** – strukturierter, stabiler Dateiname je Dokumenttyp
5. **in Zielstrukturen sortieren** – Zielordner nach Profil und Kategorie
6. **unklare Fälle markieren** – keine stillen Fehlentscheidungen
7. **Entscheidungen nachvollziehbar dokumentieren** – Trace, Bericht, Begründung

### Rechnungen: erster Dokumenttyp, nicht der einzige

Rechnungen sind der erste und heute einzige produktiv implementierte Dokumenttyp.
Die Architektur soll aber von Beginn an so gestaltet sein, dass weitere Typen ohne
Umbau des Kerns hinzukommen können.

---

## 3. Produktprinzip

Diese Grundsätze gelten für alle künftigen Architekturentscheidungen:

### Keine festen Nutzer- oder Instanzregeln im Produktkern
- Keine SOMAA-spezifischen Regeln im Kern-Code.
- Keine fest codierten Nutzerpfade (kein `/Desktop/Hadi/`, kein `testing/input`).
- Nutzerprofile erzeugen **Runtime-Regeln** für einen konkreten Lauf.
- Basisregeln (`office_rules.json`) bleiben stabil und werden nicht automatisch überschrieben.

### Originalschutz
- **Originaldateien des Nutzers werden niemals verändert.**
- Der Processing Core darf nur auf einem **input_snapshot** arbeiten.
- Pro Lauf wird ein frischer input_snapshot durch Kopie (nicht Move) erstellt.
- `testing/input` und `testing/output` sind Entwicklungshilfen, kein Produktmodell.

### Nachvollziehbarkeit vor Automatismus
- Jede automatische Entscheidung muss nachvollziehbar sein.
- Unklare Fälle werden nicht erraten, sondern zur Prüfung markiert.
- Jeder Lauf erzeugt Reports und Traces.
- Preview vor Speichern: Nutzer soll sehen, welche Regeln entstehen, bevor sie aktiv werden.

### Laufbezogene Isolation
- Jeder Lauf bekommt seinen eigenen Ordner.
- `runtime/`, `logs/`, `output/` sind pro Lauf isoliert.
- Mehrere Läufe stören sich nicht gegenseitig.

---

## 4. Zielarchitektur

```
┌─────────────────────────────────────────────────────────────┐
│                    UI / CLI (später)                         │
│          Nutzer wählt source, output, Profil                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Run Manager                              │
│   invoice_tool/run.py  ✓ implementiert                       │
│   - nimmt source + output + profile entgegen                 │
│   - erzeugt Run-Ordner                                       │
│   - erstellt input_snapshot                                  │
│   - lädt Profile Compiler                                    │
│   - baut AppConfig pro Lauf                                  │
│   - ruft Processing Core auf                                 │
└────────────┬──────────────────────────────┬─────────────────┘
             │                              │
             ▼                              ▼
┌────────────────────────┐    ┌─────────────────────────────┐
│   Profile Compiler     │    │      Processing Core        │
│   invoice_tool/        │    │   invoice_tool/processing.py │
│   profile_compiler.py  │    │   - Extraktion              │
│   - address_profiles   │    │   - Klassifikation          │
│   - account_profiles   │    │   - Routing                 │
│   - business_context   │    │   - Dateiname               │
│   - vendor_profiles    │    │   - Archivierung (snapshot) │
│   - classification     │    │   - Reports + Traces        │
│   → runtime_rules      │    └─────────────────────────────┘
└────────────────────────┘
```

### 4.1 Processing Core

- Verarbeitet PDFs anhand von `AppConfig` und `OfficeRules`.
- Führt Extraktion, Klassifikation, Routing, Dateinamensbildung, Archivierung und
  Report-Erstellung aus.
- Bleibt möglichst unabhängig von UI-Details und konkreten Nutzerprofilen.
- Darf Originaldateien **nicht direkt verändern**.
- Archivierung (`_archive_original()`) ist nur innerhalb eines `input_snapshot` erlaubt.
- Kernklasse: `InvoiceProcessor` – vorerst unverändert, langfristig umbenennen.

### 4.2 Run Manager

- Nimmt frei wählbare `--source` und `--output` Argumente entgegen.
- Erzeugt pro Lauf einen eigenen Run-Ordner (`YYYYMMDD_HHMMSS`).
- Erstellt `input_snapshot/` durch **Kopie** (niemals Move) aus `source`.
- Übergibt `input_snapshot/` als `eingangsordner` an den Processing Core.
- Übergibt `run_dir/output/` als `ausgangsordner`.
- Isoliert `runtime/` und `logs/` pro Lauf.
- Sammelt Reports und Traces im Run-Ordner.
- Schützt Originaldateien strikt.
- Wird später sowohl von **CLI als auch UI** genutzt.

**Beispiel-CLI:**
```
python -m invoice_tool.run \
  --source "/Pfad/zum/Quellordner" \
  --output "/Pfad/zum/Zielordner" \
  --profile "/Pfad/zur/profile_config.json"
```

**Geplante Run-Struktur:**
```
<output>/
  <YYYYMMDD_HHMMSS>/
    input_snapshot/         ← Kopien der Original-PDFs
    output/
      _runs/{run_id}/
        report.txt
        report.json
        decision_trace.jsonl
        routing_summary.csv
      _history/
      _duplicate_reports/
      ai/ ep/ amex/ unklar/ ...
    runtime/
      state/
        processed_state.json
    logs/
      run_{run_id}.log
    runtime_rules.json      ← für diesen Lauf erzeugte Regeln (dokumentiert)
    profile_snapshot.json   ← verwendetes Profil (dokumentiert)
```

### 4.3 Profile Compiler

- Übersetzt Nutzerprofile (`profile_config.json`) in technische Runtime-Regeln.
- Überschreibt `office_rules.json` **nicht dauerhaft**.
- Erzeugt Regeln pro Lauf – In-Memory oder als `runtime_rules.json`.
- Ermöglicht Preview und Export.

**Aktueller MVP (implementiert):**
- `address_profiles` → `routing.strassen` + `routing.prioritaetsregeln`

**Geplante Erweiterungen:**
- `account_card_profiles` → `routing.konten`
- `business_context_profiles` → `routing.business_context_rules`
- `classification_profile` → `classification.*`
- `vendor_profiles` → vendor-spezifische `payment_detection_rules`

### 4.4 Runtime Rules

- Entstehen aus `base_rules` (office_rules.json) + `user_profile` (profile_config.json).
- Gelten **nur für den jeweiligen Lauf**.
- Werden im Run-Ordner als `runtime_rules.json` dokumentiert.
- Ermöglichen nachvollziehbares Debugging: „Welche Regeln galten bei diesem Lauf?"
- Dienen als Brücke zwischen UI-Einstellungen und technischer Verarbeitung.
- Werden **niemals** automatisch zurück in `office_rules.json` geschrieben.

### 4.5 UI / Nutzeroberfläche

- Späterer Einstieg für Nutzer.
- Nutzer wählt Dateien oder Ordner (Dateiauswahl oder Drag & Drop).
- Nutzer wählt oder erstellt ein Profil.
- Nutzer startet einen Lauf.
- Nutzer sieht Ergebnisse, unklare Fälle und Reports.
- UI darf Basisregeln nicht unkontrolliert überschreiben.
- UI nutzt den Run Manager intern – kein gesonderter Code-Pfad.

---

## 5. Dokumenttypen – statt nur Rechnungen

Künftig sollen `document_profiles` definieren, wie ein Dokumenttyp erkannt und benannt wird.

### Rechnung *(heute implementiert)*

| Feld | Beschreibung |
|---|---|
| Datum | Rechnungsdatum |
| Lieferant | Rechnungssteller |
| Betrag | Gesamtbetrag / Amount due |
| Zahlungsweg | IBAN, Karte, PayPal, Amex… |
| Kategorie | ai, ep, private |
| Konto | vobaai, vobaep, amex… |

Dateinamensschema: `{date}_er_{category}_{supplier}_{amount}_{payment}.pdf`

---

### Bestellbestätigung *(Klassifikation implementiert, Benennungsschema in Arbeit)*

| Feld | Beschreibung |
|---|---|
| Datum | Bestelldatum |
| Anbieter | Shop / Lieferant |
| Bestellnummer | Referenz |
| Produkt/Thema | Was wurde bestellt |

Dateinamensschema: `{date}_d_bestellbestaetigung_{vendor}_{order_number}.pdf`

---

### Vertrag *(Zielbild)*

| Feld | Beschreibung |
|---|---|
| Datum | Abschluss- oder Gültigkeitsdatum |
| Vertragspartner | Gegenüber |
| Thema | Vertragsgegenstand |
| Projekt/Kategorie | Zuordnung |

Dateinamensschema: `{date}_vertrag_{party}_{topic}.pdf`

---

### Bescheid *(Zielbild)*

| Feld | Beschreibung |
|---|---|
| Datum | Bescheiddatum |
| Behörde | Aussteller |
| Thema | Art des Bescheids |
| Jahr | Bezugsjahr |

Dateinamensschema: `{date}_bescheid_{authority}_{topic}_{year}.pdf`

---

### Weitere geplante Typen *(Zielbild)*

- Gutschrift
- Quittung / Kassenbeleg
- Versicherungsunterlagen
- Steuerunterlagen
- Projektunterlagen
- Lieferschein
- Kontoauszug
- Interne Übersicht
- Sonstige PDF-Dokumente

> Diese document_profiles sind **Zielbild**, nicht sofortiger Implementierungsumfang.
> Sie zeigen die geplante Richtung, nicht den aktuellen Entwicklungsstand.

---

## 6. Frei wählbare Input-/Output-Orte

### Grundsätze

- Nutzer sind nicht an feste Pfade gebunden.
- `source` und `output` müssen **frei wählbar** sein.
- UI soll Dateiauswahl oder Drag & Drop ermöglichen.
- CLI soll freie Pfade über `--source` und `--output` unterstützen.
- `testing/input` und `testing/output` sind **Entwicklungshilfen**, kein Produktmodell.
- `source` darf niemals direkt durch den Processor verändert werden.
- `output` darf nicht identisch mit `source` sein.
- `source` darf nicht innerhalb des `output`-Run-Ordners liegen.
- Jeder Run-Ordner muss eindeutig sein (Timestamp + ggf. Suffix-Counter).

### Beispiel Laufstruktur

```
/Users/alice/runs/
  2026-04-28_174500/
    input_snapshot/
      rechnung1.pdf
      rechnung2.pdf
      archiv/
        260428_archiv/
          rechnung1.pdf   ← nach Verarbeitung hierher verschoben
    output/
      ai/
      amex/
      unklar/
      _runs/
        20260428_174500/
          report.txt
          report.json
          decision_trace.jsonl
          routing_summary.csv
    runtime/
      state/
        processed_state.json
    logs/
      run_20260428_174500.log
    runtime_rules.json
    profile_snapshot.json
```

---

## 7. Regeln und Profile

### Geplante Profilbereiche

| Bereich | Beschreibung | Status |
|---|---|---|
| `categories` | Bekannte Kategorien (ai, ep, private…) | Schema ✓ |
| `folders` | Zielordner-Definitionen | Schema ✓ |
| `address_profiles` | Adresse → Kategorie, Matching-Modus | Schema ✓, Compiler MVP ✓ |
| `account_card_profiles` | IBAN/Karte/Apple Pay → Konto | Schema ✓, Compiler MVP ✓ |
| `business_context_profiles` | Keywords → Geschäftskontext | Schema ✓, Compiler MVP ✓ |
| `vendor_profiles` | Lieferant → Zahlungsfeld | Schema ✓, Compiler MVP ✓ |
| `classification_profile` | Invoice/Document Keywords | Schema ✓, Compiler MVP ✓ |
| `naming_profile` | Dateinamensstruktur | Schema ✓, Compiler MVP ✓ |
| `review_policy` | Unklar-Verhalten | Schema ✓, Compiler MVP ✓ |
| `payment_profiles` | Zahlungsarterkennung | Schema ✓, Compiler MVP ✓ |
| `document_profiles` | Dokumenttypen (Rechnung, Vertrag…) | Zielbild, nicht implementiert |

### Trennung von Profil und Basisregeln

```
Nutzer-Profil (profile_config.json)
        │
        ▼
Profile Compiler
        │
        ▼
Runtime Rules (für diesen Lauf)
        │
 ───────┴──────────────────────────────
 │  Basis-Regeln (office_rules.json)  │
 │  – stable, manually maintained    │
 │  – NOT overwritten by profiles    │
 └────────────────────────────────────┘
        │
        ▼
InvoiceProcessor / Processing Core
```

- `office_rules.json` ist **nicht die UI-Speicherdatei** für Nutzerprofile.
- UI-Einstellungen dürfen nicht dauerhaft und stillschweigend `office_rules.json`
  überschreiben.
- Nutzerprofile beschreiben **Nutzerwünsche**.
- Der Compiler erzeugt daraus technische Runtime-Regeln.
- Basisregeln bleiben separat.

---

## 8. Preview- und Export-Prinzip

Bevor Regeln aktiv werden, soll der Nutzer sehen können:

- welche Regeln aus seinem Profil entstehen
- welche Adressen erkannt werden
- welche Konten/Karten erkannt werden
- welche Dokumenttypen entstehen würden
- welche Konflikte existieren (z.B. gleicher IBAN-Ending für zwei Konten)
- welche Regeln manuell bleiben müssen

### Preview

> Anzeigen ohne Speichern.

Der Nutzer sieht die erzeugten Routing-Regeln als lesbares Ergebnis –
kein automatisches Schreiben in Konfigurationsdateien.

### Export

> Generierte Regeln als separate Datei ausgeben.

Die generierten Regeln können als `runtime_rules.json` oder als Vorschlag
für `office_rules.json` exportiert werden –
aber **keine automatische Überschreibung** von `office_rules.json`.

### Merge / Übernahme

Erst in einem späteren Schritt:
- nur kontrolliert
- nur auf explizite Nutzeraktion
- nie stillschweigend

---

## 9. Nachvollziehbarkeit / Trace

Jeder Lauf soll dokumentieren:

| Was | Wo |
|---|---|
| Verwendetes Profil | `profile_snapshot.json` |
| Erzeugte Runtime-Regeln | `runtime_rules.json` |
| Extrahierte Dokumentfelder | `decision_trace.jsonl` |
| Gegriffene Routing-Regeln | `decision_trace.jsonl` |
| Zielordner und Dateiname | `decision_trace.jsonl`, `routing_summary.csv` |
| Unsicherheiten | `decision_trace.jsonl` (conflicts, warnings) |
| Gründe für unklar | `report.txt` + `decision_trace.jsonl` |
| Laufprotokoll | `logs/run_{run_id}.log` |

### Bereits vorhandene Grundlagen

- `decision_trace.jsonl` ✓
- `routing_summary.csv` ✓
- `report.txt` ✓
- `report.json` ✓
- `RunLogger` ✓

### Langfristiges Ziel

Diese Traces sollen nicht nur technisch verwertbar, sondern **nutzerverständlich** werden.
Ein Nutzer soll ohne technisches Wissen verstehen können, warum eine Datei so benannt
und einsortiert wurde.

---

## 10. Sicherheits- und Schutzprinzipien

| Prinzip | Erläuterung |
|---|---|
| Originalschutz | Originaldateien des Nutzers niemals verändern |
| Snapshot-Pflicht | Processing Core nur auf input_snapshot ausführen |
| Run-Isolation | Keine Dateien außerhalb definierter Run-/Output-Ordner löschen |
| Keine stille Überschreibung | Regeländerungen immer explizit und nachvollziehbar |
| Keine stille Umdeutung | Unklare Fälle nicht raten – markieren |
| Profilvalidierung | Profile müssen gegen Schema validiert werden |
| Konfliktprüfung | Doppelte/widersprüchliche Regeln müssen erkannt werden |
| Datenschutz | Sensible Daten nicht unnötig in Logs oder Beispieldateien |
| Testdaten-Trennung | Testdaten und echte Nutzerdaten müssen getrennt bleiben |
| source ≠ output | `source == output` muss geprüft und verhindert werden |
| Verschachtelung prüfen | `source` innerhalb `output` (oder umgekehrt) muss erkannt werden |
| Mehrlauf-Isolation | Mehrere Läufe bekommen eigene `runtime/` und `logs/` |
| Kollisionsbehandlung | Dateinamenkollisionen im Run-Ordner müssen behandelt werden |
| Archiv nur im Snapshot | `_archive_original()` darf nur innerhalb `input_snapshot/` arbeiten |

---

## 11. Run Manager – technisches MVP-Ziel

### Datei

`invoice_tool/run.py`

### CLI-Signatur

```
python -m invoice_tool.run \
  --source  <Pfad zum PDF-Quellordner>   \
  --output  <Pfad zum Run-Basisordner>   \
  [--config  <Pfad zur invoice_config.json>]  \
  [--rules   <Pfad zur office_rules.json>]    \
  [--profile <Pfad zur profile_config.json>]
```

### Geplante Funktionen

```python
def create_run_snapshot(source: Path, run_dir: Path) -> Path:
    """Kopiert alle PDFs aus source in run_dir/input_snapshot/.
    Originaldateien werden nie verändert."""

def build_run_config(base_config: AppConfig, run_dir: Path) -> AppConfig:
    """Erzeugt einen neuen AppConfig mit isolierten Pfaden für diesen Run."""

def run_once(
    source: Path,
    output: Path,
    *,
    config_path: Path,
    rules_path: Path | None = None,
    profile_path: Path | None = None,
) -> Path:
    """Führt einen vollständigen Lauf durch. Gibt den Run-Ordner zurück."""

def main() -> int:
    """CLI-Entrypoint für python -m invoice_tool.run"""
```

### Implementierungsidee (ohne Änderung von InvoiceProcessor)

```python
import dataclasses

# Originale AppConfig laden (API-Key, Regeln, Modell…)
base_config = load_app_config(config_path)

# Run-Ordner erstellen
run_dir = output / datetime.now().strftime("%Y%m%d_%H%M%S")
run_dir.mkdir(parents=True, exist_ok=True)

# Snapshot erstellen (Kopie, kein Move)
snapshot = create_run_snapshot(source, run_dir)

# AppConfig für diesen Lauf – Pfade überschreiben, Rest beibehalten
run_config = dataclasses.replace(
    base_config,
    eingangsordner=snapshot,
    ausgangsordner=run_dir / "output",
    runtime_ordner=run_dir / "runtime",
    log_ordner=run_dir / "logs",
)

# Processing Core unverändert nutzen
processor = InvoiceProcessor(run_config, extractor, office_rules=office_rules)
processor.process_all()
```

### Schlüsseleigenschaft

`InvoiceProcessor` bleibt **unverändert**. Der Run Manager ist eine neue Schicht darüber.

---

## 12. Entwicklungsreihenfolge

Empfohlene Reihenfolge (nicht verbindlicher Sprint-Plan, sondern Richtungspriorisierung):

| Schritt | Thema | Abhängig von |
|---|---|---|
| 1 | **Run Manager MVP** – frei wählbare source/output, Snapshot-Schutz, isolation | – |
| 2 | **Runtime-Rules-Konzept** – base_rules + profile → run_rules pro Lauf | Run Manager |
| 3 | **Preview/Export** – generierte Regeln anzeigen und exportieren | Profile Compiler |
| 4 | **Profile Compiler erweitern** – account_profiles, business_context, classification | Runtime-Rules |
| 5 | **Profilvalidierung** – Schema-Prüfung, Konfliktprüfung | Profile Compiler |
| 6 | **Nutzerverständlicher Report** – Trace und Report für Nicht-Techniker | Trace |
| 7 | **UI MVP** – einfache Review-Oberfläche, Ergebnisanzeige | Run Manager, Report |
| 8 | **document_profiles** – weitere Dokumenttypen | Klassifikation |
| 9 | **Packaging / Installation** – Produktisierung | alle oben |

---

## 13. Aktueller Nicht-Umfang

Folgendes ist heute **noch nicht** gebaut und explizit außerhalb des aktuellen Entwicklungsstandes:

- ❌ Allgemeines `document_profiles`-System für beliebige Dokumenttypen
- ❌ Vollständige UI (nur Planung)
- ✅ Run Manager (`invoice_tool/run.py` – implementiert, produktiv nutzbar)
- ✅ Runtime-Rules-Integration (Profil → Runtime Rules pro Lauf, vollständig verknüpft)
- ✅ Konto-/Zahlungsregel-Generierung via Profile Compiler (account_card_profiles, vendor_profiles)
- ❌ Automatisches Merge in `office_rules.json` (Runtime Rules bleiben laufbezogen, kein Permanent-Merge)
- ❌ Nutzerverwaltung oder Mehrbenutzerfähigkeit
- ✅ Preview-Skript für generierte Regeln (`scripts/preview_profile_runtime_rules.py`)
- ✅ Run-Verifikationsskript (`scripts/check_profile_run.py` – PASS/FAIL + Entscheidungssignal)
- ✅ Dev-Assistant (`scripts/dev_assistant.py` – bündelt status/test/smoke/check in `--mode next` mit Smart-Skip)
- ✅ Autonomer Cursor-Agent-Workflow (`docs/roadmap/PDF_TOOL_CURSOR_AGENT_WORKFLOW.md` – bis zu 3 Schritte ohne Unterbrechung)
- ❌ Nutzerverständlicher Schlussbericht für Nicht-Techniker (jetzt technisch-strukturiert)
- ❌ Installation / Packaging / Produktdistribution
- ✅ Profilvalidierung (`validate_profile()` in profile_compiler.py, Laufzeit-Checks)

---

## 14. Verbindliche Leitentscheidung

Das Projekt wird ab jetzt so weiterentwickelt, dass der **erste Anwendungsfall Rechnungen**
bleibt, die Architektur aber auf **allgemeine, profilbasierte PDF-Dokumentverarbeitung**
ausgerichtet ist.

### Prüffrage für neue Architekturentscheidungen

Vor jeder neuen Implementierung:

> 1. Ist diese Lösung **nur für Rechnungen**?
> 2. Ist sie **nur für einen bestimmten Nutzer** (z.B. SOMAA/Hadi)?
> 3. Oder ist sie als **allgemeine, profilbasierte PDF-Dokumentenlogik** nutzbar?

Wenn eine Lösung nur invoice-only oder nur nutzer-spezifisch ist,
muss sie **bewusst als Übergangslösung** gekennzeichnet werden.

### Grundsatz

> **Nutzer bringen ihre Profile. Das System bringt die Architektur.**
>
> Keine Logik im Produktkern soll von einer bestimmten Adresse, einem bestimmten Konto
> oder einem bestimmten Nutzer abhängen. Diese Dinge gehören in Konfigurationsdateien,
> nicht in Code.

---

## 15. MVP-Freeze / Stabilization Mode

**Status: AKTIV seit 2026-04-30**

Das Projekt hat den MVP-Stand erreicht. Alle geplanten Profile-Compiler sind implementiert.
Die Entwicklung tritt in den Stabilisierungsmodus.

### Abgeschlossener MVP-Umfang

- ✅ 8 Profile-Compiler: address, account_card, business_context, vendor, classification,
  naming, review_policy, payment_profiles
- ✅ Runtime-Rules-Integration (profile_config → runtime_rules.json pro Lauf)
- ✅ Run Manager (`invoice_tool/run.py`)
- ✅ Smoke-Test + Run-Verifikation (`scripts/check_profile_run.py`)
- ✅ Dev-Assistant (`scripts/dev_assistant.py`, Smart-Skip, `--mode next`)
- ✅ Autonomer Cursor-Agent-Workflow (`docs/roadmap/PDF_TOOL_CURSOR_AGENT_WORKFLOW.md`)
- ✅ 414 Unit-Tests

### Was im Stabilisierungsmodus erlaubt ist (ohne gesonderte Freigabe)

- Bugfixes bei reproduzierbaren Fehlern
- Test- und Smoke-Test-Verifikation
- Bedienanleitungen, Doku-Korrekturen
- Echter kontrollierter Arbeitslauf nach ausdrücklicher Freigabe
- Ergebnisprüfung

### Was ausdrückliche Freigabe erfordert

- Neue Compiler, Profile oder Runtime-Logik
- Neue Architekturbausteine
- UI-Entwicklung
- Produktivlauf-Logik außerhalb freigegebener Pfade
- Neue Dependencies
- Architekturänderungen

---

*Dieses Dokument ist ein lebendiger Plan und wird mit Architekturentscheidungen aktualisiert.*  
*Letzter redaktioneller Stand: April 2026.*
