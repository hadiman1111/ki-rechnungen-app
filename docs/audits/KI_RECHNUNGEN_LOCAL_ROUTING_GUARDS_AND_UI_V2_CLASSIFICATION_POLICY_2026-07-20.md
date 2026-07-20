# KI-Rechnungen — Local Routing Guards + UI-v2 Classification Policy

**Task ID:** `KI_RECHNUNGEN_LOCAL_ROUTING_GUARDS_AND_UI_V2_CLASSIFICATION_POLICY_01`  
**Datum:** 2026-07-20  
**Initial:** `READY_FOR_LOCAL_ROUTING_GUARDS_AND_UI_V2_CLASSIFICATION_POLICY`  
**Final:** `LOCAL_ROUTING_GUARDS_AND_UI_V2_CLASSIFICATION_POLICY_IMPLEMENTED`

## Zweck

Lokale Fehlklassifikationen absichern und dieselbe Fachlogik generisch in der UI-v2-ClassificationPolicy vorbereiten — ohne private Hadi/SOMAA-Defaults in der allgemeinen Oberfläche.

## Guards

| Guard | Modul | Wirkung |
|---|---|---|
| Payment Evidence | `invoice_tool/routing_guards.py` + Hook in `apply_final_assignment` / `_process_invoice` | Ohne sicheren Zahlungsweg des Zahlenden kein `vobaai`/`vobaep` |
| Mixed Address | `evaluate_mixed_address_ambiguity` | Geschäftlich + privat → `unklar` |
| Invoice Direction | `evaluate_invoice_direction_guard` | Eigene Ausgangsrechnung → `document`, nicht Eingangsrechnung |
| Document Type | `evaluate_document_type_guard` + Keywords in `office_rules.json` | Jahreskonto/DATEV-Auswertung → `document`/`accounting_report` |

## UI-v2

- `ClassificationPolicy` in `saas_product_model.py` mit sicheren Defaults
- Persistenz Save/Load/Export/Import über `saas_profile_store` / Draft-State
- ViewModel-Texte für Zahlungsweg, Rechnungsrichtung, Dokumenttyp, gemischte Adressen
- Keine privaten Defaults, kein Cloud-/Mandantenversprechen

## Erwartete Fallergebnisse

| Fall | Ergebnis |
|---|---|
| Luxvenum (Lieferanten-IBAN) | `payment_field=unklar`, Ordner `unklar` |
| EasyPark Apple Pay ohne Endung | `unklar` |
| Bikesnboards gemischte Adresse | `unklar` |
| SOMAA → Maucher Ausgang | `document`, nicht `er_ai_…_vobaai` |
| DATEV Jahreskonto | `document` / `accounting_report` |

## Unverändert

- Hadi/SOMAA `profile_config.local.json` nicht geändert
- Interne Launcher-App nicht geändert
- Import/Export-Commit `1441cf9` erhalten
- Amazon-/Anthropic-/Recipient-/Duplicate-Verhalten regressiert nicht
- Kein Push, keine produktive Verarbeitung

## Tests

Kern- und UI-v2-Suiten grün (u. a. `test_routing_guards_real_cases.py`, `test_saas_ui_v2_classification_policy.py`).
