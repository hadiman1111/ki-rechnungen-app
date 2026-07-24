# Track-B Review Decision to Finalization Design

**Task ID:** `KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_01`  
**Masterplan:** Prompt 28/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.  
In dieser Phase gilt: **`final_write_allowed=false`**.  
No runtime/code changes are expected — design/specification only.

---

## Purpose

Dieses Design spezifiziert den sicheren Track-B-Pfad von der Review-Entscheidung bis zur Finalisierungsbereitschaft — ohne produktives finales Schreiben.

Korrekte Sequenz:

1. Review item  
2. Nutzer prüft Vorschau-Dateiname, Betrag, Lieferant, Konfiguration, Ziel  
3. Nutzer akzeptiert oder bearbeitet  
4. Item wird `finalization-ready` (oder bleibt geblockt)  
5. Finalization-Preview/Audit wird erzeugt  
6. Erst ein späterer, explizit freigegebener Finalization-Task darf finale Dateien schreiben

Eine Review-Entscheidung ist **noch keine** produktive Finalisierung.

---

## Baseline from Prompt 27

- Track-B configuration rule apply/rerun preview flow ready.
- Gespeicherte Regeln gelten nur nach expliziter Nutzerbestätigung + explizitem Preview-Rerun.
- PayPal-Fälle können in Preview von Unklar → PayPal wechseln.
- Generische Karte wird nicht zu AMEX.
- Missing `payment_field` bleibt Unklar.
- Preview Export nach Rerun nutzt aktualisierten Matching-Zustand.
- Manifest/review-items enthalten `rule_applied`, `applied_configuration_*`, `rerun_preview_after_rule_change`, previous/new matched configuration.
- Keine produktive Verarbeitung; keine realen Rechnungsordner; Release-Tags unverändert.
- Product status vorher: `TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_READY`
- HEAD Baseline: `94e265637d0956a5393de0681794e81ef3c63559`

---

## Current product capability

Bis Prompt 27 kann Track B:

- Sandbox-/Dry-Run-Review-Items aus `ProcessingRunState` anzeigen
- Vorschau-Dateinamen, Felder, Matching, Coverage-Guidance und Apply/Rerun-Preview zeigen
- Preview Export (Manifest, review-items, kopierte Preview-PDFs unter erlaubtem Output-Root) erzeugen
- Freshness-Guards gegen stale Export-State erzwingen
- Konfigurationsregeln speichern und Preview-Matching neu bewerten

Noch **nicht** vorhanden (Lücke dieses Designs):

- verbindliches ReviewDecision-Modell
- FinalizationReadiness-Modell
- explizite Entscheidungen: akzeptieren / bearbeiten / Unklar belassen / ignorieren / zurückstellen / Konfiguration anpassen
- Freigabe → finalization-ready ohne finales Schreiben
- finale Schreibpipeline

Aktuelle Review-Aktionen in `review_workflow.build_review_actions` sind bewusst disabled / readiness-only (`Als geprüft markieren`, `Entscheidung später speichern`, `Nachweis prüfen`) und mutieren keine Dateien.

---

## Diagnosis

1. **Was Track B bis Prompt 27 kann:** Preview/Review/Matching/Apply-Rerun/Preview-Export inkl. Freshness — sandbox only.  
2. **Fehlende Review-Entscheidungen:** `accept_suggestion`, `edit_suggestion`, `keep_review_required`, `ignore_for_export`, `defer`, `needs_configuration_change`.  
3. **Aktuelle Item-Zustände:** review / planned-preview / error-getrennt; `REVIEW_REQUIRED*` Namenspräfixe; keine finalization-ready-Stufe.  
4. **Pflichtfelder vor Finalization Readiness:** supplier, date, amount, payment_field (wenn Regel es verlangt), complete filename pattern / placeholders, matched oder intentional akzeptierte Konfiguration, sichtbarer Vorschau-Dateiname, sicheres Ziel.  
5. **Blocker:** siehe Abschnitt Finalization blockers.  
6. **Approval-Darstellung:** `decided_by_user=true` + Timestamp + approved preview/target + `finalization_ready` erst nach Gates.  
7. **Edit-Konzept:** sichere Felder editierbar; validierter Dateiname; `edited_fields` auditiert.  
8. **Duplicate/Conflict-Konzept:** Zielname im Batch und auf Disk unter Output-Root prüfen; Policy muss explizit sein.  
9. **Stale/Source-Hash-Konzept:** `source_hash_at_decision` und `preview_state_id` müssen bis Final Write unverändert bleiben.  
10. **Out of scope bis Final-Write-Implementierung:** jedes produktive Rename/Move/Archive/Delete/Overwrite.

