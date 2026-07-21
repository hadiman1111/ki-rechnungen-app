# GENERALIZED REAL-CASE ROUTING FIX VALIDATION

Datum: 2026-07-21  
Task ID: `KI_RECHNUNGEN_GENERALIZED_REAL_CASE_ROUTING_FIX_VALIDATION_COMMIT_PUSH_01`

## 1. Lokaler Böttcher-Fall

Beobachtete Datei (Fixture, nicht produktive Quelle): `260523_d_boettcher_amex.pdf`

Inhaltliche Signale:

- Titel `RECHNUNG`, Rechnung Nr., Datum, Positionen, MwSt, Gesamtwert
- Empfänger/Rechnungsanschrift mit konfigurierter Organisationsadresse (lokales Profil)
- `Zahlung per Kreditkarte` ohne Karten-/Konto-Referenz
- Formatnotizen `ZUGFeRD`/`XRechnung available on request`
- Compound-Label `Rechnungs-/Lieferscheindatum`
- Mehrdeutige Position `Fahrradschloss` (kein Private-Override)

Erwartetes konkretes Ergebnis:

- `dokumenttyp = invoice` (nicht document)
- `art = ai`
- `payment_field = unklar`
- `target_folder = unklar`
- Dateiname sinngemäß: `260523_er_ai_boettcher_84.39_unklar.pdf`

## 2. Verallgemeinerte Produktregel

| Schicht | Regel |
|---|---|
| Invoice vs Document | Starke Rechnungsindikatoren (Titel, Nr., Datum, Adresse, Positionen, MwSt/Summe, Zahlungsbedingungen) gewinnen gegen schwache Format-/Verbundphrasen. |
| Document-Keywords | Token-Grenzen: `lieferschein` matched nicht in `lieferscheindatum`. Harte Keywords (Bestellbestätigung, Jahreskonto, …) bleiben Dokument. |
| Business Assignment | Geschäftliche Rechnungsadresse setzt Business-Kontext über profilkonfigurierte Organisationskennungen — nicht über Artikeltexte. |
| Payment Evidence | Unspezifische Kreditkartenangabe ohne bekannte Karten-/Konto-Referenz → `payment_field=unklar`, Ziel `unklar`. Kein AMEX/vobaai/vobaep/private aus bloßer Formulierung. |
| Filename | Eingangsdateiname ist keine Beweisquelle für Dokumenttyp, Art, Zahlung oder Zielordner. |

Neutrales Synthetic-Fixture: ACME GmbH / Hauptstrasse / `Zahlung per Kreditkarte` → invoice + konfigurierte Business-Kategorie + payment unknown/review.

## 3. Root Cause

1. **Warum document?** Profil-`document_keywords` enthielten `lieferschein`. Substring-Match traf `Rechnungs-/Lieferscheindatum` → `lieferscheindatum` → Document vor Invoice-Keywords.
2. **Welche Regel?** `classify_document_type` prüfte Document-Keywords zuerst mit `normalized_keyword in search_text`.
3. **Invoice-Indikatoren?** RECHNUNG, Rechnung Nr., Datum, Adresse, Positionen, MwSt, Gesamtwert — vorhanden, aber nach Document-Hit nicht mehr ausgewertet.
4. **Warum Invoice nicht dominierte?** Keine Priorität starker Invoice-Signale über schwache Document-Treffer; kein Token-Boundary.
5. **SOMAA/Bismarck erkannt?** Im Text ja; im Document-Pfad aber ohne Invoice-Routing irrelevant für `er_ai_…`.
6. **Warum nicht art=ai?** Document-Pfad ohne Business-Invoice-Routing.
7. **„Zahlung per Kreditkarte“?** Im Text vorhanden; kein sicherer Zahlungsweg.
8. **Warum amex?** Eingangsdateiname enthielt `_amex`; schwache/fehlgeleitete Document-Verarbeitung konnte diesen Eindruck verstärken. Dokumenttext enthielt kein AMEX.
9. **AMEX-Quelle?** Dateiname / schwache Default-Logik — nicht belastbarer Dokumenttext.
10. **Verantwortliche Funktion:** `invoice_tool/classification.py::classify_document_type` (+ Profil-`document_keywords`).
11. **Beweis:** Reproduktion mit Preset + `lieferschein`-Keyword → vor Fix `document`, nach Fix `invoice`; Regressionstests in `tests/test_boettcher_business_invoice_unknown_card_payment_guard.py`.

