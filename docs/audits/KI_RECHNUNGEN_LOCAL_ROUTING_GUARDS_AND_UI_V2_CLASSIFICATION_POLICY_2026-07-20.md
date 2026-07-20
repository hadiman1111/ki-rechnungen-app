# KI-Rechnungen — Local Routing Guards + UI-v2 Classification Policy

**Task ID:** `KI_RECHNUNGEN_LOCAL_ROUTING_GUARDS_AND_UI_V2_CLASSIFICATION_POLICY_01`  
**Datum:** 2026-07-20  
**Initial:** `READY_FOR_LOCAL_ROUTING_GUARDS_AND_UI_V2_CLASSIFICATION_POLICY`  
**Final:** `LOCAL_ROUTING_GUARDS_AND_UI_V2_CLASSIFICATION_POLICY_IMPLEMENTED`

## Zweck

Lokale Fehlklassifikationen absichern und dieselbe Fachlogik generisch in der UI-v2-ClassificationPolicy vorbereiten — ohne private Hadi/SOMAA-Defaults in der allgemeinen Oberfläche.

Erweiterung Fehlfall F: Cursor-/Anysphere-Inkonsistenz (ai vs private) per Decision-Trace erklären und stabilisieren.

## Guards

| Guard | Modul | Wirkung |
|---|---|---|
| Payment Evidence | `invoice_tool/routing_guards.py` + Hook in `apply_final_assignment` / `_process_invoice` | Ohne sicheren Zahlungsweg des Zahlenden kein `vobaai`/`vobaep` |
| Mixed Address | `evaluate_mixed_address_ambiguity` | Geschäftlich + privat → `unklar` |
| Invoice Direction | `evaluate_invoice_direction_guard` | Eigene Ausgangsrechnung → `document`, nicht Eingangsrechnung |
| Document Type | `evaluate_document_type_guard` + Keywords in `office_rules.json` | Jahreskonto/DATEV-Auswertung → `document`/`accounting_report` |
| Software/AI Tool | `invoice_tool/software_ai_tools.py` + Hook in `_process_invoice` | Cursor/Anysphere-Nutzung mit beruflichem Signal → `ai`; ohne → `unklar`; Refund behält Kategorie |

## UI-v2

- `ClassificationPolicy` in `saas_product_model.py` mit sicheren Defaults
- Nested `software_ai_tool_policy` (detect / require business signal / preserve refunds / unknown → unklar)
- Persistenz Save/Load/Export/Import über `saas_profile_store` / Draft-State
- ViewModel-Texte für Zahlungsweg, Rechnungsrichtung, Dokumenttyp, gemischte Adressen, Software-/AI-Tools
- Keine privaten Defaults, kein Cloud-/Mandantenversprechen

## Erwartete Fallergebnisse

| Fall | Ergebnis |
|---|---|
| Luxvenum (Lieferanten-IBAN) | `payment_field=unklar`, Ordner `unklar` |
| EasyPark Apple Pay ohne Endung | `unklar` |
| Bikesnboards gemischte Adresse | `unklar` |
| SOMAA → Maucher Ausgang | `document`, nicht `er_ai_…_vobaai` |
| DATEV Jahreskonto | `document` / `accounting_report` |
| Cursor BE0KJYS5-0016 / 101.10 | `ai` / `amex` / Ordner `amex` |
| Cursor BE0KJYS5-0010 / 59.01 (inkl. Refund) | `ai` / `amex` / Ordner `amex` |
| Cursor ohne berufliche Signale | `unklar` (Zur Prüfung), nicht blind `ai`/`private` |

## CURSOR / ANYSPHERE — ROOT CAUSE

