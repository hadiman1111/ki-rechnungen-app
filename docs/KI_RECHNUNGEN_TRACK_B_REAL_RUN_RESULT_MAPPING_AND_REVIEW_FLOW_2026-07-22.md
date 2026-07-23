# Track-B Real Run Result Mapping and Review Flow

**Task ID:** `KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_01`  
**Masterplan:** Prompt 4/34  
**Date:** 2026-07-22

## Purpose

Echte `CoreDryRunResult`-Daten aus dem Prompt-3-Bridge-Lauf für Track-B Workspace und Prüffluss nutzbar machen — ohne produktive Verarbeitung, ohne Originalmutation, ohne Fake-Erfolge.

## What changed

- Neue Mapping-Schicht `invoice_tool/ui_v2/result_mapping.py`
- Reichere `ProcessingRunState`-Felder: `error_items`, `planned_destinations`, `outcome_kind`, `detailed_item_mapping_complete`
- `core_bridge` delegiert die Ergebnisabbildung an `result_mapping`
- `run_result_display` zeigt Buckets, Warnungen, Zielvorschau, Safety-Proof
- `review_state` / `review_components` verdrahten denselben Laufzustand in den Prüffluss
- Export/Reporting liest strukturierte geplante Ziele, bleibt preview-only

## Result mapping

`map_core_dry_run_result_to_processing_run_state(CoreDryRunResult)` liefert:

| Feld | Quelle |
|------|--------|
| `run_id` | Dry-Run |
| `status` | COMPLETED / COMPLETED_WITH_REVIEW → completed; FAILED; BLOCKED |
| `results` | `recognized` |
| `review_items` | `review` |
| `error_items` / `errors` | `errors` |
| `planned_destinations` / count | `planned_destinations` (applied=False, preview_only=True) |
| `warnings` | Dry-Run-Warnungen |
| `safety_proof_summary` | „Originale unverändert · Produktiv gesperrt · Export Vorschau“ |
| `outcome_kind` | empty / all_review / mixed / failed / … |

Keine erfundenen Dokumentzeilen. Fehlen Detailzeilen trotz Aggregatzahlen → `detailed_item_mapping_complete=False`.

## Bucket model

1. **Erkannt / geplant** — sandbox-geplant, nicht produktiv verarbeitet  
2. **Zur Prüfung** — menschliche Entscheidung nötig  
3. **Fehler** — Dry-Run konnte nicht klassifizieren/vorbereiten  
4. **Warnungen** — Hinweise (z. B. OCR nicht ausgeführt)  
5. **Sicherheitsnachweis** — Originale unverändert · Produktiv gesperrt · Export Vorschau  

Leere Eingänge → `outcome_kind=empty`, kein fingierter Erfolg.

## Review flow behavior

- Prüffälle nur aus `review_items`
- Fehler getrennt (`error_items` / Error-Sektion)
- Erkannte Dokumente nicht in der Prüfliste
- Geplante Ziele nur als Vorschau inspizierbar
- Aktionen disabled; keine Übernehmen-/Buchen-/Verschieben-/Umbenennen-/Final-ausführen-Aktion

## Workspace display behavior

- Status completed / mit Prüffällen / fehlgeschlagen / blockiert
- Count-Zeile: Erkannt · Prüfung · Fehler · Geplant
- Safety-Proof-Zeile
- Leerer Lauf ehrlich markiert
- Gleiche `ProcessingRunState` wie Review

## Safety proof display

Kompakte Zeile überall dort, wo ein Dry-Run-Ergebnis angezeigt wird:

`Originale unverändert · Produktiv gesperrt · Export Vorschau`

## Export/reporting preview limitation

Export bleibt lokal preview-only (`preview=true`, kein DATEV-/Cloud-Produktivexport).  
Vollständige Export-/Reporting-Parity → Prompt 5/34.

## What remains for Prompt 5/34 and Prompt 6/34

- **Prompt 5/34:** Export/Reporting-Vorschau polieren / Parity  
- **Prompt 6/34:** Local-Pilot-Acceptance-Gate  

## Why local pilot is still pending

Kein Acceptance-Gate, kein produktiver Modus, keine reale Rechnungsordner-Verarbeitung, kein Pilot-Claim.

## Tests

- `tests/test_ui_v2_real_run_result_mapping_and_review_flow.py`
- Focused Suite inkl. Bridge / Core-Dry-Run / Workspace / Track-A-Schutz
- Vollständige UI-v2 / SaaS-UI-v2 Suite

## Product status after task

`TRACK_B_REAL_RUN_RESULT_MAPPING_AVAILABLE_PENDING_EXPORT_AND_ACCEPTANCE`
