# Track-B Review Decision State and UI Flow

**Task ID:** `KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_STATE_AND_UI_FLOW_01`  
**Masterplan:** Prompt 29/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_REVIEW_DECISION_STATE_AND_UI_FLOW_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.  
In dieser Phase gilt: **`final_write_allowed=false`**.

---

## Purpose

Implementiert den Track-B Review-Entscheidungsstate und UI-Flow gemäß Prompt-28-Design.

Nutzer können je Preview-Item explizit entscheiden, was als Nächstes passieren soll — ohne produktives finales Schreiben.

Korrekte Sequenz bleibt:

1. Review item  
2. Nutzer wählt Entscheidung  
3. State speichert Entscheidung  
4. Item kann `finalization-ready` / `decision_ready_for_future_finalization` werden  
5. Manifest/Review-Report enthält Decision-/Readiness-Felder  
6. Finales Schreiben bleibt blockiert bis zu einem späteren, explizit freigegebenen Task

---

## Baseline from Prompt 28

- ReviewDecision- und FinalizationReadiness-Modelle spezifiziert  
- Decision behaviors und Finalization blockers spezifiziert  
- UI-/Manifest-/Safety-Anforderungen spezifiziert  
- Product status vorher: `TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_READY`  
- HEAD Baseline: `24055954124b9d859d30c041cf562a15bd683a36`

---

## ReviewDecision implementation

Modul: `invoice_tool/ui_v2/review_decision.py`

`ReviewDecision` Felder:

- `decision_id`, `source_item_id`, `source_filename`
- `decision_type`: `accept_suggestion` | `edit_suggestion` | `keep_review_required` | `ignore_for_export` | `defer` | `needs_configuration_change`
- `decided_by_user`, `decision_timestamp`
- `approved_preview_filename`, `approved_target_preview_path`
- `edited_fields`, `reason`, `warnings_acknowledged`
- `finalization_ready`, `finalization_blockers`, `audit_note`
- `source_hash_at_decision`, `preview_state_id`
- `decision_ready_for_future_finalization`
- `final_write_allowed` (immer `false`)
- `exclude_from_finalization_batch`, `review_status`, `routes_to_configuration_flow`

In-Memory-Bag auf `UiV2State.review_decision_ui`.

---

## FinalizationReadiness implementation

Modul: `invoice_tool/ui_v2/finalization_readiness.py`

`FinalizationReadiness` Felder:

- `item_id`, `ready`, `approved`
- `required_fields_present`, `configuration_resolved`, `filename_complete`
- `output_root_safe`, `target_conflict_status`
- `source_unchanged_since_preview`, `preview_state_fresh`
- `blockers`, `warnings`, `next_action`
- `decision_ready_for_future_finalization`
- `final_write_allowed` (immer `false`)

### Gewähltes Readiness-Modell

- `ready` / `decision_ready_for_future_finalization` darf `true` werden, wenn Entscheidungs-Gates bestehen (Felder, Approval, Konflikte, Freshness, Source-Hash).
- `final_write_allowed` bleibt in dieser Phase **immer** `false`.
- `finalization_disabled_in_current_mode` wird als Warnung/Phase-Hinweis geführt, nicht als permanenter Hard-Blocker, der Readiness dauerhaft unsichtbar macht.
- `finalization_ready=true` bedeutet **nicht** finales Schreiben.

---

## Decision transition behavior

Reine/state-sichere Funktionen:

- `create_accept_suggestion_decision` — erfordert `decided_by_user=true` + explizite Bestätigung (zweistufig in der UI)
- `create_edit_suggestion_decision` — validiert Dateiname, speichert `edited_fields`
- `create_keep_review_required_decision` — bleibt in Review / Unklar
- `create_ignore_for_export_decision` — schließt aus Finalisierungs-/Export-Vorschau aus
- `create_defer_decision` — Status `pending`
- `create_needs_configuration_change_decision` — routet zurück zum Konfigurationsregel-Flow
- `apply_review_decision_to_item` — schreibt nur Track-B/UI-v2 State

Keine Funktion ruft `run_once` auf, schreibt Dateien, mutiert Inputs oder setzt `final_write_allowed=true`.

---

## UI flow

Review-Seite (`invoice_tool/ui_v2/pages/review.py`) zeigt:

- Vorschlag akzeptieren  
- Vorschlag bearbeiten  
- Konfiguration anpassen und neu prüfen  
- als Unklar belassen  
- ignorieren / nicht exportieren  
- zurückstellen  

Nach Entscheidung:

- decision type  
- approved filename (falls vorhanden)  
- blockers / warnings  
- finalization-ready Indicator  
- Safety-Text: **„Noch keine finale Verarbeitung — Originale bleiben unverändert.“**  
- editierbares Vorschau-Dateiname-Feld  
- `final_write_allowed: false`

Accept ist zweistufig: erster Klick arm't Bestätigung, zweiter Klick speichert die Entscheidung.

---

## Edited filename validation

`validate_edited_filename` lehnt ab:

- leerer Dateiname  
- Pfadtrenner (`/` `\`)  
- Traversal (`..`)  
- fehlende `.pdf`-Endung  
- fehlende Platzhalter (wenn Pattern noch abhängig)  
- Duplikat-Ziel  
- unsicherer Zielpfad außerhalb Output-Root  

---

## Duplicate/conflict detection

`detect_duplicate_approved_targets` auf Preview-State-Ebene:

- erkennt doppelte freigegebene Target-Preview-Pfade/Namen  
- markiert betroffene Items mit `duplicate_target_filename`  
- kein Auto-Overwrite, kein stilles Suffix-Anhängen  

---

## Manifest/review-items fields

Preview Export (`preview_export.py`) enthält je Item wo anwendbar:

- `review_decision`  
- `decision_timestamp`  
- `approved_by_user`  
- `finalization_ready` / `decision_ready_for_future_finalization`  
- `finalization_blockers`  
- `approved_preview_filename`  
- `target_preview_path`  
- `user_edited_fields`  
- `warnings_acknowledged`  
- `source_hash_at_decision`  
- `preview_state_id`  
- `final_write_allowed=false`  

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

- ReviewDecision-State-Modell im Code  
- FinalizationReadiness-Berechnung im Code  
- sechs Decision-Transitions ohne Final Write  
- UI-Entscheidungsaktionen + Safety-Text  
- Edited-Filename-Validierung  
- Duplicate-Target-Erkennung  
- Manifest-/Report-Felder inkl. `final_write_allowed=false`  
- Focused Tests + Track-A-Schutz  

---

## What is still not proven

- Finalization Preview Batch & Conflicts (nächster Prompt)  
- tatsächliche Final-Write-Pipeline unter Safety Gates  
- manueller Full-GUI-Durchlauf mit produktiver Freigabe (bewusst out of scope)

---

## Test result

Siehe Audit — Focused + UI-v2/SaaS Suite + `git diff --check`.

---

## No productive processing

Ja — Decision/State/UI/Manifest only.

## No real invoice folders

Ja — Controlled-/Sandbox-Kontext; keine realen Rechnungsordner.

## Not SaaS-ready

Explizit nicht SaaS-ready.

## Not production-ready

Explizit nicht production-ready.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_FINALIZATION_PREVIEW_BATCH_AND_CONFLICTS_01`
