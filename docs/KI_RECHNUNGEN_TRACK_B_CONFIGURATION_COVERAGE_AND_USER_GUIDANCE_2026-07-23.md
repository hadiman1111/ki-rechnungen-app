# Track-B Configuration Coverage and User Guidance

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_COVERAGE_AND_USER_GUIDANCE_01`  
**Masterplan:** Prompt 23/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CONFIGURATION_COVERAGE_AND_USER_GUIDANCE_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-reif**, **nicht produktionsreif**.

---

## Purpose

Wenn das Matching korrekt auf Unklar fällt, weil keine aktive Konfiguration die erkannte Zahlungsart abdeckt, sollen UI, Review-Report und Preview-Export klar erklären:

- was erkannt wurde
- welche Konfigurationen geprüft wurden
- warum keine passte
- welche Abdeckung fehlt
- was der Nutzer als Nächstes tun kann

Nur Guidance — keine automatische Erstellung/Änderung von Nutzerkonfigurationen.

---

## Baseline from Prompt 22

- Matching-Engine korrekt (PayPal ≠ AMEX, generic card ≠ AMEX ohne Nachweis).
- Controlled 5-PDF: alle Unklar mit präzisen Matching-Gründen.
- Coverage-Gaps offengelegt: keine PayPal-Konfiguration, keine Nicht-AMEX-Karten-Konfiguration.
- Nutzerführung war noch zu technisch / nicht handlungsorientiert genug.

HEAD-Baseline (inkl. Audit-Follow-up Prompt 22): `01c0716a28d11efe40ea15a538434327ce6eae3c`.

---

## Config coverage problem

Erkannte Signale (PayPal, generic card, fehlendes Zahlungsfeld) führten zu Unklar, aber Review/Export zeigten keine klare Abdeckungswarnung und keine sicheren nächsten Schritte.

---

## Guidance model

Neues Modul: `invoice_tool/ui_v2/configuration_guidance.py`

Funktion: `derive_configuration_coverage_guidance(...)`

Outputs:

| Feld | Bedeutung |
|---|---|
| `configuration_coverage_status` | z. B. `missing_config_for_detected_payment` |
| `missing_configuration_type` | `paypal` / `generic_card` / `payment_field` |
| `user_guidance` | kurzer deutscher Hinweis |
| `suggested_configuration_action` | sichere nächste Aktion |
| `guidance_severity` | `info` / `warning` / `error` |

Propagierung über Matching-Transparenz → Filename-Mapping → PlannedDestination → Review-UI → Preview-Export (Manifest/CSV/review-items/README).

---

## PayPal guidance

- Status: `missing_config_for_detected_payment`
- Typ: `paypal`
- Hinweis: „PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.“
- Aktion: „PayPal-Konfiguration ergänzen oder manuell prüfen.“

Keine automatische Zuordnung zu Architektur/Privat/Event.

---

## Generic-card guidance

- Status: `no_safe_card_configuration`
- Typ: `generic_card`
- Hinweis: „Kreditkarte erkannt, aber AMEX nicht belegt; keine passende Nicht-AMEX-Karten-Konfiguration vorhanden.“
- Aktion: „Karten-Konfiguration ergänzen oder Beleg manuell prüfen.“

Keine Empfehlung, generic card als AMEX zu matchen.

---

## Missing-payment-field guidance

- Status: `missing_payment_field`
- Typ: `payment_field`
- Hinweis: „Zahlungsfeld nicht sicher erkannt; Konfiguration konnte deshalb nicht eindeutig gewählt werden.“
- Aktion: „Zahlungsfeld prüfen oder Konfiguration mit anderem Match-Kriterium ergänzen.“

---

## UI/report propagation

Review-UI / review-items zeigen zusätzlich:

- Konfigurationsabdeckung
- Nutzerhinweis
- vorgeschlagene Aktion
- Matching-Grund / geprüfte Bedingungen (bereits Prompt 22)

Sichere nächste Schritte (generisch):

1. Konfiguration ergänzen  
2. bestehende Konfiguration anpassen  
3. manuell prüfen  
4. als Unklar belassen  

---

## Controlled 5-PDF verification result

| PDF | Erkennung | Guidance |
|---|---|---|
| FA011466.pdf (LUMITOP) | PayPal | PayPal-Abdeckung fehlt |
| Rechnung RE-202605-14594.pdf (Bootshop) | PayPal | PayPal-Abdeckung fehlt |
| 320262919974.pdf (Böttcher) | card / kein AMEX | generic-card Guidance |
| Rechnung-2026156019-102201.pdf (Luxvenum) | kein Zahlungsfeld | missing-payment-field |
| 420260091336.pdf (Böttcher Storno) | kein Zahlungsfeld | missing-payment-field |

Input unverändert; nur Preview-Export.

---

## Preview export result

Manifest/CSV/review-items/README enthalten:

- `configuration_coverage_status`
- `missing_configuration_type`
- `user_guidance`
- `suggested_configuration_action`
- `guidance_severity`

---

## Safety guarantees

- Keine Config-Mutation
- Kein `run_once`
- Keine finale Write/Move/Archive/Delete
- Keine realen Rechnungsordner
- Keine produktive Verarbeitung
- Track A / Processing-Core unberührt
- Release-Tags unverändert

---

## Remaining gap

- Nutzer muss PayPal-/Karten-Konfigurationen selbst anlegen (bewusst nicht auto).
- Pattern-Preview / GUI-Smoke für Konfigurationsmuster folgt als nächster Prompt.
- Kein Anspruch auf vollständige SaaS-Reife.

---

## Test result

- Focused Track-B + Protection: grün (inkl. neuer Guidance-Suite)
- UI-v2/SaaS: grün (576 passed, 44 skipped)
- `git diff --check`: clean

---

## No productive processing

Bestätigt.

## No real invoice folders

Bestätigt.

## Not SaaS-ready / Not production-ready

Bestätigt — Guidance ist Preview/Sandbox-Hilfe.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_01`
