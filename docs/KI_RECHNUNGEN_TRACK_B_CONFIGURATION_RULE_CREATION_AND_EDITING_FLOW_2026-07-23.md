# Track-B Configuration Rule Creation and Editing Flow

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_01`  
**Masterplan:** Prompt 26/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Aus Review-/Guidance-Hinweisen zu fehlender Konfigurationsabdeckung sollen sichere Regelentwürfe erzeugt, geprüft und nur nach expliziter Nutzerbestätigung in UI-v2-Profil-/Config-State gespeichert werden können.

---

## Baseline from Prompt 25

- GUI-Smoke für Pattern Preview Export bestanden.
- PayPal / generische Nicht-AMEX-Karte bleiben korrekt, aber unerwünscht Unklar, weil keine passende aktive Konfiguration existiert.
- Missing `payment_field` bleibt Unklar mit Guidance.
- HEAD Baseline: `8d035dbd0b1ea6b7dfbaed7c96eedee8a6949033`
- Product status vorher: `TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_PASS_WITH_CONFIG_COVERAGE_GAPS`

Docs:

- `docs/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_2026-07-23.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_2026-07-23.md`

---

## Remaining configuration coverage gap

Nach Prompt 25 fehlen weiterhin aktive Regeln für:

1. PayPal (`payment_field=paypal`)
2. Generische Kreditkarte ohne AMEX-Nachweis (`payment_field=card`)
3. Fehlendes Zahlungsfeld (kein blindes payment_field-Matching)

Unklar-Fallback bleibt korrekt aktiv, bis der Nutzer eine Regel bestätigt.

---

## Rule draft model

Modul: `invoice_tool/ui_v2/configuration_rule_draft.py`

`ConfigurationRuleDraft` Felder u. a.:

- `draft_id`, `source_review_item_id`, `source_filename`
- `draft_type`: `create_new_configuration` | `edit_existing_configuration` | `manual_review_only`
- vorgeschlagener Name, Matching-Merkmal/Operator/Werte, Dateinamensmuster
- `reason`, `source_evidence`, `warnings`
- `requires_user_confirmation=true`, `saved=false`
- Dateiname-Vorschau, unbekannte Platzhalter, Duplikatwarnung, Future-Match-Preview

Kein stilles Speichern. Keine privaten/Hadi-/SOMAA-Defaults.

---

## PayPal draft behavior

- Typ: `create_new_configuration`
- Name: `PayPal`
- Bedingung: `payment_field ist paypal`
- Dateinamensmuster: Unklar-/Fallback-Pattern oder vorhandenes aktives Pattern
- Warnung: keine automatische Geschäfts-/Kategorie-Zuordnung
- Speichern nur nach explizitem Klick + Zielordner

---

## Generic-card draft behavior

- Name: `Kreditkarte / Nicht-AMEX-Karte`
- Bedingung: `payment_field ist card`
- Warnung: generische Karte ist nicht AMEX; AMEX bleibt separat und braucht expliziten Nachweis
- Kein Mapping card → AMEX

---

## Missing-payment-field behavior

- Keine automatische payment_field-Regel
- `draft_type=manual_review_only`
- Vorschlag: Beleg prüfen, anderes Match-Kriterium wählen oder Unklar belassen
- Aktion „Manuell prüfen / Unklar lassen“ speichert nichts

---

## UI actions

In der Review-UI (bei Coverage-Gaps):

1. **Konfiguration aus Hinweis erstellen**
2. **Bestehende Konfiguration anpassen**
3. **Manuell prüfen / Unklar lassen**

Erstellen/Anpassen öffnet ein Entwurfspanel (kein stilles Speichern) mit Evidenz, Vorschlag, Dateinamensmuster, Vorschau, Warnungen, Speichern/Abbrechen.

Modul UI: `invoice_tool/ui_v2/configuration_rule_editor.py`  
Verdrahtung: `invoice_tool/ui_v2/pages/review.py`

---

## Save behavior

- Speichern erfordert `explicit_user_confirmation=True` (expliziter Button).
- Speichert nur in UI-v2 Profil-/Config-State über `configuration_write_adapter`.
- Kein Track-A-Config-Schreiben.
- Kein `run_once`.
- Keine Input-Mutation.
- Keine finalen PDF-Writes.
- Keine produktive Verarbeitung.
- Nach Speichern: kein automatischer produktiver Rerun (Preview-Rerun ist Folgeaufgabe).

---

## Validation

Geprüft werden:

- Name vorhanden
- Matching-Merkmal / unterstützter Operator / mindestens ein Wert
- Dateinamensmuster vorhanden
- bekannte Platzhalter (unbekannte → Fehler)
- Duplikatbedingung → Warnung
- kein AMEX aus generic-card
- keine Business-Category-Defaults
- Zielordner zum Speichern erforderlich (kein privater Default)

---

## Safety guarantees

- Recognition findet Fakten; Matching prüft aktive Regeln; fehlende Regel → Guidance → Draft → Bestätigung
- Unklar-Fallback bleibt erhalten
- Keine produktive Verarbeitung
- Keine realen Rechnungsordner
- Track A / Processing-Core unberührt
- Release-Tags unverändert
- Keine Reife-Claims

---

## What is now proven

- PayPal-/Nicht-AMEX-Karten-Entwürfe aus Guidance
- Missing-payment ohne blinde Regel
- Review-Aktionen sichtbar
- Validierung inkl. Platzhalter/Duplikat/AMEX-Guard
- Explizites Speichern in isoliertem UI-v2-Profil (Tests)
- Report-Felder `configuration_rule_draft_available` u. a.

---

## What is still not proven

- End-to-end manuelle GUI mit Speichern + anschließendem Preview-Rerun auf Controlled-5-PDF
- Automatischer Apply/Rerun nach Speichern
- SaaS-/Production-Reife

---

## Test result

Focused + verwandte Track-B-Tests sowie UI-v2/SaaS-Suite (siehe Audit).

---

## No productive processing

Ja — nur Draft/Save in Profil-State; kein produktiver Lauf.

## No real invoice folders

Ja — Controlled-Testpfade / Temp-Profile; keine realen Rechnungsordner.

## Not SaaS-ready

Explizit nicht.

## Not production-ready

Explizit nicht.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_APPLY_AND_RERUN_PREVIEW_01`
