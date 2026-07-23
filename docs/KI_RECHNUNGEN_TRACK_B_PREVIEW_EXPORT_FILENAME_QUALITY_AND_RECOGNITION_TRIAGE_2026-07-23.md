# Track-B Preview Export Filename Quality and Recognition Triage

**Task ID:** `KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_AND_RECOGNITION_TRIAGE_01`  
**Masterplan:** Prompt 17/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_PREVIEW_EXPORT_FILENAME_QUALITY_IMPROVED`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Diagnose und Verbesserung der Preview-Export-Dateinamen in Track-B: Warum erscheinen alle PDFs als `REVIEW_REQUIRED__…`, und wie können sichere Vorschlagsnamen genutzt werden, ohne finale Produktivnamen zu behaupten.

---

## User observation

Im Output-Ordner liegen Preview-PDFs, aber alle Dateinamen starten mit `REVIEW_REQUIRED__` und behalten den Originalnamen. Der Nutzer erwartet zu sehen, was das System aus den Rechnungen machen würde (wie in der internen Hadi-App mit echten Umbenennungen).

---

## Baseline from Prompt 16

- Classification: `TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_READY_COMMITTED_AND_PUSHED`
- HEAD: `70fc810535287ca2d1776784de9a76d38ad6d42e`
- Preview-Export schreibt Paket unter kontrolliertem Output
- PDFs byte-identisch; Review-Fälle mit Prefix `REVIEW_REQUIRED__`
- CTA: „Preview-Export in Output-Ordner schreiben“
- Keine produktive Verarbeitung, keine Input-Mutation

---

## Latest preview-export evidence

Inspected folder:

`/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/preview-export-manual-verify-16-20260723T071458840917Z`

| Source | Preview | Status | Review | planned_target | suggested meaningful name |
|---|---|---|---|---|---|
| `320262919974.pdf` | `REVIEW_REQUIRED__320262919974.pdf` | unklar | yes | `preview/320262919974.pdf` | **nein** (Basename = Original) |
| `420260091336.pdf` | `REVIEW_REQUIRED__420260091336.pdf` | unklar | yes | `preview/420260091336.pdf` | **nein** |
| `FA011466.pdf` | `REVIEW_REQUIRED__FA011466.pdf` | unklar | yes | `preview/FA011466.pdf` | **nein** |
| `Rechnung RE-202605-14594.pdf` | `REVIEW_REQUIRED__Rechnung RE-202605-14594.pdf` | unklar | yes | `preview/Rechnung RE-202605-14594.pdf` | **nein** |
| `Rechnung-2026156019-102201.pdf` | `REVIEW_REQUIRED__Rechnung-2026156019-102201.pdf` | unklar | yes | `preview/Rechnung-2026156019-102201.pdf` | **nein** |

Manifest hatte zuvor: `planned_target`, aber **kein** `suggested_filename` / `filename_source` / `naming_reason`.  
Keine Supplier-/Datum-/Betragsfelder in den Export-Zeilen.

---

## Why files are REVIEW_REQUIRED

1. Track-B Sandbox-Dry-Run klassifiziert alle 5 PDFs als Review (`unklar` / `all_review`).
2. Preview-Export markiert Review-Fälle bewusst mit `REVIEW_REQUIRED__` (Sicherheit, keine finale Freigabe).
3. Das ist **korrektes Safety-Verhalten** für ungelöste Prüffälle — nicht ein Schreibfehler.

---

## Whether planned/suggested names exist

- **planned_target:** ja, aber nur `preview/<original-filename>` — Ordner-/Pfad-Hinweis ohne abweichenden Rechnungsdateinamen.
- **suggested_filename / sinnvolle Umbenennung:** nein in der Prompt-16-Evidenz.
- **supplier/date/amount:** nicht im Track-B Result-/Export-State vorhanden.
- Ursache der „nur REVIEW_REQUIRED“-Namen: fehlende Extraktion/Mapping in Track-B, **nicht** allein aggressives Prefixing bei vorhandenem Vorschlagsnamen.

---

## Naming quality result

| Aspekt | Ergebnis |
|---|---|
| Safety Prefix für Review | bleibt |
| Nutzung abweichender geplanter Namen | jetzt: `REVIEW_REQUIRED__SUGGESTED__<safe>.pdf` |
| Fallback ohne Vorschlag | `REVIEW_REQUIRED__<sanitized-original>.pdf` |
| Fake-Metadaten | verboten / nicht erfunden |
| Manifest-Transparenz | `filename_source`, `naming_reason`, `suggested_filename`, `planned_target` |

Aktuelle 5 Real-PDFs fallen weiter auf Original-Fallback, weil Track-B keine abweichenden Vorschlagsnamen liefert. Die Export-Schicht ist vorbereitet; die Erkennungslücke bleibt.

---

## Improvements implemented

- `invoice_tool/ui_v2/preview_export.py`: `resolve_preview_naming`, Suggested-Prefix, Manifest-/CSV-/README-/review-items-Felder
- Review-UI: Vorschau-Dateiname, Grund für REVIEW_REQUIRED, Geplantes Ziel, „Benennung noch nicht final“
- Workspace-Helper-Text nennt Namensfelder und Nicht-Finalität
- Keine Track-A-/Core-Änderungen, keine produktiven Writes

---

## Remaining recognition/mapping gap

Track-B Dry-Run / Result-Mapping liefert für die kontrollierten PDFs weiterhin:

- nur Review-Buckets ohne „erkannt“
- `planned_path` mit Original-Basename
- keine Extraktionsfelder für Lieferant/Datum/Betrag
- keine Mapping-Pipeline wie in der internen App für finale Umbenennung

Nächster Reparaturschritt muss Extraction + suggested-filename Mapping adressieren — ohne Track A zu öffnen und ohne Produktivwrites.

---

## Relation to internal app behavior

Die interne Hadi-App kann echte umbenannte Outputs erzeugen (Track A / Core). Track-B darf diese Logik später nur über sichere, isolierte Bridges wiederverwenden — **nicht** durch Öffnen von Track-A-UI oder `run_once`/Produktivpfaden jetzt. Konzeptuell: gleiche Naming-Idee, anderer Sicherheitsrahmen (Preview + REVIEW_REQUIRED).

---

## Safety guarantees

- Preview Export only
- Input unverändert
- Keine finalen Produktivdateien
- Keine realen Rechnungsordner
- Kein `run_once`
- Nicht SaaS-ready
- Nicht production-ready
- Release-Tags unverändert

---

## Test result

Focused + Track-B/UI-v2/SaaS-Suite (siehe Audit).  
`git diff --check` clean erwartet.

---

## No productive processing

Bestätigt.

## No real invoice folders

Bestätigt — nur `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/…`.

## Not SaaS-ready

Bestätigt.

## Not production-ready

Bestätigt.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_EXTRACTION_AND_SUGGESTED_FILENAME_MAPPING_REPAIR_01`

Ziel: Track-B Dry-Run/Mapping so reparieren, dass sichere geplante/vorgeschlagene Dateinamen (Lieferant/Datum/Betrag-Kontext) in den Result-State gelangen — weiterhin Preview-only.
