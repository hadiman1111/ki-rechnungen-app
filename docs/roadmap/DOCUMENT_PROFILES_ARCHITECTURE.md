# Architektur: document_profiles

Stand: Mai 2026  
Status: Schema definiert + Runtime-Compiler-Erweiterung implementiert (Schritt 8b/8c abgeschlossen)

---

## 1. Zweck dieses Dokuments

Dieses Dokument klärt die Architekturbeziehung zwischen den bestehenden Konfigurationsebenen
und dem neu definierten `document_profiles`-Schema.

Es beantwortet folgende Fragen verbindlich:

- Sind `document_profiles` Teil von `profile_config`, Teil von `office_rules` oder eine
  separate Konfigurationsebene?
- Wie verhalten sich `document_profiles` gegenüber bestehenden Presets?
- Welche Schicht ist dauerhaft und systemseitig?
- Welche Schicht ist nutzerseitig?
- Welche Schicht wird pro Lauf erzeugt?
- Was darf die UI niemals überschreiben?

---

## 2. Konfigurationsebenen – Überblick

```
┌─────────────────────────────────────────────────────────────────┐
│  office_rules.json                                               │
│  ─────────────────                                               │
│  SYSTEM-SCHICHT – dauerhaft, manuell gepflegt                   │
│  - Preset-Struktur (active_preset + presets-Objekt)             │
│  - Basis-Routing-Regeln (strassen, konten, payment_detection…)  │
│  - Classification-Keywords (Basis)                              │
│  - Dateinamen-Schema (Basis)                                     │
│  - Archivierungs- und Duplikat-Einstellungen                    │
│  Darf NICHT von UI oder Profilen überschrieben werden.          │
└────────────────────────┬────────────────────────────────────────┘
                         │ (base rules + profile → merge)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  profile_config.local.json  (oder profile_config.json)         │
│  ────────────────────────────────────────────────────────────── │
│  NUTZER-SCHICHT – lokal, nutzerseitig, git-ignoriert (local)   │
│  - categories, folders                                          │
│  - account_card_profiles, address_profiles                      │
│  - vendor_profiles, payment_profiles                            │
│  - business_context_profiles, classification_profile            │
│  - naming_profile, review_policy                                │
│  - document_profiles  ← NEU (Schema definiert, MVP)            │
│  Wird vom Profile Compiler in Runtime Rules übersetzt.         │
│  Darf office_rules.json NICHT dauerhaft überschreiben.         │
└────────────────────────┬────────────────────────────────────────┘
                         │ (Profile Compiler)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  runtime_rules.json  (pro Lauf generiert)                       │
│  ─────────────────────────────────────────────────────────────  │
│  LAUF-SCHICHT – laufbezogen, niemals dauerhaft                  │
│  - Aus office_rules.json (Basis) + profile_config (Nutzer)      │
│  - Enthält nur technische Regelstrukturen für die Verarbeitung  │
│  - Wird im Run-Ordner dokumentiert (nachvollziehbar)            │
│  - Wird NIEMALS zurück in office_rules.json geschrieben        │
│  - Darf NICHT als permanente Nutzerkonfiguration behandelt sein │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Verbindliche Antworten auf die Architekturfragen

### 3.1 Sind document_profiles Teil von profile_config, office_rules oder eine separate Schicht?

**`document_profiles` sind Teil von `profile_config`.**

Sie sind ein optionales Array-Feld in `profile_config.json` (oder `profile_config.local.json`).
Sie befinden sich in der nutzerseitigen Schicht, nicht in der systemseitigen Schicht.

**Begründung:**
- `office_rules.json` enthält systemseitige, stabile Basisregeln (Presets, Routing-Grundstruktur).
  Dokumenttypen sind nutzerdefiniert – unterschiedliche Nutzer verarbeiten unterschiedliche
  Dokumenttypen.
- Eine separate dritte Konfigurationsdatei (z.B. `document_profiles.json`) würde die
  Konfigurationslandschaft ohne klaren Mehrwert fragmentieren.
- Die bestehenden Profil-Compiler übersetzen bereits alle anderen `profile_config`-Bereiche
  in technische Runtime-Regeln. `document_profiles` folgt demselben Muster.

### 3.2 Wie verhalten sich document_profiles gegenüber bestehenden Presets?

`document_profiles` sind **keine Presets** im Sinne der `office_rules.json`-Preset-Struktur.

| Konzept | Ebene | Zweck |
|---------|-------|-------|
| `office_rules.json` Presets | System | Technische Regelsets (z.B. `office_default`) |
| `profile_config` Profiles | Nutzer | Nutzerspezifische Einstellungen (Konten, Adressen…) |
| `document_profiles` | Nutzer | Dokumenttyp-Definitionen (was ist ein Vertrag? was ist eine Rechnung?) |

`document_profiles` beschreiben **was ein Dokumenttyp ist und wie er verarbeitet werden soll**.
Presets beschreiben **wie das System technisch konfiguriert ist**.

### 3.3 Welche Schicht ist permanent und systemseitig?

`office_rules.json` – manuell gepflegt, wird nicht automatisch überschrieben.

### 3.4 Welche Schicht ist nutzerseitig?

`profile_config.local.json` (für produktive lokale Nutzung, git-ignoriert) und
`profile_config.json` (für versionierte Beispiele oder Teamprofile).

`document_profiles` gehören zur nutzerseitigen Schicht.

### 3.5 Welche Schicht wird pro Lauf erzeugt?

`runtime_rules.json` – wird vom Profile Compiler aus Basis-Regeln und Nutzerprofil erzeugt.
Gilt nur für den jeweiligen Lauf.

### 3.6 Was darf die UI niemals überschreiben?

- `office_rules.json` (darf nie dauerhaft durch UI oder Profile überschrieben werden)
- `runtime_rules.json` darf nie als dauerhafte Nutzerkonfiguration behandelt werden

---

## 4. document_profiles – Schema-Überblick (MVP)

### Speicherort

`profile_config.schema.json` → Eigenschaft `document_profiles` → Array von `DocumentProfile`

### Typ-Definitionen (in `$defs`)

| Definition | Beschreibung |
|------------|-------------|
| `DocumentProfile` | Haupttyp eines Dokumenttyp-Profils |
| `DocumentNamingSchema` | Dateinamensschema für einen spezifischen Dokumenttyp |
| `DocumentTypeEnum` | Bekannte technische Dokumenttypen (enum) |
| `DuplicatePolicyEnum` | Duplikat-Verhaltensoptionen (enum) |

### Pflichtfelder eines DocumentProfile

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | string | Technischer Schlüssel (Muster: `^[a-z0-9_-]+$`) |
| `label` | string | Nutzerfreundlicher Name |
| `document_type` | DocumentTypeEnum | Technischer Dokumenttyp |

### Optionale Felder (MVP)

| Feld | Typ | Beschreibung | MVP-Status |
|------|-----|-------------|------------|
| `description` | string | Beschreibung für UI/Doku | ✓ Schema |
| `schema_version` | string | Für spätere Migration | ✓ Schema |
| `enabled` | boolean | Aktiv/inaktiv | ✓ Schema |
| `classification_hints` | string[] | Positive Erkennungs-Keywords | ✓ Schema, ✓ Compiler (8b) |
| `negative_hints` | string[] | Ausschluss-Keywords | ✓ Schema, ✓ Compiler (8b) |
| `required_fields` | string[] | Pflicht-Extraktionsfelder | ✓ Schema |
| `optional_fields` | string[] | Optionale Extraktionsfelder | ✓ Schema |
| `naming_schema` | DocumentNamingSchema | Dateinamens-Template | ✓ Schema, ✓ Compiler (8b) |
| `target_folder_id` | string | Zielordner-ID aus folders[] | ✓ Schema, ✓ Compiler (8b) |
| `fallback_folder_id` | string | Fallback-Ordner-ID | ✓ Schema, ✓ Compiler (8b) |
| `confidence_threshold` | number | Minimaler Confidence-Wert | ✓ Schema, ✓ Compiler (8b) |
| `duplicate_policy` | DuplicatePolicyEnum | Duplikat-Verhalten | ✓ Schema, ✓ Compiler (8b) |
| `ui_help_text` | string | UI-Hilfetext (kein technischer Effekt) | ✓ Schema |

### Bekannte DocumentTypeEnum-Werte

```
invoice              – Eingangsrechnung (heute vollständig implementiert)
credit_note          – Gutschrift
contract             – Vertrag
delivery_note        – Lieferschein
tax_notice           – Steuerbescheid / Bescheid
order_confirmation   – Bestellbestätigung
internal_document    – Interner Beleg / Eigenbeleg
generic_document     – Sonstiges PDF-Dokument
```

---

## 5. Implementierungsstatus

### Was heute definiert ist (nach diesem Schritt)

- ✅ `document_profiles`-Array-Feld in `profile_config.schema.json` registriert
- ✅ `DocumentProfile`-Typ vollständig in `$defs` definiert
- ✅ `DocumentNamingSchema`-Typ definiert
- ✅ `DocumentTypeEnum` und `DuplicatePolicyEnum` definiert
- ✅ Architekturbeziehung dokumentiert (dieses Dokument)
- ✅ Masterplan aktualisiert

### Was implementiert ist (nach Schritt 8b/8c)

- ✅ Profile Compiler: `_compile_document_profiles()` in `invoice_tool/profile_compiler.py`
- ✅ Matching: `_match_document_profile()` in `invoice_tool/processing.py`
- ✅ Dateinamens-Renderer: `render_document_filename()` in `invoice_tool/filename_schema.py`
- ✅ Confidence-Threshold: Klassifikations-Score gegen `confidence_threshold` geprüft
- ✅ Zielordner-Routing anhand von `target_folder_id` (resolved via folders[])
- ✅ Fallback-Ordner bei fehlenden Pflicht-Platzhaltern
- ✅ Negative-Hints blockieren Profile korrekt
- ✅ Trace-Felder: `matched_document_profile_id`, `matched_document_profile_score`, `document_profile_used_fallback`, `document_profile_missing_placeholders`
- ✅ runtime_rules.json enthält `document_profiles[]` (top-level, außerhalb von presets)
- ✅ End-to-End-Validierung (Schritt 8c) bestanden

### Phase 2b: UI-Profil-Editor für document_profiles

- ✅ UI-Profil-Editor für `document_profiles`: Phase 2b implementiert (nur Bearbeiten bestehender Einträge)
- Bearbeitbare Felder: `label`, `enabled`, `document_type`, `target_folder_id`, `fallback_folder_id`,
  `confidence_threshold`, `classification_hints`, `negative_hints`
- Für `document_type == "invoice"` wird kein „Bearbeiten"-Button angezeigt (UI-Schutz)

**Noch nicht implementiert (explizit außerhalb des Umfangs):**
- ❌ Hinzufügen / Löschen von `document_profiles`
- ❌ `naming_schema`-Bearbeitung
- ❌ `duplicate_policy`-Bearbeitung
- ❌ Import / Export von Profilen

### Sonstige offene Punkte

- ❌ `required_fields` / `optional_fields`: Schema definiert, kein Runtime-Effekt
- ❌ Duplikat-Policy pro Dokumenttyp (Feld vorhanden, aber Runtime-Logik noch nicht aktiv)

---

## 6. Implementierungsreferenz (nach Schritt 8b/8c)

Die folgenden Module sind die zentralen Implementierungspunkte:

1. **`invoice_tool/profile_compiler.py`** – `_compile_document_profiles()`:
   Übersetzt `document_profiles[]` aus `profile_config` in compilierte Runtime-Dicts.
   Validiert `target_folder_id`, `fallback_folder_id`, blockiert `document_type=invoice`.

2. **`invoice_tool/processing.py`** – `_match_document_profile()` + `_process_document_with_profile()`:
   Matching mit `classification_hints`/`negative_hints`, Confidence-Threshold-Prüfung,
   Fallback-Folder-Logik bei fehlenden Platzhaltern.

3. **`invoice_tool/filename_schema.py`** – `render_document_filename()`:
   Template-Auswertung, Fallback-Werte, Sanitisierung, Reporting von fehlenden Platzhaltern.

4. **`invoice_tool/run.py`** – `run_once()`:
   Propagiert `document_profiles` aus dem compilierten Profil in `runtime_rules.json`
   und übergibt sie an `InvoiceProcessor`.

**Rechnungen bleiben unberührt:** Die bestehende `_process_invoice()`-Pipeline läuft
unabhängig davon, ob `document_profiles` geladen sind oder nicht.
Wenn `document_profiles` fehlt oder leer ist, verhält sich das System wie bisher.

---

## 7. Sicherheits- und Schutzprinzipien

Für `document_profiles` gelten dieselben Prinzipien wie für alle anderen Profil-Bereiche:

- Profile werden gegen Schema validiert, bevor sie aktiv werden.
- `office_rules.json` wird nicht überschrieben.
- Runtime-Regeln gelten nur für den jeweiligen Lauf.
- Unklare Fälle werden markiert, nicht erraten.
- Originaldateien werden niemals verändert.

---

## 8. Illustrative Beispielprofile (nicht operativ)

> **Hinweis:** Die folgenden Beispiele illustrieren das Schema.
> Sie sind nicht in einer produktiven Konfigurationsdatei gespeichert.
> Das Schema und der Runtime-Compiler sind seit Schritt 8b implementiert.

### 8.1 Eingangsrechnung (invoice) – heute stabiler Anwendungsfall

```json
{
  "id": "rechnung",
  "label": "Eingangsrechnung",
  "description": "Rechnung eines Lieferanten. Heute vollständig implementierter Dokumenttyp.",
  "schema_version": "1.0",
  "enabled": true,
  "document_type": "invoice",
  "classification_hints": ["rechnung", "invoice", "mwst", "mehrwertsteuer"],
  "negative_hints": ["lieferschein", "packing slip", "bestellbestätigung"],
  "required_fields": ["date", "supplier", "amount"],
  "optional_fields": ["payment_method", "category", "payment_field"],
  "naming_schema": {
    "type_literal": "er",
    "template": "{date}_er_{category}_{supplier}_{amount}_{payment}",
    "fallback_values": {
      "date": "unknown-date",
      "supplier": "unknown-supplier",
      "amount": "unknown-amount"
    }
  },
  "target_folder_id": "ai",
  "fallback_folder_id": "unklar",
  "confidence_threshold": 0.5,
  "duplicate_policy": "flag"
}
```

### 8.2 Vertrag (contract) – Zielbild, noch nicht implementiert

```json
{
  "id": "vertrag",
  "label": "Vertrag",
  "description": "Vertragsunterlagen mit Vertragspartner und Thema. Zielbild – noch nicht implementiert.",
  "schema_version": "1.0",
  "enabled": false,
  "document_type": "contract",
  "classification_hints": ["vertrag", "contract", "vereinbarung", "rahmenvertrag", "lizenzvertrag"],
  "negative_hints": ["rechnung", "invoice", "lieferschein"],
  "required_fields": ["date", "party"],
  "optional_fields": ["topic", "reference_number", "valid_until"],
  "naming_schema": {
    "type_literal": "vertrag",
    "template": "{date}_vertrag_{party}_{topic}",
    "fallback_values": {
      "date": "unknown-date",
      "party": "unknown-party",
      "topic": "unbekannt"
    }
  },
  "target_folder_id": "ai",
  "fallback_folder_id": "unklar",
  "confidence_threshold": 0.6,
  "duplicate_policy": "flag",
  "ui_help_text": "Verträge mit Lieferanten, Partnern oder Behörden."
}
```

### 8.3 Steuerbescheid (tax_notice) – Zielbild, noch nicht implementiert

```json
{
  "id": "steuerbescheid",
  "label": "Steuerbescheid",
  "description": "Bescheid von Finanzamt oder Behörde. Zielbild – noch nicht implementiert.",
  "schema_version": "1.0",
  "enabled": false,
  "document_type": "tax_notice",
  "classification_hints": ["bescheid", "steuerbescheid", "finanzamt", "steuer", "umsatzsteuerbescheid"],
  "negative_hints": ["rechnung", "invoice"],
  "required_fields": ["date", "authority"],
  "optional_fields": ["topic", "year", "reference_number"],
  "naming_schema": {
    "type_literal": "bescheid",
    "template": "{date}_bescheid_{authority}_{topic}_{year}",
    "fallback_values": {
      "date": "unknown-date",
      "authority": "behoerde",
      "topic": "unbekannt",
      "year": "unbekannt"
    }
  },
  "target_folder_id": "ai",
  "fallback_folder_id": "unklar",
  "confidence_threshold": 0.6,
  "duplicate_policy": "flag"
}
```

### 8.4 Lieferschein (delivery_note) – Zielbild, noch nicht implementiert

```json
{
  "id": "lieferschein",
  "label": "Lieferschein",
  "description": "Lieferschein / Packing Slip. Zielbild – noch nicht implementiert.",
  "schema_version": "1.0",
  "enabled": false,
  "document_type": "delivery_note",
  "classification_hints": ["lieferschein", "packing slip", "packing list", "delivery note"],
  "negative_hints": ["rechnung", "invoice", "mwst"],
  "required_fields": ["date", "supplier"],
  "optional_fields": ["reference_number", "order_number"],
  "naming_schema": {
    "type_literal": "lieferschein",
    "template": "{date}_lieferschein_{supplier}_{reference}",
    "fallback_values": {
      "date": "unknown-date",
      "supplier": "unknown-supplier",
      "reference": "unbekannt"
    }
  },
  "target_folder_id": "ai",
  "fallback_folder_id": "unklar",
  "confidence_threshold": 0.6,
  "duplicate_policy": "skip"
}
```

### 8.5 Gutschrift (credit_note) – Zielbild, noch nicht implementiert

```json
{
  "id": "gutschrift",
  "label": "Gutschrift",
  "description": "Gutschrift eines Lieferanten. Zielbild – noch nicht implementiert.",
  "schema_version": "1.0",
  "enabled": false,
  "document_type": "credit_note",
  "classification_hints": ["gutschrift", "credit note", "credit memo", "erstattung", "rückerstattung"],
  "negative_hints": [],
  "required_fields": ["date", "supplier", "amount"],
  "optional_fields": ["reference_number"],
  "naming_schema": {
    "type_literal": "gutschrift",
    "template": "{date}_gutschrift_{supplier}_{amount}",
    "fallback_values": {
      "date": "unknown-date",
      "supplier": "unknown-supplier",
      "amount": "unknown-amount"
    }
  },
  "target_folder_id": "ai",
  "fallback_folder_id": "unklar",
  "confidence_threshold": 0.55,
  "duplicate_policy": "flag"
}
```

---

*Stand: Mai 2026. Zuletzt aktualisiert nach Phase 2b (UI-Profil-Editor für document_profiles implementiert).*