| Feld | Wert |
|---|---|
| CURSOR_ROOT_CAUSE_FOUND | **yes** |
| Exact root cause | Vendor-Profil `cursor-anysphere` setzt nur `payment_field=amex`, hat **keine `category`**. `resolve_supplier_profile_routing` setzte bisher `art = category or default_art` → `private`. Bei `exclusive=True` überschrieb `_process_invoice` den bereits korrekten Business-Context (`ai` via somaa/Bismarck) mit diesem Private-Default. |
| Rule/function/profile field responsible | `supplier_routing.resolve_supplier_profile_routing` (`art = category or preset.routing.default_art`) + exclusive Branch in `processing._process_invoice`; Profilfeld `vendor_profiles[].category` fehlend; `routing.default_art=private` |
| Why file A became ai | `supplier_raw` oft nur `"Cursor"` → Vendor-Hints (`anysphere`, `hi@cursor.com`, …) matchen nicht → kein exclusive Supplier-Override → Business-Context `somaa-unspecified` / Straße → `art=ai`, Payment AMEX-1005 → `amex` |
| Why file B became private | `supplier_raw` enthält `Anysphere` / `hi@cursor.com` → exclusive Supplier-Match → fehlende category → **default_art=private** überschreibt Business-Context `ai` |
| default_art private involved | **yes** (nur bei exclusive Match ohne category) |
| Refund/Credit involved | **no** als Ursache (Refund-Zeilen ändern die Kategorie nicht; sie waren Begleiterscheinung in Beleg B) |
| page-2 Payment history involved | **no** als Ursache der Art-Inkonsistenz (AMEX-1005 war in beiden Fällen für Payment verfügbar) |

### Decision-Trace (synthetisch, isoliert)

**A (101.10, supplier_raw=`Cursor`):** supplier_profile=None → business=`ai` (somaa-unspecified) → payment=amex → final **ai/amex**

**B (59.01, supplier_raw mit Anysphere/hi@cursor.com):** supplier_profile=`cursor-anysphere` exclusive, economic_assignment=None, art vorher fälschlich private → business hätte `ai` geliefert → final vorher **private/amex**

## What was changed

1. `supplier_routing.py`: fehlende category → `art_deferred=True`, kein `default_art=private` mehr
2. `processing.py`: bei payment-only exclusive/non-exclusive Vendor-Regeln Art über Business-Context + `refine_routing_for_software_ai_tool` setzen
3. Neu: `invoice_tool/software_ai_tools.py` — AI-/Coding-Tool-Erkennung, berufliche Signale erforderlich, Refund behält Kategorie
4. UI-v2: `SoftwareAiToolPolicy` + ViewModel-Texte
5. Tests: `tests/test_cursor_anysphere_consistency.py`

## How future Cursor/Anysphere files are stabilized

- Payment-only Vendor-Regel liefert AMEX, aber **keine** blinde Private-Art
- Mit beruflichem Signal (Business-Context / Geschäfts-Straße) → konsistent **ai / amex**
- Ohne berufliches Signal → **unklar** (Zur Prüfung), nicht blind ai/private
- Refund/Credit/Mid-month-Negativzeilen kippen die wirtschaftliche Kategorie nicht

## Unverändert

- Hadi/SOMAA `profile_config.local.json` nicht geändert (category bleibt absichtlich leer; Code deferred Art)
- Interne Launcher-App nicht geändert
- Import/Export-Commit `1441cf9` erhalten
- Amazon-/Anthropic-/Recipient-/Duplicate-Verhalten regressiert nicht
- Kein Push, keine produktive Verarbeitung, keine realen Rechnungsordner verändert

## Tests

```text
.venv/bin/python -m pytest \
  tests/test_cursor_anysphere_consistency.py \
  tests/test_routing_guards_real_cases.py \
  tests/test_unknown_payment_routing_guard.py \
  tests/test_amazon_supplier_rule.py \
  tests/test_recipient_duplicate_anthropic_fix.py \
  tests/test_file_lifecycle.py \
  tests/test_target_routing.py \
  tests/test_runtime_rules.py \
  tests/test_saas_ui_v2_classification_policy.py
```

Ergebnis: **129 passed** (inkl. Cursor consistency + UI-v2 Policy).

| # | Report-Feld | Wert |
|---|---|---|
| 9 | What was changed | siehe oben |
| 10 | Future stabilization | siehe oben |
| 11 | New tests added | `tests/test_cursor_anysphere_consistency.py` |
| 12 | Cursor consistency test result | **passed** |
