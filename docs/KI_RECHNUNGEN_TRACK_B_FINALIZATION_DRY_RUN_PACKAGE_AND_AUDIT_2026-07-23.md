# Track-B Finalization Dry-Run Package and Audit

**Task ID:** `KI_RECHNUNGEN_TRACK_B_FINALIZATION_DRY_RUN_PACKAGE_AND_AUDIT_01`  
**Masterplan:** Prompt 31/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_FINALIZATION_DRY_RUN_PACKAGE_AND_AUDIT_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.  
In dieser Phase gilt: **`final_write_allowed=false`**.

---

## Purpose

Implementiert ein sicheres, nicht-produktives Finalisierungs-Trockenlauf-Paket mit Audit-Ausgabe für Track B.

Aus einer `FinalizationPreviewBatch` entsteht ein prüfbares Paket unter dem kontrollierten Sandbox-Output — mit Manifest, Audit, Plan und Ready-/Blocked-/Conflict-Reports. Kein finales Schreiben, keine Originale verändert, kein `run_once`.

Korrekte Sequenz:

1. Review decisions existieren  
2. `FinalizationPreviewBatch` gruppiert und validiert sie  
3. `FinalizationDryRunPackage` schreibt nur Audit-/Plan-Artefakte  
4. Nutzer kann geplante spätere Aktionen und Blocker prüfen  
5. Finales Schreiben bleibt deaktiviert  
6. Ein späterer, explizit freigegebener Task darf Final-Write-Gating entwerfen/implementieren

---

## Baseline from Prompt 30

- `FinalizationPreviewBatch` mit Counts und Conflict-Modell  
- Review-UI „Finalisierungs-Vorschau“  
- Preview-Export-Manifest mit Batch-/Item-Feldern  
- `final_write_allowed=false`  
- Product status vorher: `TRACK_B_FINALIZATION_PREVIEW_BATCH_AND_CONFLICTS_READY`  
- HEAD Baseline: `cf8c9d9dbce5f6915e0eca33795cf76560b372cf`

---

## FinalizationDryRunPackage model

Modul: `invoice_tool/ui_v2/finalization_dry_run_package.py`

Felder:

- `package_id`, `batch_id`, `preview_state_id`, `source_run_id`, `created_at`
- `input_root`, `output_root`, `package_root`
- `dry_run_package=true`
- `final_write_allowed=false`
- `productive_mode_requested=false`
- `source_mutation=false`
- `final_files_written=false`
- `originals_moved/renamed/archived/deleted=false`
- Counts: `total_items`, `ready_count`, `blocked_count`, `ignored_count`, `deferred_count`, `still_review_required_count`
- `artifacts`, `safety_summary`, Item-Records, Conflicts

Item-Records enthalten u. a.:

- `source_filename`, `source_sha256`, `preview_sha256`
- `approved_preview_filename`, `target_preview_path`
- `review_decision`, `finalization_status`
- `finalization_blockers`, `finalization_warnings`, `conflicts`
- `ready_for_future_finalization` yes/no
- `final_write_allowed=false`
- `would_copy_or_rename_source_to_target` (Plan-Text only)

---

## Package writer

`write_finalization_dry_run_package(...)` / `apply_finalization_dry_run_package(state)`

- schreibt nur unter kontrolliertem Sandbox-/Test-Output
- Ordnerpräfix: `finalization-dry-run-` + Run-/Package-ID + Timestamp
- erzeugt **keine** finalen PDFs
- führt geplante Operationen **nicht** aus

---

## Package artifacts

Pflicht:

- `README_FINALIZATION_DRY_RUN.md`
- `finalization-dry-run-manifest.json`
- `finalization-dry-run-manifest.csv`
- `finalization-audit.md`
- `finalization-plan.md`
- `conflicts.md`
- `blocked-items.md`
- `ready-items.md`

Optional ergänzt:

- `ignored-items.md`
- `deferred-items.md`
- `still-review-required.md`

README stellt klar:

- Trockenlauf / Dry Run  
- kein finales Produktions-Output  
- Originale unverändert  
- keine finalen PDFs  
- `final_write_allowed=false`  
- Finalisierung braucht spätere explizite Autorisierung  

---

## UI action

Review-UI zeigt:

- „Finalisierungs-Trockenlauf erstellen“
- „Audit-Paket erzeugen“
- „Nur prüfen — nichts final schreiben“
- Paketpfad nach Erstellung
- Counts / Conflict-Zusammenhang über Batch-Summary

---

## Preview export integration

Preview-Export-Manifest enthält:

- `finalization_dry_run_package_available`
- `finalization_dry_run_package_path` (falls erzeugt)
- `finalization_dry_run_package_id`
- `final_write_allowed=false`

---

## Safety gates

Writer lehnt ab:

- Output außerhalb kontrollierter Sandbox/Test-Policy  
- `package_root` außerhalb `output_root`  
- `final_write_allowed=true`  
- produktiver Modus / `run_once`  
- fehlender Batch  
- stale Preview-State (wenn erkannt)  
- reale Rechnungsordner-Ziele laut Path Policy  

---

## Controlled output policy

- nur explizite Sandbox-/Test-Pfade (`is_explicit_copied_sandbox_test_path`)
- harte Produktivmarker und Original-Heuristiken blockieren
- Paketordnername beginnt mit `finalization-dry-run-`
- Paket enthält Markdown/JSON/CSV — keine finalen Produktions-PDFs

---

## What is now proven

- Dry-Run-Package-Modell mit Safety-Flags  
- Writer erzeugt prüfbares Artefakt-Paket  
- UI-CTA und Labels vorhanden  
- Preview-Export-Metadaten angebunden  
- Focused Tests + Track-A-Schutz  
- `final_write_allowed` bleibt false  

---

## What is still not proven

- Controlled Final Write Gate Design (nächster Prompt)  
- tatsächliche Final-Write-Pipeline unter Safety Gates  
- manueller Full-GUI-Durchlauf mit produktiver Freigabe (bewusst out of scope)

---

## Test result

Siehe Audit — Focused + UI-v2/SaaS Suite + `git diff --check`.

---

## No productive processing

Ja — Dry-Run-/Audit-Artefakte only.

## No real invoice folders

Ja — Controlled-/Sandbox-Kontext; keine realen Rechnungsordner.

## Not SaaS-ready

Explizit nicht SaaS-ready.

## Not production-ready

Explizit nicht production-ready.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_GATE_DESIGN_01`
