# Track-B Finalization Preview Batch and Conflicts

**Task ID:** `KI_RECHNUNGEN_TRACK_B_FINALIZATION_PREVIEW_BATCH_AND_CONFLICTS_01`  
**Masterplan:** Prompt 30/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_FINALIZATION_PREVIEW_BATCH_AND_CONFLICTS_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.  
In dieser Phase gilt: **`final_write_allowed=false`**.

---

## Purpose

Implementiert eine sichere, nicht-produktive Finalisierungs-Vorschau-Batch- und Konfliktübersicht für Track B.

Review-Entscheidungen werden gruppiert, gezählt und auf Konflikte/Blocker geprüft — ohne finales Schreiben, ohne Originale zu verändern und ohne `run_once`.

Korrekte Sequenz:

1. Review decisions existieren  
2. `FinalizationPreviewBatch` gruppiert und validiert sie  
3. Nutzer sieht, was später bereit wäre  
4. Blocker/Konflikte sind sichtbar  
5. Finales Schreiben bleibt deaktiviert  
6. Ein späterer, explizit freigegebener Task darf Final-Write-Gating implementieren

---

## Baseline from Prompt 29

- ReviewDecision- und FinalizationReadiness-State implementiert  
- Sechs Decision-Aktionen in der Review-UI  
- Accept zweistufig; Edited-Filename-Validierung  
- Duplicate/Conflict-Erkennung auf Preview-State-Ebene  
- Manifest/review-items mit Decision-/Readiness-Feldern  
- `final_write_allowed=false`  
- Product status vorher: `TRACK_B_REVIEW_DECISION_STATE_AND_UI_FLOW_READY`  
- HEAD Baseline: `d44047231fc5a5d469854436b4e02940224204f7`

---

## FinalizationPreviewBatch model

Modul: `invoice_tool/ui_v2/finalization_preview_batch.py`

Felder:

- `batch_id`, `preview_state_id`, `created_at`, `source_run_id`
- `input_root`, `output_root`
- `final_write_allowed=false`, `productive_mode_requested=false`, `source_mutation=false`
- Counts: `total_items`, `ready_count`, `blocked_count`, `ignored_count`, `deferred_count`, `still_review_required_count`
- `items`, `conflicts`, `warnings`, `safety_summary`

---

## Batch item model

`FinalizationPreviewBatchItem`:

- `item_id`, `source_filename`, `review_decision_type`, `approved_by_user`
- `approved_preview_filename`, `target_preview_path`
- `finalization_status`:
  - `ready_for_future_finalization`
  - `blocked`
  - `ignored`
  - `deferred`
  - `still_review_required`
- `finalization_readiness`, `blockers`, `warnings`
- `source_hash_at_decision`, `preview_state_id`
- `final_write_allowed=false`, `target_conflict_status`

---

## Conflict model

`FinalizationPreviewConflict`:

- `conflict_id`, `conflict_type`, `affected_item_ids`
- `severity`, `message`, `blocking`, `suggested_resolution`

Conflict types:

- `duplicate_target_filename`, `duplicate_target_path`
- `unsafe_target_path`, `stale_preview_state`, `changed_source_hash`
- `missing_approval`, `missing_required_field`
- `unresolved_configuration`, `incomplete_filename`
- `ignored_item`, `deferred_item` (informativ, nicht blockierend)

---

## Batch builder behavior

`build_finalization_preview_batch(...)` — pure/state-only:

- nimmt alle aktuellen Review-Items inkl. Decisions/Readiness
- Status-Mapping laut Decision-Typ und Blockern
- Accept/Edit → `ready_for_future_finalization` nur ohne Blocker
- Duplikate blockieren alle betroffenen Items
- unsichere Ziele, stale State, Source-Hash-Änderung blockieren
- `final_write_allowed` bleibt immer `false`

---

## UI summary

Review-UI zeigt „Finalisierungs-Vorschau“ mit:

- Bereit für spätere Finalisierung: X  
- Blockiert: Y  
- Ignoriert / Zurückgestellt / Weiterhin zur Prüfung  
- Safety: **„Noch kein finales Schreiben — Originale bleiben unverändert.“**  
- bei Konflikten: Typ, Anzahl, Message, suggested_resolution  

---

## Preview export/manifest fields

Batch-Ebene:

- `finalization_preview_batch`
- `final_write_allowed=false`
- `ready_count`, `blocked_count`, `ignored_count`, `deferred_count`, `still_review_required_count`
- `conflicts`, `safety_summary`

Item-Ebene:

- `finalization_status`
- `finalization_blockers`, `finalization_warnings`
- `target_conflict_status`
- `final_write_allowed=false`

Export bleibt preview-only.

---

## Safety guarantees

- keine finalen Dateien  
- keine Source-Mutation  
- kein `run_once`  
- kein Archive/Delete/Rename von Originalen  
- keine realen Rechnungsordner  
- kein SaaS-ready-/production-ready-Claim  
- Track A / Processing-Core unverändert  

---

## What is now proven

- FinalizationPreviewBatch-/Item-/Conflict-Modelle im Code  
- Batch-Builder mit Counts und Konflikt-Erkennung  
- UI-Batch-Summary inkl. Safety-Text  
- Manifest-/Item-Felder für Batch  
- `final_write_allowed=false` überall  
- Focused Tests + Track-A-Schutz  

---

## What is still not proven

- Finalization Dry-Run Package & Audit (nächster Prompt)  
- tatsächliche Final-Write-Pipeline unter Safety Gates  
- manueller Full-GUI-Durchlauf mit produktiver Freigabe (bewusst out of scope)

---

## Test result

Siehe Audit — Focused + UI-v2/SaaS Suite + `git diff --check`.

---

## No productive processing

Ja — Batch/Preview/Audit only.

## No real invoice folders

Ja — Controlled-/Sandbox-Kontext; keine realen Rechnungsordner.

## Not SaaS-ready

Explizit nicht SaaS-ready.

## Not production-ready

Explizit nicht production-ready.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_FINALIZATION_DRY_RUN_PACKAGE_AND_AUDIT_01`