---

## ReviewDecision model

Datenmodell **`ReviewDecision`**:

| Field | Meaning |
|---|---|
| `decision_id` | stabile ID der Entscheidung |
| `source_item_id` | Review-/Dokument-ID |
| `source_filename` | Originaldateiname (unverändert) |
| `decision_type` | siehe unten |
| `decided_by_user` | `true` nur bei expliziter Nutzeraktion |
| `decision_timestamp` | Zeitpunkt der Entscheidung |
| `approved_preview_filename` | vom Nutzer freigegebener Vorschau-Dateiname |
| `approved_target_preview_path` | geplantes Ziel (Preview-Pfad) |
| `edited_fields` | Map/Liste geänderter Felder bei `edit_suggestion` |
| `reason` | optionale Begründung |
| `warnings_acknowledged` | vom Nutzer bestätigte Warnungen |
| `finalization_ready` | `true/false` nach Readiness-Gates |
| `finalization_blockers` | Liste aktiver Blocker-Codes |
| `audit_note` | freie Audit-Notiz |

Erlaubte `decision_type`-Werte:

- `accept_suggestion` — Vorschlag akzeptieren  
- `edit_suggestion` — Vorschlag bearbeiten  
- `keep_review_required` — als Unklar belassen  
- `ignore_for_export` — ignorieren / nicht exportieren  
- `defer` — zurückstellen  
- `needs_configuration_change` — Konfiguration anpassen und neu prüfen  

UI-Labels (Design):

- Vorschlag akzeptieren  
- Vorschlag bearbeiten  
- Konfiguration anpassen und neu prüfen  
- als Unklar belassen  
- ignorieren / nicht exportieren  
- zurückstellen  

Regel: stillschweigendes Auto-Approve ist verboten. `REVIEW_REQUIRED` darf ohne explizite Approval nicht entfernt werden.

---

## FinalizationReadiness model

Datenmodell **`FinalizationReadiness`**:

| Field | Meaning |
|---|---|
| `item_id` | Bezug zum Review-Item |
| `ready` | alle Gates bestanden |
| `approved` | explizite Nutzerfreigabe vorhanden |
| `required_fields_present` | Pflichtfelder vorhanden |
| `configuration_resolved` | Match oder intentional akzeptiert |
| `filename_complete` | Pattern vollständig / keine fehlenden Placeholder |
| `output_root_safe` | Ziel unter erlaubtem Output-Root |
| `target_conflict_status` | `ok` / `duplicate` / `conflict` / `unresolved` |
| `source_unchanged_since_preview` | Source-Hash unverändert |
| `preview_state_fresh` | Preview-State nicht stale |
| `blockers` | aktive Blocker |
| `warnings` | nicht-blockierende Hinweise |
| `next_action` | empfohlener nächster Schritt |

Ein Item wird nur dann finalization-ready, wenn:

- required fields present  
- configuration matched oder intentional accepted  
- filename pattern complete  
- preview filename visible  
- user explicitly approves  
- source file unchanged since preview  
- target path within allowed output root  
- duplicate/conflict handling defined and resolved  
- no remaining blockers  

