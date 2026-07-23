# Track-B Extraction and Suggested Filename Mapping Repair

**Task ID:** `KI_RECHNUNGEN_TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_REPAIR_01`  
**Masterplan:** Prompt 18/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, nicht SaaS-ready, nicht production-ready.

---

## Purpose

Track-B so verdrahten, dass für kopierte Real-PDFs sichere vorgeschlagene Dateinamen aus lokaler Texttextextraktion entstehen und im Review/Preview-Export sichtbar werden — ohne finale Produktivnamen und ohne Input-Mutation.

---

## Baseline from Prompt 17

- Classification: `TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_IMPROVED_COMMITTED_AND_PUSHED`
- HEAD: `333872a93219402eea5ee1ee6eaa1d75598c72d7`
- Preview-Export nutzt bereits `REVIEW_REQUIRED__SUGGESTED__…` wenn ein abweichender Vorschlag existiert
- Für die 5 Real-PDFs fehlten Extraktions-/Mapping-Daten → Fallback auf Originalnamen
- Manifest hatte `filename_source` / `naming_reason`, aber keine Lieferant/Datum/Betrag-Felder

---

## Internal app naming diagnosis

1. Die interne App extrahiert Felder über OCR/AI (`invoice_tool/extraction.py`, OpenAI Vision) und Normalisierung.
2. Dateinamen entstehen über Routing-Templates (`render_routing_filename_template` / `build_runtime_filename` in `target_routing.py`, Muster z. B. `{invoice_date}_{supplier}_{amount}_{payment_field}.pdf`).
3. Schreiben/Archivieren läuft über `processing.py` / Lifecycle (`publish_output_atomically`, Archive) — stark an produktive Write-/Move-/Archive-Pfade gekoppelt.
4. `core_dry_run.py` ist absichtlich minimal: PDFs → Review, **kein OCR/AI**, `planned_path` behält den Original-Basename.
5. Track-B rief bisher keinen Naming-Planner auf; Result-Mapping transportierte keine Extraktionsfelder.

---

## Track-B gap diagnosis

| Ursache | Befund |
|---|---|
| Core Dry-Run minimal | ja — PDFs ohne Extraktion |
| AI/OCR disabled in dry-run | ja, bewusst |
| Adapter droppt Felder | nein — Felder existierten gar nicht |
| Result mapping droppt Felder | sekundär — nichts zum Mappen |
| Preview export ignore | nein — Export war vorbereitet |
| Profile/config missing | nicht die Primärursache für diese 5 PDFs |
| PDFs unlesbar | nein — alle 5 haben Texttextlayer |

---

## Implemented mapping/bridge

Neu (nur Track-B / UI-v2):

- `invoice_tool/ui_v2/suggested_filename_mapping.py` — sicheres Mapping aus strukturierten Feldern
- `invoice_tool/ui_v2/extraction_mapping.py` — lokale PDF-Textlayer-Extraktion (PyMuPDF), keine AI/OCR/Network, nur Sandbox-Pfade
- Enrichment in `sandbox_execution_boundary.sandbox_core_runner` nach Dry-Run
- Propagation über `ProcessingPlannedDestination`, Review-UI, Preview-Export/Manifest

Nicht geändert: Track-A-UI, processing-core, `run_once`, Release-Tags.

---

## Suggested filename fields

- `supplier` / vendor
- `invoice_date`
- `amount`
- `document_type`
- `payment_account` (nur Kurz-Kategorie: paypal/card/transfer — nie IBAN/PAN)
- `suggested_filename`
- `filename_source`
- `naming_confidence`
- `naming_reason`
- `suggested_filename_fields`

---

## Preview export behavior after repair

- Mit Vorschlag: `REVIEW_REQUIRED__SUGGESTED__<safe>.pdf`
- Ohne Vorschlag: `REVIEW_REQUIRED__<original>.pdf`
- Manifest enthält Extraktions-/Naming-Felder
- Review bleibt `REVIEW_REQUIRED` bis zur späteren Freigabe

---

## Controlled 5-PDF verification result

Input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`  
Output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`

Lokale Extraktion (Textlayer) liefert für alle 5 PDFs sinnvolle Vorschläge, u. a.:

| Quelle | Beispiel-Vorschlag |
|---|---|
| `320262919974.pdf` | `260523_Böttcher_AG_84.39.pdf` |
| `420260091336.pdf` | `260618_Böttcher_AG_68.94.pdf` |
| `FA011466.pdf` | `260511_LUMITOP_500.00.pdf` |
| `Rechnung RE-202605-14594.pdf` | `260515_1A-Bootshop.de_80.55.pdf` |
| `Rechnung-2026156019-102201.pdf` | `260511_Luxvenum_LED_GmbH_154.95.pdf` |

Input-Digests bleiben unverändert. Kein `run_once`, keine Produktivordner.

Hinweis: Beträge/Supplier sind lokale Heuristik (nicht identisch mit interner AI-Pipeline). Preview-only.

---

## Safety guarantees

- Preview / Sandbox only
- Input unverändert
- Keine finalen Produktivdateien
- Keine realen Rechnungsordner
- Kein `run_once`
- Kein AI/OCR-Netzaufruf in dieser Bridge
- Nicht SaaS-ready
- Nicht production-ready
- Release-Tags unverändert

---

## Remaining gap

- Lokale Heuristik ≠ volle interne AI/OCR-/Routing-Qualität (z. B. Betrag FA011466 Basispreis vs. Total)
- Keine finale Produktiv-Umbenennung / kein Approve-Write
- Kein DATEV-/Cloud-Export

---

## Relation to internal app behavior

Konzeptuell gleiche Naming-Idee (Datum/Lieferant/Betrag), aber Track-B nutzt eine **read-only Sandbox-Bridge** statt des produktiven Processing-/Archive-Pfads. Track A bleibt unverändert.

---

## Test result

Focused + Track-B/UI-v2/SaaS-Suite (siehe Audit).  
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

`KI_RECHNUNGEN_TRACK_B_SUGGESTED_FILENAME_PREVIEW_EXPORT_GUI_SMOKE_01`

Ziel: GUI-Smoke mit den jetzt vorhandenen Vorschlagsnamen im Preview-Export.
