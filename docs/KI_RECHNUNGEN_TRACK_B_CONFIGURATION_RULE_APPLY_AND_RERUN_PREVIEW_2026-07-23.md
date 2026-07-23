# Track-B Configuration Rule Apply and Rerun Preview

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_01`  
**Masterplan:** Prompt 27/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Nach explizitem Speichern einer Konfigurationsregel soll die Preview-Matching-Auswertung sicher neu berechnet werden können — ohne produktive Verarbeitung, ohne Input-Mutation und ohne finale PDF-Schreibung.

---

## Baseline from Prompt 26

- Track-B Regelentwurf/Speichern bereit (`configuration_rule_draft` / `configuration_rule_editor`).
- PayPal-/Karten-Entwürfe mit Bestätigungspflicht; missing `payment_field` → `manual_review_only`.
- Speichern nur über UI-v2 `configuration_write_adapter`.
- Kein automatischer Preview-Rerun nach Speichern (Lücke für Prompt 27).
- HEAD Baseline: `994ca4f678dace6b69682ff05ef22a6767d8206c`
- Product status vorher: `TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_READY`

---

## Apply/rerun preview design

Modul: `invoice_tool/ui_v2/configuration_rule_apply_preview.py`

Flow:

1. Nutzer speichert Regel explizit (Prompt 26).
2. UI markiert Apply/Rerun als verfügbar (`mark_rule_saved_for_preview_apply`).
3. Nutzer klickt explizit eine Preview-only Aktion.
4. `rerun_preview_matching_after_rule_change` bewertet `planned_destinations` neu gegen aktive UI-v2-Konfigurationen.
5. Felder `previous_matched_configuration` / `new_matched_configuration` / `rule_applied` / … werden gesetzt.
6. Preview Export liest den aktualisierten Run-State.

Kein `run_once`. Kein Auto-Rerun ohne Klick.

---

## PayPal rule behavior

Nach Speichern von PayPal (`payment_field ist paypal`) und Preview-Rerun:

- LUMITOP: Unklar → PayPal
- 1A-Bootshop: Unklar → PayPal
- Böttcher card: bleibt Unklar (ohne separate Kartenregel)
- Luxvenum / Böttcher Storno: bleiben Unklar (fehlendes payment_field)
- Keine stille Geschäfts-/Kategorie-Zuordnung

---

## Generic-card rule behavior

Nach Speichern von `Kreditkarte / Nicht-AMEX-Karte` (`payment_field ist card`):

- Generische Karte kann auf Nicht-AMEX-Karte matchen
- AMEX bleibt separat und braucht expliziten AMEX-Nachweis
- Kein Mapping card → American Express

---

## Missing-payment-field behavior

Ohne Zahlungsfeld bleibt Unklar, sofern keine andere explizite Nutzerregel matcht. Keine blinde payment_field-Regel.

---

## UI action after save

Nach Speichern zeigt die Review-UI ein Panel mit einer der Aktionen:

- `Vorschau mit neuer Regel neu berechnen`
- `Matching erneut prüfen`
- `Regel auf Prüffälle anwenden`

Sichtbare Klarstellung:

- Regel gespeichert
- Vorschau neu berechnet
- keine finale Verarbeitung
- Originale unverändert

---

## Preview export after rerun

Manifest / review-items enthalten u. a.:

- `rule_applied`
- `applied_configuration_name`
- `applied_configuration_condition`
- `rerun_preview_after_rule_change`
- `matched_after_rule_change`
- `previous_matched_configuration`
- `new_matched_configuration`

Export-Dateinamen nutzen den neu gematchten Konfigurationszustand (Pattern der gematchten Regel).

---

## Safety guarantees

- Input unverändert
- Output nur Preview-Export
- Keine finalen PDF-Writes
- Kein produktiver `run_once`-Pfad
- Keine realen Rechnungsordner
- Track A / Processing-Core unberührt
- Release-Tags unverändert
- Unklar-Fallback bleibt erhalten

---

## What is now proven

- Explizites Speichern + expliziter Preview-Rerun
- PayPal-Fälle können in Preview von Unklar zu PayPal wechseln
- Generische Karte bleibt von AMEX getrennt
- Missing payment_field bleibt Unklar ohne passende Regel
- Manifest/Export trägt Apply/Rerun-Transparenzfelder
- Keine produktive Verarbeitung in diesem Flow

---

## What is still not proven

- Endgültige Review-Entscheidung → Finalisierung (späterer Prompt)
- Manueller Full-GUI-Durchlauf mit produktivem Freigabe-Schritt (bewusst nicht in Scope)
- SaaS-/Production-Reife

---

## Test result

Focused Prompt-27 + verwandte Track-B + Track-A-Schutz sowie UI-v2/SaaS-Suite (siehe Audit).

---

## No productive processing

Ja — nur Preview-Matching-Rerun auf in-memory Run-State.

## No real invoice folders

Ja — Controlled-Testpfade / Temp-Profile.

## Not SaaS-ready

Explizit nicht.

## Not production-ready

Explizit nicht.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_REVIEW_DECISION_TO_FINALIZATION_DESIGN_01`
