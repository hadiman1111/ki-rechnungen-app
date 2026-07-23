# Track-B Profile Configuration Filename Pattern Bridge Repair

**Task ID:** `KI_RECHNUNGEN_TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_REPAIR_01`  
**Masterplan:** Prompt 20/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Track-B Preview-Export-Namen an die **bestehende** Profil-/Konfigurations-Dateinamenssyntax anbinden:

aktive Profilkonfiguration → Dateinamensmuster → gerenderte Platzhalter → `REVIEW_REQUIRED__SUGGESTED__…`

---

## User correction

Nicht eine parallele kanonische Grammatik als Source of Truth nutzen.

Korrekte Quelle:

1. aktives Profil  
2. gematchte aktive Konfiguration  
3. konfiguriertes Dateinamensmuster  
4. gerenderte Platzhalterwerte  

Screenshot-/UI-Beispiel (American Express):

- Muster: `{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf`
- Beispiel: `2026-07-08_er_er_musterfirma_125,00_beispielkonto.pdf`

Beträge: Dezimal**komma**, zwei Nachkommastellen (`125,00`, `84,39`).

---

## Baseline from Prompt 19

- Classification: `TRACK_B_CANONICAL_FILENAME_TEMPLATE_AND_CATEGORY_MAPPING_READY_COMMITTED_AND_PUSHED`
- HEAD: `01859687051aa72b09352db0fea385f667334563`
- Generisches Muster: Datum / Rechnungsart / Zuordnung / Name / Betrag
- Beträge mit Punkt (`84.39`)
- Keine Nutzung der Konfigurationsmuster

---

## Existing configuration filename pattern source of truth

Aktives SOMAA-Profil (lokal) enthält u. a.:

| Konfiguration | Erkennung | Muster |
|---|---|---|
| American Express | payment_field ∈ amex / American Express | `{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf` |
| Event Production | ep / Event Production / vobaep | gleiches Muster |
| Architektur & Innenarchitektur | ai / … | gleiches Muster |
| Privat | private / Privat / … | gleiches Muster |
| Unklar | Fallback | gleiches Muster |

---

## Current gap (before this task)

- Prompt-19-Namen überschrieben die Konfigurationssyntax
- Punkt-Dezimalbeträge
- Keine Manifest-Felder für Konfiguration / Muster / Platzhalter

---

## Configuration matching bridge

Neu: `invoice_tool/ui_v2/configuration_matching.py`

- lädt aktive Konfigurationen + Unklar-Fallback aus dem Profilstore
- matcht über `payment_field` / `payment_account`-Signale gegen konfigurierte Werte
- unsichere Free-Text-Treffer für `payment_field` sind deaktiviert (Empfänger-/Letterhead-Kollisionen)
- bei Unsicherheit → konfiguriertes **Unklar**, kein Blind-Default auf Architektur

---

## Pattern renderer behavior

Neu: `invoice_tool/ui_v2/configuration_filename_renderer.py`

- ersetzt bekannte Platzhalter in konfigurierter Reihenfolge
- erhält Literale wie `_er_`
- fehlende Platzhalter → `FEHLT_<key>` + `missing_placeholders`
- `filename_source`:
  - `configuration_pattern`
  - `configuration_pattern_incomplete`
  - `canonical_fallback_no_configuration_pattern`
  - `original_fallback`

---

## Amount comma formatting

`format_amount_comma()` → immer `decimal_comma_2` (`84,39`, `500,00`).

---

## Placeholder mapping

| Platzhalter | Quelle |
|---|---|
| `invoice_date` | Extraktion → `YYYY-MM-DD` |
| `art` | Richtung/Dokumenttyp → `er` / `ar` |
| `supplier` | Lieferant / Gegenpartei |
| `amount` | Betrag mit Komma |
| `payment_field` | Match-Wert oder `payment_account`, sonst fehlend |

---

## Generic canonical template demoted to fallback

`canonical_filename_template.py` bleibt erhalten, wird aber nur genutzt wenn **kein** Konfigurationsmuster verfügbar ist. Manifest dann:

`filename_source = canonical_fallback_no_configuration_pattern`

---

## UI/report propagation

Review / Manifest / CSV / review-items zeigen u. a.:

- Konfiguration
- Dateinamensmuster
- Vorschau-Dateiname
- Platzhalterwerte
- fehlende Platzhalter
- Betrag format
- Benennung noch nicht final

---

## Controlled 5-PDF verification result

Input unverändert (5 PDFs). Preview-Export-Beispiele:

- `REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_er_Böttcher_AG_84,39_card.pdf`
- `REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-06-18_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf`
- `REVIEW_REQUIRED__SUGGESTED__2026-05-11_er_er_LUMITOP_500,00_paypal.pdf`
- `REVIEW_REQUIRED__SUGGESTED__2026-05-15_er_er_1A-Bootshop.de_80,55_paypal.pdf`
- `REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf`

Konfiguration in diesen Fällen überwiegend **Unklar** (kein sicheres payment_field-Match auf amex/ep/ai/private).  
Keine Dot-Decimal-Beträge in den Preview-Namen.

---

## Safety guarantees

- nur Preview/Sandbox
- Input byte-identisch
- kein `run_once`
- keine finalen Writes/Moves/Archives
- keine realen Rechnungsordner
- Track A / Processing-Core unberührt

---

## Remaining gap

- lokale Heuristik liefert `card`/`paypal`, nicht die Konto-Codes der Profilregeln (`amex`, `ep`, …)
- GUI-Smoke für Pattern-Preview-Export steht noch aus

---

## Relation to internal app behavior

Track A / Core unverändert. Track-B liest nur Profil-/Konfigurationsdaten und rendert Preview-Namen.

---

## Test result

- Focused Track-B suite: **218 passed**
- UI-v2 / SaaS: **576 passed, 44 skipped**
- `git diff --check`: clean (für gestaged Files)

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_01`
