# Track-B Canonical Filename Template and Category Mapping Repair

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_REPAIR_01`  
**Masterplan:** Prompt 19/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, nicht SaaS-ready, nicht production-ready.

---

## Purpose

Track-B Suggested-Filenames auf das kanonische Muster bringen:

`<YYMMDD>_<DOCUMENT_DIRECTION>_<BUSINESS_CATEGORY>_<COUNTERPARTY_NAME>_<AMOUNT>.pdf`

Preview-Export nutzt:

`REVIEW_REQUIRED__SUGGESTED__<canonical>.pdf`

---

## User observation

Prompt-18-Namen enthielten Datum/Name/Betrag, aber **keine** Rechnungsart und **keine** Zuordnung:

- `REVIEW_REQUIRED__SUGGESTED__260523_Böttcher_AG_84.39.pdf`

Erforderlich z. B.:

- `REVIEW_REQUIRED__SUGGESTED__260523_Eingangsrechnung_Architektur_Böttcher_AG_84.39.pdf`
- oder bei unklarer Zuordnung: `…_Eingangsrechnung_Unklare_Zuordnung_Böttcher_AG_84.39.pdf`

---

## Baseline from Prompt 18

- Classification: `TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_READY_COMMITTED_AND_PUSHED`
- HEAD: `6efa0a955d1d9fc7eba183200a8e82986d3962f4`
- Lokale Texttextextraktion liefert Lieferant/Datum/Betrag für 5/5 PDFs
- Muster war `{invoice_date}_{supplier}_{amount}.pdf`
- Review blieb `REVIEW_REQUIRED`

---

## Required canonical filename pattern

1. Datum (`YYMMDD`)
2. Rechnungsart: `Eingangsrechnung` / `Ausgangsrechnung` / `Unklare_Rechnungsart`
3. Zuordnung: `Architektur` / `Innenarchitektur` / `Event_and_Production` / `Privat` / `Unklare_Zuordnung`
4. Gegenpartei/Name
5. Betrag

---

## Current gap (before this task)

- Document direction und Business category wurden nicht in den Dateinamen übernommen
- `document_type` war nur `rechnung`/`storno`, nicht Rechnungsart
- Keine Zuordnungsschicht — und kein erlaubtes Blind-Default auf Architektur

---

## Implemented canonical template

Neu: `invoice_tool/ui_v2/canonical_filename_template.py`

- `build_canonical_filename`
- `map_document_direction`
- `map_business_category`
- `filename_template_version = track_b_canonical_v1`

`suggested_filename_mapping.py` rendert über dieses Template.

---

## Document direction mapping

- Explizite Richtung / Alias → kanonischer Wert
- Caller-provided `own_issuer_hints` (ohne private Hardcodes) → ggf. `Ausgangsrechnung`
- Externer Lieferant + invoice-like `document_type` → `Eingangsrechnung`
- Sonst → `Unklare_Rechnungsart` + Review

---

## Business category mapping

- Routing-/Profil-/Ordner-Labels (Aliase) → kanonische Werte
- **Kein** Default auf `Architektur`
- Unsicher → `Unklare_Zuordnung` + Review

---

## Unknown-field behavior

| Feld | Marker |
|---|---|
| Rechnungsart | `Unklare_Rechnungsart` |
| Zuordnung | `Unklare_Zuordnung` |
| Datum/Name/Betrag | `Unklar` + `naming_reason` / `missing_fields` |

---

## UI/report propagation

Review/Manifest/CSV/review-items zeigen u. a.:

- Vorschau-Dateiname
- Rechnungsart
- Zuordnung
- Name
- Betrag
- fehlende Felder
- Benennung noch nicht final
- `canonical_filename`, `filename_template_version`, `naming_reason`, `naming_confidence`

---

## Controlled 5-PDF verification result

Input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`  
Output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`

Erwartete Struktur (Beispiel):

`REVIEW_REQUIRED__SUGGESTED__260523_Eingangsrechnung_Unklare_Zuordnung_Böttcher_AG_84.39.pdf`

Für die 5 kopierten PDFs:

- Datum / Name / Betrag aus lokaler Extraktion
- Rechnungsart: `Eingangsrechnung` (externer Lieferant + invoice-like)
- Zuordnung: `Unklare_Zuordnung` (kein sicheres Routing/Profil-Label im Sandbox-Lauf)
- Input unverändert, Preview-only

---

## Safety guarantees

- Preview / Sandbox only
- Input unverändert
- Keine finalen Produktivdateien
- Keine realen Rechnungsordner
- Kein `run_once`
- Keine privaten Tenant-Defaults in generischer Logik
- Nicht SaaS-ready
- Nicht production-ready
- Release-Tags unverändert

---

## Remaining gap

- Sichere Zuordnung zu Architektur / Innenarchitektur / Event_and_Production / Privat braucht noch Routing-/Profil-Signale oder eine spätere Klassifikationsstufe
- Lokale Heuristik ≠ volle interne AI/OCR-Qualität
- Keine finale Produktiv-Umbenennung

---

## Relation to internal app behavior

Interne Richtungslogik existiert in `routing_guards.py` (inkl. profilbezogener Issuer-Hints). Track-B spiegelt nur eine **sandbox-sichere** Ableitung ohne private Hardcodes und ohne productive Write-Pfade. Track A unverändert.

---

## Test result

Focused Prompt-19/18 + angrenzende Track-B-Tests sowie UI-v2/SaaS-Suite (siehe Audit).  
`git diff --check` clean erwartet.

---

## No productive processing

Bestätigt.

## No real invoice folders

Bestätigt — nur kontrollierte Testordner.

## nicht SaaS-ready

Bestätigt.

## nicht production-ready

Bestätigt.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CANONICAL_FILENAME_PREVIEW_EXPORT_GUI_SMOKE_01`

Ziel: GUI-Smoke mit kanonischen Preview-Export-Dateinamen.
