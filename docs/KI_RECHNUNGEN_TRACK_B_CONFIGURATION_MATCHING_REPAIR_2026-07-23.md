# Track-B Configuration Matching Repair

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_MATCHING_REPAIR_01`  
**Masterplan:** Prompt 22/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CONFIGURATION_MATCHING_READY_CONFIG_COVERAGE_GAPS_DISCLOSED`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Track-B aktives Konfigurationsmatching reparieren: Bedingungen aktiver Profilkonfigurationen auswerten, Treffer nur bei erfüllten Bedingungen, Unklar nur als Fallback mit präziser Begründung.

---

## Baseline from Prompt 21

- Beträge/Payment/Art repariert (LUMITOP 476,00, Bootshop 105,75, Storno sichtbar).
- Matching blieb partial: alle 5 Fälle Unklar, Reasons generisch oder unvollständig transparent.
- Aktive Profile hatten keine PayPal-Konfiguration.

---

## Current partial matching problem

- PayPal/card wurden erkannt, aber Matching erklärte Kandidaten/Bedingungen nicht vollständig.
- Mehrdeutige Treffer fielen pauschal auf Unklar statt höchste Konfidenz.
- Manifest/UI zeigten keine `evaluated_configuration_candidates` / `available_configurations`.

---

## Active configuration source

Source of Truth:

`active profile` → `profile_store.load_profile_bundle` → aktive `configurations` + `unmatched`  
über `invoice_tool/ui_v2/configuration_matching.py` (`load_active_configuration_candidates`).

Aktuelle aktive Runtime-Konfigurationen (Beispielprofil):

- American Express (`payment_field`: amex / American Express)
- Event Production (`payment_field`: ep / …)
- Architektur & Innenarchitektur (`payment_field`: ai / …)
- Privat (`payment_field`: private / …)
- Unklar (Fallback)

Keine aktive PayPal-Konfiguration.

---

## Configuration condition model

Aus bestehenden Config-Feldern (`matching.feature_key`, `operator`, `values`):

- `payment_field_equals` / `payment_field_contains`
- `supplier_contains` / `recipient_contains`
- `document_type_equals`
- `text_contains` (nur Nicht-Payment-Features)
- `fallback_unmatched`

Hard guards:

- PayPal matcht nie American Express
- generic card/credit_card matcht nie AMEX ohne expliziten AMEX-Nachweis
- inaktive Konfigurationen matchen nie

---

## Candidate evaluation

Pro Beleg:

- `available_configurations`
- `evaluated_configuration_candidates` inkl. `condition_results`
- `matched` / `reason` / `confidence`
- `unmatched_reasons`
- `missing_configuration_rule`
- `alternative_matches` bei Mehrfachtreffern

---

## Matching priority

1. Nur aktive Nicht-Fallback-Configs
2. Bedingungen müssen erfüllt sein
3. Spezifische Payment-Configs vor Unklar
4. Unklar nur wenn kein Nicht-Fallback matcht
5. Bei mehreren Treffern: höchste Konfidenz, Alternativen dokumentieren

---

## PayPal / no-PayPal-config behavior

Wenn `payment_field=paypal` und keine aktive PayPal-Config:

- Match = Unklar
- Reason: `payment_field paypal detected, but no active configuration supports PayPal`
- `missing_configuration_rule`: keine aktive PayPal-Konfiguration

---

## Generic-card / no-AMEX behavior

Wenn `payment_field=card|credit_card|card_generic` ohne AMEX-Nachweis:

- kein American-Express-Match
- Reason: `generic credit card detected, AMEX not proven`

---

## Controlled 5-PDF verification result

| Beleg | Payment | Konfiguration | Grund |
|---|---|---|---|
| LUMITOP | paypal | Unklar | keine aktive PayPal-Config |
| 1A-Bootshop | paypal | Unklar | keine aktive PayPal-Config |
| Böttcher Rechnung | card | Unklar | generic card, AMEX not proven |
| Luxvenum | fehlend | Unklar | payment_field fehlt |
| Böttcher Storno | fehlend | Unklar | payment_field fehlt |

Kein Blind-Mapping auf Architektur/Privat/Event/AMEX.

---

## Preview export result

Manifest/CSV/review-items enthalten Matching-Transparenz:

- `available_configurations`
- `evaluated_configuration_candidates`
- `matched_configuration_reason`
- `condition_results`
- `missing_configuration_rule`

Preview-Dateinamen nutzen das gematchte (hier: Unklar-)Pattern.

---

## UI/report explanation

Review zeigt:

- Konfiguration
- Matching-Grund
- geprüfte Bedingungen
- verfügbare / geprüfte Konfigurationen
- fehlende Konfigurationsregel

Nächste Nutzeraktion klar: passende aktive Konfiguration anlegen/anpassen oder manuell prüfen.

---

## Safety guarantees

- Input unverändert
- nur Preview/Sandbox
- kein `run_once`
- keine finalen Writes/Moves/Archives
- keine realen Rechnungsordner
- Track A / Processing-Core unberührt

---

## Remaining gap

- Aktive Konfigurationsabdeckung unvollständig (kein PayPal; keine generische Karten-Config außer AMEX mit Nachweis).
- GUI-Smoke für Pattern-Preview-Export steht noch aus.
- Nutzerführung zur Config-Abdeckung folgt als eigener Prompt.

---

## Test result

Siehe Laufprotokoll / Audit.

---

## No productive processing

Ja — Preview only.

## No real invoice folders

Ja.

## Not SaaS-ready

Ja.

## Not production-ready

Ja.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CONFIGURATION_COVERAGE_AND_USER_GUIDANCE_01`
