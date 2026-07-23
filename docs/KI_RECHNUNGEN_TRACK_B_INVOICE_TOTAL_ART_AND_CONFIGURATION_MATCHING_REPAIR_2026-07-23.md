# Track-B Invoice Total, Art and Configuration Matching Repair

**Task ID:** `KI_RECHNUNGEN_TRACK_B_INVOICE_TOTAL_ART_AND_CONFIGURATION_MATCHING_REPAIR_01`  
**Masterplan:** Prompt 21/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_AMOUNT_AND_PAYMENT_REPAIRED_CONFIGURATION_MATCHING_PARTIAL`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Track-B Extraktion für Betrag, Zahlungsfeld, Dokumentart und Konfigurations-Matching reparieren — bei weiterhin gültiger Source of Truth: aktive Profil-/Konfigurations-Dateinamensmuster.

---

## User manual verification

PO-Upload der Preview-Exporte zeigte falsche Beträge und generisches Matching:

| Beleg | Alt | Korrekt |
|---|---|---|
| LUMITOP | 500,00 | 476,00 |
| 1A-Bootshop | 80,55 | 105,75 |
| Böttcher Rechnung | 84,39 (ok) | 84,39; payment=card, nicht amex |
| Luxvenum | 154,95 (ok) | payment fehlt |
| Böttcher Storno | 68,94 (ok) | art=storno sichtbar |

Alle 5 Items matchten **Unklar**.

---

## Baseline from Prompt 20

- Classification: `TRACK_B_PROFILE_CONFIGURATION_FILENAME_PATTERN_BRIDGE_READY_COMMITTED_AND_PUSHED`
- HEAD: `515a8403c957e808264229af989168fd0ca022ad`
- Konfigurationsmuster als Source of Truth; Komma-Beträge; fehlende Platzhalter explizit
- Gap: lokale Heuristik lieferte Basis-/Nettobeträge; card≠amex unklar; Storno als `er/er`

---

## Current wrong values (before)

- LUMITOP: `500,00` statt `476,00` (Prix de base)
- 1A-Bootshop: `80,55` statt `105,75` (Zeilen-Netto)
- Storno: `art=er` ohne Storno-Signal im Dateinamen
- Matching-Reason generisch für alle Unklar-Fälle

---

## Amount candidate repair

Neu: `invoice_tool/ui_v2/invoice_field_candidates.py`

- Candidate-Modell mit Final-/Netto-/Tax-/Base-/Line-Flags
- Priorität: Rechnungsbetrag, Gesamtpreis Brutto, Gesamtwert, Zahlung (PayPal), Moyen de paiement, Total (nicht HT)
- Ablehnung: Prix de base, Einzelpreis, Netto, Taxe totale, Spalten-Gesamt
- Manifest: `amount_candidates`, `selected_amount`, `selected_amount_reason`, `rejected_amount_candidates`

---

## Payment field repair

- PayPal → `paypal`
- Kreditkarte ohne AMEX → `card` (nie American Express)
- AMEX nur bei explizitem Nachweis
- Fehlende Zahlungsart → `FEHLT_payment_field` + präzise Reason

---

## Storno/art repair

- `STORNORECHNUNG` → `selected_art=storno`, `document_type=storno`, `art_ambiguity=true`
- Dateiname z. B. `…_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf`
- Literal `_er_` im Konfigurationsmuster bleibt erhalten

---

## Configuration matching repair

Präzisere Unklar-Reasons:

- payment_field fehlt
- paypal erkannt, keine aktive PayPal-Konfiguration
- card generisch, kein AMEX, keine passende Config
- Signal erkannt, Bedingungen nicht erfüllt

Kein Mapping von generischem `card` auf American Express.

---

## Controlled 5-PDF verification result

| Beleg | Betrag | Payment | Art |
|---|---|---|---|
| LUMITOP | 476,00 | paypal | er |
| 1A-Bootshop | 105,75 | paypal | er |
| Böttcher Rechnung | 84,39 | card | er |
| Luxvenum | 154,95 | fehlend | er |
| Böttcher Storno | 68,94 | fehlend | storno |

Konfiguration bleibt **Unklar**, wenn keine aktive Config (PayPal/AMEX/…) matcht — Reason jetzt präzise.

---

## Preview export examples before/after

**Before:**

- `…_LUMITOP_500,00_paypal.pdf`
- `…_1A-Bootshop.de_80,55_paypal.pdf`
- `…_er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf`

**After:**

- `…_LUMITOP_476,00_paypal.pdf`
- `…_1A-Bootshop.de_105,75_paypal.pdf`
- `…_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf`

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

- Aktive Profilkonfigurationen enthalten keine PayPal-Regel → Unklar bei PayPal korrekt, aber Matching bleibt partial
- GUI-Smoke für Pattern-Preview-Export steht noch aus
- Keine produktive Konto-Zuordnung (amex/ep/ai/private) ohne passende Evidenz/Config

---

## Test result

- Focused Track-B suite: **248 passed**
- UI-v2 / SaaS: siehe Laufprotokoll
- `git diff --check`: clean für gestaged Files

---

## No productive processing

Ja — Preview only.

## No real invoice folders

Ja.

## Not SaaS-ready

Ja — explizit nicht SaaS-ready.

## Not production-ready

Ja — explizit nicht production-ready.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_CONFIGURATION_MATCHING_REPAIR_01`