## 4. Implementation Summary

- `classification.py`: Token-Boundary für Document-Keywords; Compound-Prefix für Invoice-Keywords (`rechnung`→`rechnungsadresse`); Format-Noise-Strip; starke Invoice-Indikatoren überschreiben schwache Document-Treffer.
- `routing_guards.py`: Guard für unspezifische Kreditkarte ohne Referenz; demote unsichere Payment-Felder (`amex`/`vobaai`/…) auf `unklar`.
- `saas_product_model.py` + `saas_profile_surface.py`: generische Policies
  - `invoice_detection_policy`
  - `payment_evidence_policy`
  - `business_assignment_policy`
  - plus bestehende address/business_document policies
- Keine privaten SaaS-Defaults (Hadi/SOMAA/Bismarck/AMEX-1005/vobaai/vobaep).

## 5. Tests

Neu:

- `tests/test_boettcher_business_invoice_unknown_card_payment_guard.py`

Fokussierte Suites (grün):

- Böttcher-Guard, Amazon Mixed Address, Business Non-Invoice, Routing Real Cases, Unknown Payment, Cursor/Anysphere, Recipient/Anthropic, File Lifecycle, Target Routing, Runtime Rules, SOMAA Filename Token Repair

UI-v2/SaaS Suites (grün):

- `test_saas_product_model.py`, `test_saas_ui_v2_classification_policy.py`, `test_saas_ui_v2_profile_store.py`, `test_saas_ui_v2_profile_draft_import_export.py`
- `tests/test_ui_v2_*.py` (passed/skipped)

## 6. Exact Expected Filename

`260523_er_ai_boettcher_84.39_unklar.pdf`  
(oder `…_boettcher-ag_…` je nach Supplier-Normalisierung)

## 7. Regression Matrix

| Fall | Erwartung | Ergebnis |
|---|---|---|
| Böttcher | invoice / ai / unklar | grün |
| Amazon private billing + business delivery | nicht ai/amex, Ziel unklar | grün |
| LED-Centrum Bestellbestätigung | nicht invoice/er; art ai; paypal; unklar | grün |
| Cursor/Anysphere | ai/amex bei echter AMEX-Evidence | grün |
| Luxvenum | Supplier-IBAN ≠ Payer → unklar | grün |
| EasyPark Apple Pay ohne Endung | unklar | grün |
| Bikesnboards mixed/ambiguous | unklar/review | grün |
| DATEV Jahreskonto | accounting report, nicht invoice | grün |
| SOMAA Ausgangsrechnung | outgoing, nicht incoming expense | grün |

## 8. UI-v2 Policy Summary

Generische Defaults (keine privaten Tenant-Werte):

- `invoice_detection_policy.invoice_indicators_override_format_notes = true`
- `invoice_detection_policy.format_availability_notes_are_not_document_type = true`
- `invoice_detection_policy.filename_is_not_source_of_truth = true`
- `payment_evidence_policy.generic_credit_card_without_identifier_target = "unklar"`
- `payment_evidence_policy.card_payment_requires_known_reference = true`
- `payment_evidence_policy.supplier_bank_details_are_not_payer_evidence = true`
- `business_assignment_policy.business_billing_address_assigns_business_context = true`
- `business_assignment_policy.ambiguous_items_do_not_override_business_billing_address = true`
- `business_assignment_policy.organization_identifiers_are_profile_configured = true`
- bestehende `address_policy` / `business_document_policy` unverändert gültig

## 9. Private-Default Guard Result

UI-v2 Blank-Policy und Surface-Payload enthalten keine Marker  
`Hadi` / `SOMAA` / `AMEX-1005` / `vobaai` / `vobaep` / `Bismarck` / `Rötestr`.

## 10. Explicit Non-Claims

- nicht SaaS-ready
- nicht multi-tenant
- kein vollständiger Rule Editor
- keine produktive Verarbeitung in diesem Lauf
- keine realen Rechnungsordner verändert
- kein GUI/Shell-WIP, Launcher, Evidence, venv, Build-App committed
