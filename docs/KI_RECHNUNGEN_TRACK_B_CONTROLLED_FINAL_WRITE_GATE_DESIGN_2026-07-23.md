# Track-B Controlled Final Write Gate Design

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_GATE_DESIGN_01`  
**Masterplan:** Prompt 32/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CONTROLLED_FINAL_WRITE_GATE_DESIGN_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.  
In dieser Phase gilt: **`final_write_allowed=false`**.  
`final_write_execution_available=false` in this phase.  
No runtime/code changes are expected — design/specification only.  
No final files written.

---

## Purpose

Dieses Design spezifiziert das kontrollierte Final-Write-Gate für Track B: die exakten Bedingungen, unter denen ein **späterer** Task finale Dateien schreiben darf — und die harten Bedingungen, unter denen Final Write **immer** blockiert bleibt.

Ein Controlled Final Write Gate ist **kein** finales Schreiben.

Korrekte Sequenz:

1. Review decisions  
2. `FinalizationPreviewBatch`  
3. `FinalizationDryRunPackage`  
4. `ControlledFinalWriteGate` design (dieser Task)  
5. später explizit autorisierte Final-Write-Implementierung  
6. erst dann kontrolliertes Final-Output — und nur, wenn jedes Gate besteht

In diesem Task: **keine** finalen Dateien schreiben, keine Originale bewegen/umbenennen/archivieren/löschen, kein `run_once`, kein produktiver Pfad.

---

## Baseline from Prompt 31

- `FinalizationDryRunPackage` existiert (`invoice_tool/ui_v2/finalization_dry_run_package.py`).
- Dry-run package model inkl.:
  - `dry_run_package=true`
  - `final_write_allowed=false`
  - `productive_mode_requested=false`
  - `source_mutation=false`
  - `final_files_written=false`
  - `originals_moved/renamed/archived/deleted=false`
- Package writer schreibt nur unter kontrolliertem Sandbox-/Preview-Output (`finalization-dry-run-` Prefix).
- Pflicht-Artefakte: README, Manifest JSON/CSV, Audit, Plan, Conflicts, Ready/Blocked (+ optional Ignored/Deferred/Still-Review).
- UI: „Finalisierungs-Trockenlauf erstellen“, „Audit-Paket erzeugen“, „Nur prüfen — nichts final schreiben“.
- Preview Export enthält Dry-Run-Package-Metadaten.
- Keine produktive Verarbeitung; keine realen Rechnungsordner; keine finalen PDFs; keine Original-Mutation.
- Track A/Core unverändert; Release-Tags unverändert.
- Product status vorher: `TRACK_B_FINALIZATION_DRY_RUN_PACKAGE_AND_AUDIT_READY`
- HEAD Baseline: `30e02842a024b60656179952b98c878c6210ea88` (Feature Prompt 31: `ae697de5afe90614debf0850a1ab23cbeabafa0a`)

---

## Current product capability

Bis Prompt 31 kann Track B:

- Review decisions speichern und Readiness berechnen
- `FinalizationPreviewBatch` mit Conflicts/Counts erzeugen
- `FinalizationDryRunPackage` als prüfbares Audit-/Plan-Paket schreiben
- Preview Export inkl. Batch- und Dry-Run-Metadaten
- Safety-Flags hart auf `final_write_allowed=false` halten

Noch **nicht** vorhanden (Lücke dieses Designs → spätere Implementierung):

- `FinalWriteGate` Runtime-Modell
- `FinalWriteAuthorization` Runtime-Modell
- `FinalWritePlan` Runtime-Modell
- aktive Final-Write-Ausführung (Copy/Rename in Final-Output)
- produktiver Write-Pfad

---

## Diagnosis

1. **Was Prompt 31 implementiert hat:** nicht-produktives Dry-Run-/Audit-Paket aus einer `FinalizationPreviewBatch` unter Sandbox-Output; UI-CTAs; Preview-Export-Metadaten; harte Ablehnung von `final_write_allowed=true` und produktivem Modus.
2. **Final-write-adjacent metadata bereits vorhanden:** `source_sha256`, `preview_sha256`, `target_preview_path`, `approved_preview_filename`, `ready_for_future_finalization`, `final_write_allowed=false`, Dry-Run `package_id` / `batch_id` / `preview_state_id`, Conflict-/Blocker-Listen, Safety-Flags.
3. **Bereits vertretene Gates (Konzept/Runtime-adjacent):** Dry-Run-only Writer; Output-Root Sandbox-Policy; stale preview block im Dry-Run; Path-Policy gegen reale Rechnungsordner; `final_write_allowed` immer false; keine Original-Mutation.
4. **Noch nicht vertretene Gates:** explizite `FinalWriteAuthorization` mit Confirmation Phrase; Preflight-Recheck unmittelbar vor Write; Pre-/Post-Write-Audit-Records der Final-Write-Pipeline; Rollback/Abort-Semantik; aktivierbare Execution mit `final_write_execution_available`.
5. **Autorisierung künftiger Final-Write-Requests:** nur über `FinalWriteAuthorization` nach Dry-Run-Package-Link, Scope-Klarheit, Acknowledgements und optionaler Confirmation Phrase — nie durch bloße Review-Accept-Aktion.
6. **Unterschied zu Review-Accept:** `accept_suggestion` / `edit_suggestion` setzen höchstens `finalization_ready` / `ready_for_future_finalization`. Sie erzeugen **keine** Write-Autorisierung und dürfen **nicht** `final_write_allowed=true` setzen.
7. **Source-Hash-Recheck:** unmittelbar vor Write `source_sha256_at_write_check` neu berechnen und mit `source_sha256_at_preview` (bzw. Dry-Run-/Decision-Hash) vergleichen; Mismatch → Blocker `source_hash_changed`.
8. **Target-Path-Recheck:** `final_target_path` muss unter erlaubtem `output_root` liegen (`target_within_output_root=true`); sonst Blocker `target_outside_output_root`.
9. **Duplicate/Conflict-Recheck:** Batch- und Disk-Konflikte erneut prüfen; unresolved Duplicate/Target-exists ohne Policy → Blocker.
10. **Stale Preview blockieren:** wenn `preview_state_id` oder Dry-Run-Package nicht mehr zum aktuellen Preview-State passt → Blocker `stale_preview_state` / stale dry-run package.
11. **Dry-Run-Package-Link:** jedes zukünftige Final Write muss `dry_run_package_id` referenzieren und dasselbe `preview_state_id` / `batch_id` tragen.
12. **Warum kein Final Write in diesem Task:** Sequenz verlangt zuerst das Gate-Design; Execution bleibt späterem autorisiertem Task vorbehalten; hier bleibt `final_write_execution_available=false` und `final_write_allowed=false`.

---

## FinalWriteGate model

Datenmodell **`FinalWriteGate`**:

| Field | Meaning |
|---|---|
| `gate_id` | stabile Gate-ID |
| `source_run_id` | zugehöriger Processing-/Preview-Run |
| `preview_state_id` | Preview-State, gegen den das Gate geprüft wird |
| `dry_run_package_id` | verknüpftes FinalizationDryRunPackage |
| `batch_id` | verknüpfte FinalizationPreviewBatch |
| `created_at` | Erstellungszeitpunkt |
| `final_write_allowed` | nur `true` in späterer Execution-Task **nach** allen Checks; in dieser Phase immer `false` |
| `productive_mode_requested` | muss explizit und separat freigegeben sein; Default `false` |
| `gate_status` | siehe unten |
| `required_preconditions` | Liste der Pflichtvoraussetzungen |
| `blockers` | aktive harte Blocker |
| `warnings` | nicht-blockierende Hinweise |
| `user_authorization_required` | `true` — ohne `FinalWriteAuthorization` kein Write |
| `audit_required` | `true` — Pre-Write-Audit Pflicht |
| `source_recheck_required` | `true` |
| `target_recheck_required` | `true` |
| `conflict_recheck_required` | `true` |
| `stale_state_recheck_required` | `true` |
| `final_write_execution_available` | **`false` in this phase** |

Erlaubte `gate_status`-Werte:

- `closed` — Gate geschlossen; keine Write-Vorbereitung aktiv
- `open_for_future_authorized_write` — Design/Preflight erlaubt zukünftige autorisierte Execution (noch keine Execution)
- `blocked` — mindestens ein Hard Blocker aktiv

In Prompt 32 bleibt Runtime-Execution aus: selbst bei vollständig spezifizierten Preconditions ist `final_write_execution_available=false` und `final_write_allowed=false` (Blocker in this phase).

---

## FinalWriteAuthorization model

Datenmodell **`FinalWriteAuthorization`**:

| Field | Meaning |
|---|---|
| `authorization_id` | stabile Autorisierungs-ID |
| `authorized_by_user` | explizite Nutzeridentität / Session-Marker (kein Auto) |
| `authorization_timestamp` | Zeitpunkt der Bestätigung |
| `authorization_scope` | `selected_items` **oder** `whole_ready_batch` |
| `selected_item_ids` | IDs im Scope |
| `user_acknowledged` | Map der Pflicht-Acknowledgements (siehe unten) |
| `dry_run_package_id` | muss zum Gate passen |
| `finalization_preview_batch_id` | muss zum Gate passen |
| `confirmation_phrase_required` | ob Phrase Pflicht ist |
| `confirmation_phrase_entered` | eingegebene Phrase |
| `authorization_valid` | alle Acknowledgements + Scope + Phrase + keine Authorization-Blocker |
| `authorization_blockers` | Gründe, warum Autorisierung ungültig ist |

`user_acknowledged` muss mindestens enthalten:

- `final_write_will_copy_or_rename` — Nutzer versteht: dies ist kein Trockenlauf mehr; Dateien werden ins Final-Output kopiert/umbenannt (Copy/Rename-Copy)
- `originals_policy` — Nutzer bestätigt die Original-Policy (Default-Design: `leave_original_unchanged`; Archive nur als späterer separater Schritt)
- `conflicts_resolved` — Konflikte sind gelöst oder bewusst per Policy behandelt
- `source_hash_recheck` — Source-Hash-Recheck akzeptiert
- `target_path_recheck` — Target-Path-Recheck akzeptiert
- `no_rollback_guarantee_without_backup` — kein Rollback-Garantie ohne Backup

**Confirmation phrase option:** wenn `confirmation_phrase_required=true`, muss die eingegebene Phrase exakt der geforderten Phrase entsprechen (z. B. produkt-/kontextspezifisch konfigurierbar). Fehlt sie → Blocker.

Unterschied zu Review-Accept: Review-Accept autorisiert **keine** Dateischreibung. Nur `FinalWriteAuthorization` mit gültigem Scope und Acknowledgements darf eine spätere Execution freigeben.

---

## FinalWritePlan model

Datenmodell **`FinalWritePlan`** — ein Record **per item**:

| Field | Meaning |
|---|---|
| `item_id` | Review-/Dokument-ID |
| `source_path` | Quellpfad |
| `source_sha256_at_preview` | Hash zum Preview-/Dry-Run-Zeitpunkt |
| `source_sha256_at_write_check` | Hash beim Write-Preflight |
| `source_hash_match` | Vergleichsergebnis |
| `approved_final_filename` | freigegebener finaler Dateiname |
| `final_target_path` | geplantes Final-Ziel |
| `target_within_output_root` | Ziel liegt unter erlaubtem Output-Root |
| `target_exists` | Ziel existiert bereits |
| `duplicate_policy` | z. B. `block` / `explicit_overwrite_forbidden_by_default` / später explizit freigegebene Policy |
| `conflict_status` | `ok` / `duplicate` / `unresolved` / … |
| `operation_type` | siehe unten |
| `original_file_policy` | siehe unten |
| `ready_for_write` | Item besteht alle Item-Gates |
| `write_blockers` | Item-Blocker |
| `audit_record_id` | Verweis auf Pre-Write-Audit-Zeile |

Erlaubte `operation_type`-Werte:

- `copy_to_final_output`
- `rename_copy_to_final_output`
- `no_op`

Erlaubte `original_file_policy`-Werte (Konzept):

- `leave_original_unchanged` — Default und Pflicht-Default in frühen Phasen
- `archive_after_success_later` — nur als späterer, separat autorisierter Schritt; **nicht** in Prompt 32

Duplicate/Conflict policy (Konzept): unresolved Duplicate oder `target_exists` ohne explizite Policy → immer blockieren. Kein stilles Überschreiben.

Output-folder safety policy (Konzept): Final-Output nur unter kontrolliertem, explizit erlaubtem `output_root` (Sandbox-/Test-Policy bzw. später explizit freigegebener Controlled Output). Reale Rechnungsordner-Pfade sind Hard Blocker. Path-Traversal und Ziele außerhalb `output_root` sind Hard Blocker.

Rollback/Abort (Konzept):

- Preflight-Fehler → Abort vor erstem Write; keine Teilwrites ohne Audit
- Fehler mitten in späterer Execution → Abort weiterer Items; bereits geschriebene Items in Post-Write-Audit; **kein** automatisches Löschen von Originalen; Rollback nur soweit zuvor definiertes Backup/Kompensation existiert (`no_rollback_guarantee_without_backup`)

---

## Mandatory preconditions

Zukünftiges Final Write darf **nur** erlaubt werden, wenn **alle** wahr sind:

1. Finalization dry-run package exists (mandatory dry-run package precondition).
2. Dry-run package is linked to current preview state (`dry_run_package_id` + matching `preview_state_id`).
3. Selected items are `ready_for_future_finalization`.
4. User authorization exists (`FinalWriteAuthorization` with `authorization_valid=true`) — user authorization precondition.
5. Authorization scope is clear (`selected_items` oder `whole_ready_batch`).
6. Confirmation phrase is satisfied if required.
7. Source hash is rechecked and unchanged (`source_hash_match=true`).
8. Preview state is fresh (not stale).
9. Target paths are inside allowed output root (`target_within_output_root=true`) — target path recheck.
10. Duplicate/conflict policy is resolved — conflict recheck.
11. No unresolved blockers.
12. Output root is controlled.
13. Final audit pre-record exists (pre-write audit).
14. Final write mode is explicitly enabled.
15. `final_write_allowed` is true **only** inside the later final-write execution task after all checks (nicht in Prompt 32).
16. Track A/internal app path remains separate.

In Prompt 32: selbst Preconditions spezifiziert, aber Execution bleibt aus; `final_write_allowed=false` bleibt Blocker in this phase.

---

## Hard blockers

Blockers that always prevent final write:

| Blocker | Meaning |
|---|---|
| `missing_dry_run_package` | missing dry-run package |
| `stale_dry_run_package` | stale dry-run package |
| `stale_preview_state` | stale preview state / stale preview blocker |
| `source_hash_changed` | source hash changed |
| `target_outside_output_root` | target outside output root |
| `duplicate_target_unresolved` | duplicate target unresolved / duplicate target blocker |
| `target_exists_without_explicit_policy` | target exists without explicit policy |
| `unresolved_review_item` | unresolved review item |
| `missing_required_field` | missing required field |
| `incomplete_filename` | incomplete filename |
| `unresolved_configuration` | unresolved configuration |
| `missing_final_write_authorization` | missing final-write authorization / missing explicit final-write authorization |
| `confirmation_phrase_missing` | confirmation phrase missing when required |
| `productive_mode_not_explicitly_enabled` | productive mode not explicitly enabled |
| `final_audit_pre_record_missing` | final audit pre-record missing |
| `real_invoice_folder_path_detected` | real invoice folder path detected / real invoice folder path blocker |
| `final_write_allowed_false` | `final_write_allowed=false` as blocker in this phase |

Zusätzlich: `final_write_execution_available=false` verhindert jede Execution in Prompt 32.

Kein Bypass von Duplicate-/Conflict-, Stale- oder Source-Hash-Checks.

---

## User-facing confirmation design

UI confirmation design (Track-B / UI-v2, **design-only** in this task):

Erforderliche UI-Inhalte:

- „Finales Schreiben vorbereiten“
- „Dies ist kein Trockenlauf mehr“
- Liste der selected ready items
- source path
- final target path
- operation type
- originals policy
- conflicts summary
- source-hash recheck result
- checkbox acknowledgements (alle `user_acknowledged`-Felder)
- optional confirmation phrase (confirmation phrase option)
- final warning
- expliziter Button: **„Finales Schreiben ausführen“**
- disabled state if any blocker exists

In diesem Task ist der Button **design-only / not implemented as active final writer**.  
Kein aktiver Final-Write-Handler; keine produktive Aktion hinter dem Button.

---

## Audit design

### Pre-write audit fields

Pflicht vor jedem zukünftigen Write:

- `final_write_gate_id`
- `dry_run_package_id`
- `batch_id`
- `selected_item_ids`
- `authorization_id`
- `preflight_timestamp`
- `source_hash_recheck_result`
- `target_recheck_result`
- `conflict_recheck_result`
- `blockers`
- `final_write_allowed_at_preflight`
- `execution_available=false` in this phase

### Post-write audit fields (for later task)

Für die spätere Execution-Task:

- `execution_started_at`
- `execution_finished_at`
- `file_results`
- `final_files_written`
- `originals_moved`
- `originals_renamed`
- `originals_archived`
- `originals_deleted`
- `failures`
- `rollback_or_abort_notes`

In Prompt 32 werden Post-Write-Felder nur spezifiziert; keine Post-Write-Records aus echter Execution.

---

## Difference from Preview Export / Batch / Dry Run

| Aspect | Preview Export | Finalization Preview Batch | Finalization Dry-Run Package | Controlled Final Write (später) |
|---|---|---|---|---|
| Zweck | Review-/Export-Nachweis inkl. Preview-PDFs | Gruppierung, Counts, Conflicts | Audit-/Plan-Paket prüfen | finale Dateien unter Gates schreiben |
| Schreibt Dateien | Preview-Kopien under preview export root | nein (state only) | Markdown/JSON/CSV only | ja, nur nach allen Gates |
| `dry_run_package` | optional referenziert | n/a | `true` | n/a / linked |
| `final_write_allowed` | `false` | `false` | `false` | nur nach Preflight in Execution-Task |
| Originale | unverändert | unverändert | unverändert | Default: unverändert; Archive nur später separat |
| Autorisierung | nicht nötig für Export | nicht nötig | nicht nötig | `FinalWriteAuthorization` Pflicht |
| UI-CTA | Preview export | Finalisierungs-Vorschau | Trockenlauf / Audit-Paket | „Finales Schreiben ausführen“ (später) |

---

## Future implementation rules

Für `KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_SANDBOX_IMPLEMENTATION_01` und spätere Tasks:

1. Gate-/Authorization-/Plan-Modelle zuerst als Runtime umsetzen — Execution dahinter.
2. Niemals `final_write_allowed=true` setzen, bevor alle Mandatory Preconditions und Hard-Blocker-Checks bestanden sind.
3. Immediate recheck vor Write: source hash, preview freshness, target path, conflicts/duplicates.
4. Dry-Run-Package muss verlinkt und frisch sein.
5. UI-Button erst aktivieren, wenn Preflight sauber und Autorisierung gültig.
6. Track A / `run_once` / Processing-Core unberührt lassen.
7. Keine realen Rechnungsordner; kontrollierter Output-Root.
8. Default Original-Policy: `leave_original_unchanged`.
9. Jeder Write braucht Pre- und Post-Write-Audit.
10. Kein Auto-Finalize nach Review-Accept oder Configuration Match.

---

## Out-of-scope list

In diesem Task **nicht** implementieren:

- final write execution
- final copy/rename
- original archive
- original deletion
- productive `run_once`
- deployment
- SaaS-ready claim
- production-ready claim
- reale Rechnungsordner verarbeiten
- Release-Tags ändern
- `final_write_allowed=true` in runtime behavior
- produktive Output-Ordner erzeugen
- aktive Final-Write-Button-Execution

---

## What is now proven

- `FinalWriteGate` model is defined.
- `FinalWriteAuthorization` model is defined.
- `FinalWritePlan` model is defined.
- Mandatory preconditions inkl. dry-run package + user authorization + rechecks are defined.
- Hard blockers inkl. stale preview, source hash changed, target outside output root, duplicate target, missing authorization, real invoice folder path, `final_write_allowed=false` in this phase are defined.
- UI confirmation design inkl. confirmation phrase option is defined.
- Pre-write and post-write audit fields are defined.
- `final_write_execution_available=false` in this phase; no final files written; no productive processing; no real invoice folders.
- Nicht SaaS-ready; nicht production-ready.

---

## What is still not proven

- Runtime-Implementierung von Gate/Authorization/Plan
- Sandbox Final-Write Execution unter den Gates
- End-to-End manueller GUI-Durchlauf mit echter Dateischreibung
- produktive Freigabe außerhalb Sandbox (bewusst out of scope)

---

## Test result

Focused docs/safety tests + Prompt-31-nahe Track-B-Tests + Track-A-Schutz + UI-v2/SaaS-Suite; siehe Audit.

---

## No productive processing

Ja — reines Design/Spec; keine Runtime-Finalisierung, kein `run_once`, keine Input-Mutation, no final files written.

## No real invoice folders

Ja — Design bezieht sich auf Controlled-/Sandbox-Kontext; keine realen Rechnungsordner.

## Not SaaS-ready

Explizit nicht SaaS-ready.

## Not production-ready

Explizit nicht production-ready.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_SANDBOX_IMPLEMENTATION_01`