`finalization_ready=true` bedeutet **nicht** finales Schreiben. In dieser Phase bleibt `final_write_allowed=false`.

---

## Decision behaviors

### `accept_suggestion`

- Nur erlaubt, wenn required fields present und Nutzer explizit bestätigt.  
- Darf trotzdem `finalization_ready=false` bleiben, wenn Conflict/Blocker existieren.  
- Kein produktives Schreiben; Originale unverändert.

### `edit_suggestion`

- Nutzer darf sichere Felder editieren (z. B. Betrag, Lieferant, Zahlungsfeld, Dateiname-Teile im erlaubten Pattern).  
- Edited filename must be validated (Zeichen, Pattern, keine Path-Traversal).  
- Edited values must be recorded in `edited_fields` / Manifest.  
- Danach erneut Readiness prüfen.

### `keep_review_required`

- Item bleibt Review / Unklar.  
- Keine Finalization.  
- `REVIEW_REQUIRED` bleibt erhalten.

### `ignore_for_export`

- Item excluded from finalization batch.  
- No file operation.  
- Audit speichert Ausschlussgrund.

### `defer`

- Item remains pending.  
- Keine Finalization; Entscheidung später möglich.

### `needs_configuration_change`

- Routes back to configuration rule flow (Prompt 26/27).  
- Nach Speichern + explizitem Preview-Rerun erneut entscheiden.  
- Kein Auto-Finalize nach Configuration Match.

---

## Required fields

Vor Finalization Readiness müssen sichtbar und belegt sein (soweit Regel/Pattern sie verlangt):

- supplier / counterparty  
- date (`invoice_date`)  
- amount  
- `payment_field` where required  
- document art / direction laut Pattern  
- matched configuration name/pattern **oder** intentional accepted unresolved-with-ack (nur wenn Policy es erlaubt; Default: unresolved blockiert)  
- complete filename pattern inkl. Placeholder-Werte  
- sichtbarer Vorschau-Dateiname  
- target preview path  

---

## Finalization blockers

Muss blockieren (`finalization_ready=false`):

| Blocker code | Meaning |
|---|---|
| `missing_payment_field` | missing payment_field where required |
| `missing_supplier` | missing supplier |
| `missing_date` | missing date |
| `missing_amount` | missing amount |
| `missing_or_unclear_configuration` | missing/unclear configuration / unresolved configuration |
| `missing_filename_pattern` | missing filename pattern |
| `missing_placeholder` | incomplete filename pattern / missing placeholder |
| `duplicate_target_filename` | duplicate target filename |
| `target_outside_output_root` | target outside output root / output root unsafe / unsafe target path |
| `stale_preview_state` | stale state |
| `source_hash_changed` | source hash changed |
| `no_explicit_user_approval` | no explicit approval / no explicit user approval |
| `finalization_disabled_in_current_mode` | finalization disabled in current mode |

Zusätzlich konzeptionell:

- source file changed since preview  
- preview state stale  
- finalization mode not explicitly enabled  

Kein Bypass von Duplicate-/Conflict- oder Stale-Checks.

---

## UI design

Erforderliche UI-Elemente (Track-B / UI-v2 Review, Design only):

- decision buttons für alle sechs Entscheidungstypen  
- visible Vorschau-Dateiname  
- editable proposed filename field (bei `edit_suggestion`)  
- target preview path  
- warnings/blockers panel  
- approval checkbox **oder** explicit confirm button (explizite Freigabe)  
- „finalization-ready“ indicator  
- „not final yet“ / „noch keine finale Dateischreibung“ safety text  
- audit note field if needed  
- Anzeige von amount, supplier, configuration, source filename  

Safety copy (Pflicht):

- Review-Entscheidung ≠ produktive Finalisierung  
- Originale bleiben unverändert  
- `final_write_allowed=false` in dieser Phase  

Track-A-UI bleibt unverändert.

---

## Manifest/audit design

