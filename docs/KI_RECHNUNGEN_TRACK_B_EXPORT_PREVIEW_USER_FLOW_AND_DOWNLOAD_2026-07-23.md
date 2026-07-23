# Track-B Export Preview User Flow and Download

**Task ID:** `KI_RECHNUNGEN_TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_01`  
**Masterplan:** Prompt 16/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Nach Prompt 15 (Review-Bucket Usability) muss der Nutzer sichtbare Output-Artefakte prüfen können. Dieser Task implementiert einen kontrollierten **Preview Export** in den Sandbox-Test-Output — ohne Originale zu mutieren und ohne finale Produktivverarbeitung.

---

## Baseline from Prompt 15

- Classification: `TRACK_B_REVIEW_BUCKET_USABILITY_AND_ACTIONS_READY_COMMITTED_AND_PUSHED`
- Product status: `TRACK_B_REVIEW_BUCKET_USABILITY_AND_ACTIONS_READY`
- Review-Bucket: 5 Prüffälle, Liste + Detail, Preview-only-Aktionen (in-memory)
- Controlled input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` (5 PDFs)
- Controlled output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` (vorher leer / preview-only)
- Legacy final actions disabled; kein `run_once`; keine Writes

Noch nicht bewiesen war: sichtbares Preview-Export-Paket im Output-Ordner.

---

## Why previous output was empty

Track-B lief als Sandbox-/Dry-Run mit Ergebnis- und Review-State **nur in der UI**.  
Es gab In-Memory-Export-Vorschau (JSON/CSV-Report auf expliziten Pfad), aber **kein** Paket mit kopierten Preview-PDFs unter dem kontrollierten Output. Leerer Output war daher erwartetes Preview-only-Verhalten — nicht ein Schreibfehler.

---

## Preview export design

| Aspekt | Verhalten |
|---|---|
| Writer | `invoice_tool/ui_v2/preview_export.py` |
| Trigger | UI-CTA nach `ProcessingRunState.status == "completed"` |
| Ziel | nur positiv klassifizierte Sandbox-/Test-Output-Pfade |
| Paketname | `preview-export-<run-id>-<utc-stamp>/` |
| PDFs | byte-identische Kopien unter `files/` |
| Review | Prefix `REVIEW_REQUIRED__` |
| Reports | `README_PREVIEW_EXPORT.md`, `manifest.json`, `manifest.csv`, `review-items.md` |

---

## UI user flow

1. Kontrollierten Eingang/Ausgang wählen (`KI-Rechnungen-Test/input` + `output`).
2. Sandbox-Lauf erfolgreich abschließen (Result-State vorhanden).
3. Im Arbeitsbereich unter **Export-Vorschau** den Button  
   **„Preview-Export in Output-Ordner schreiben“** klicken.
4. UI zeigt: Preview-Export erstellt, Ordnerpfad, Kopienanzahl, Manifest/Report,  
   keine finalen Dateien / Originale unverändert / Produktiv gesperrt.
5. Output-Ordner öffnen und `preview-export-*` inspizieren.

Hinweise in der UI:

- schreibt nur ein Preview-Paket
- Originale bleiben unverändert
- keine finale Verarbeitung
- Produktiv gesperrt

Kein produktiver Final-Export-CTA.

---

## Output folder structure

Beispiel:

```text
/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/preview-export-<run-id>-<stamp>/
  README_PREVIEW_EXPORT.md
  manifest.json
  manifest.csv
  review-items.md
  files/
    REVIEW_REQUIRED__320262919974.pdf
    REVIEW_REQUIRED__420260091336.pdf
    REVIEW_REQUIRED__FA011466.pdf
    REVIEW_REQUIRED__Rechnung_RE-202605-14594.pdf
    REVIEW_REQUIRED__Rechnung-2026156019-102201.pdf
```

---

## Files written

- `README_PREVIEW_EXPORT.md` — Preview/Sandbox-Disclaimer, Safety, Pfade
- `manifest.json` — run_id, counts, items inkl. SHA-256
- `manifest.csv` — tabellarische Item-Liste
- `review-items.md` — wenn Review-Items vorhanden
- `files/*.pdf` — Preview-Kopien (byte-identisch)

---

## Safety guarantees

- Input/Output getrennt; Output muss Sandbox-/Test-Pfadpolitik bestehen
- Produktiv-/Original-Marker blockiert
- `productive_mode_requested=false`, `dry_run/preview_export=true`, `final_write=false`
- Keine Input-Mutation (kein Move/Rename/Delete/Archive)
- Kein `run_once`, kein Processing-Core-Import
- Keine Writes außerhalb des validierten Output-Roots
- Bei Fehler: kein unmarkiertes Teilpaket (Cleanup)

---

## Manifest/report content

`manifest.json` enthält u. a.:

- `run_id`, `generated_at`, `input_root`, `output_root`
- `item_count`, `copied_file_count`
- `recognized_count`, `review_count`, `error_count`, `planned_count`
- `items[]` mit `source_filename`, `preview_filename`, Status/Kategorie,
  `planned_target`, `review_required`, `source_sha256`, `preview_sha256`

README stellt klar: Preview/Sandbox, nicht final, Originale unverändert, Review manuell prüfen.

---

## Review-required handling

Ungelöste Prüffälle erhalten:

`REVIEW_REQUIRED__<sanitized-original-filename>.pdf`

Sanitisierung entfernt unsichere Zeichen; keine Path-Traversal-Namen.

---

## Test result

Focused Suite (Export + Prompt-15 + Smoke-Docs + Path Policy + Controlled Smoke + Track-A Protection): siehe Final Report / Audit.  
Zusätzlich: `tests/test_ui_v2_*.py` + `tests/test_saas_ui_v2_*.py` und `git diff --check`.

---

## What is now proven

- Nutzer kann nach erfolgreichem Sandbox-Result einen Preview-Export auslösen.
- Sichtbares Paket landet nur im kontrollierten Test-Output.
- Preview-PDFs sind byte-identisch; Input unverändert.
- Manifest/README/Review-Reports sind vorhanden und als Preview gekennzeichnet.
- Produktivpfade / Outside-Output bleiben blockiert.
- Track A / Processing-Core / Release-Tags unberührt.

---

## What is still not proven

- Manueller GUI-Smoke des Preview-Exports am Desktop (nächster Prompt)
- Finaler Approval-to-Write / produktiver Export
- Vollständige OCR/AI-Erkennung
- Track-A-Parität / Produktivordnerflows
- SaaS-/Production-Reife

---

## No productive processing

Ja — Preview-Paket only; kein Produktivlauf.

## No real invoice folders

Ja — nur kontrollierter Sandbox-/Testkontext bzw. Testdaten unter Sandbox-Pfadpolitik.

## Not SaaS-ready

Explizit **nicht SaaS-ready**.

## Not production-ready

Explizit **nicht production-ready**.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_GUI_MANUAL_SMOKE_01`