Für künftige Manifest-/review-items-Felder:

- `review_decision`  
- `decision_timestamp`  
- `approved_by_user`  
- `finalization_ready`  
- `finalization_blockers`  
- `approved_preview_filename`  
- `target_preview_path`  
- `user_edited_fields`  
- `warnings_acknowledged`  
- `source_hash_at_decision`  
- `preview_state_id`  
- `final_write_allowed=false` in this phase  

Audit evidence muss speichern:

- wer/wann entschieden hat (`decided_by_user`, Timestamp)  
- welche Felder gesehen/akzeptiert/editiert wurden  
- welche Blocker/Warnungen galten  
- Source-Hash und Preview-State-ID zum Entscheidungszeitpunkt  
- dass kein Final Write erfolgt ist  

Finalization preview vs final write:

| Aspect | Finalization preview (erlaubt später nach Decision-UI) | Final write (späterer Task) |
|---|---|---|
| Dateien schreiben | nein (außer bestehendem Preview-Export) | ja, nur nach allen Gates |
| Originale | unverändert | nur nach separater produktiver Freigabe |
| Manifest | Decision-/Readiness-Felder, `final_write_allowed=false` | Write-Audit + Ergebnispfade |
| Zweck | Nachweis der Freigabe-Absicht | tatsächliche Zielablage |

---

## Future final write safety gates

Bevor irgendeine spätere Final-Write-Implementierung Dateien schreiben darf, müssen alle Gates bestehen:

1. explicit approval exists  
2. `finalization_ready=true`  
3. no blockers  
4. source hash unchanged  
5. target path safe (within allowed output root)  
6. duplicate policy resolved  
7. preview state fresh  
8. finalization mode explicitly enabled  
9. productive write path still separately gated  
10. audit record written  

Zusätzlich: kein Auto-Finalize nach Configuration Match; kein Entfernen von `REVIEW_REQUIRED` ohne explicit approval.

---

## Out-of-scope list

In diesem Task / bis zur späteren Final-Write-Freigabe **nicht** implementieren:

- final write  
- moving files  
- renaming originals  
- archiving originals  
- deleting originals  
- productive `run_once`  
- deployment  
- SaaS-ready claim  
- production-ready claim  
- reale Rechnungsordner verarbeiten  
- Release-Tags ändern  

---

## What is now proven

- ReviewDecision-Modell ist spezifiziert.  
- FinalizationReadiness-Modell ist spezifiziert.  
- Decision behaviors für alle sechs Typen sind spezifiziert.  
- Finalization blockers inkl. missing fields, duplicate target, unsafe target path, stale state, source hash changed, no explicit approval sind spezifiziert.  
- UI-, Manifest-/Audit- und Safety-Gate-Anforderungen sind spezifiziert.  
- `final_write_allowed=false`; sandbox/preview only.  
- Keine produktive Verarbeitung; keine realen Rechnungsordner.  
- Nicht SaaS-ready; nicht production-ready.

---

## What is still not proven

- Persistierte Decision-State- und UI-Flow-Implementierung  
- End-to-End Decision → finalization-ready in der laufenden UI  
- Finale Schreibpipeline unter den Safety Gates  
- Manueller Full-GUI-Durchlauf mit produktiver Freigabe (bewusst nicht in Scope)

---

## Test result

Focused docs/safety tests + Prompt-27-nahe Track-B-Tests + Track-A-Schutz + UI-v2/SaaS-Suite; siehe Audit.

---

## No productive processing

Ja — reines Design/Spec; keine Runtime-Finalisierung, kein `run_once`, keine Input-Mutation.

## No real invoice folders

Ja — Design bezieht sich auf Controlled-/Sandbox-Kontext; keine realen Rechnungsordner.

## Not SaaS-ready

Explizit nicht SaaS-ready.

## Not production-ready

Explizit nicht production-ready.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_STATE_AND_UI_FLOW_01`
