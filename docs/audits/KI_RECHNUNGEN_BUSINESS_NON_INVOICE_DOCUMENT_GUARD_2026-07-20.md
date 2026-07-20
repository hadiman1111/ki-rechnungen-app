# BUSINESS NON-INVOICE DOCUMENT GUARD (LED-Centrum / Böttcher-Ergänzung)

Datum: 2026-07-20  
Ergänzung zu Routing-Guards nach Amazon Mixed Address Guard (`42a0991`)

## LED-Centrum Root Cause

Datei (Beobachtung): `260519_d_bestellbestaetigung-led-leuchtmittel_vn.pdf`

1. **Warum nur document?** `classify_document_type` traf Document-Keywords (`Ihre Bestellung` / Bestellbestätigung) → `dokumenttyp=document`. Anschließend lief `_process_document` ohne Art-/Payment-Routing → neutrales `d_…_vn.pdf`.
2. **SOMAA-Rechnungsadresse erkannt?** Inhaltlich vorhanden (SOMAA / Bismarckstrasse im Rechnungsadressblock), aber im Document-Pfad **nicht** für `art` ausgewertet.
3. **PayPal erkannt?** Im Text vorhanden (`Zahlungsmethode: PayPal`); Document-Pfad rief `detect_payment_method` **nicht** auf.
4. **document_type vs art/payment?** Ja — bisher bedeutete `document` faktisch Verlust von `art`/`payment_field`.
5. **Zwischenstatus?** Es gab nur `invoice` vs. neutrales `document` (plus optionale Document-Profiles), keinen business_non_invoice-Pfad.
6. **Finale neutrale Route:** `InvoiceProcessor._process_document`.

## Fix

- `evaluate_business_non_invoice_document` in `routing_guards.py`
- `_process_business_non_invoice_document` in `processing.py`:
  - `dokumenttyp=order_confirmation` (nicht invoice)
  - `art=ai` bei beruflicher Rechnungsadresse
  - `payment_field=paypal` bei explizitem PayPal
  - Zielordner `unklar` (nicht buchbar)
  - Dateiname: `{date}_d_{art}_{name}_{amount}_{payment}.pdf`
- UI-v2 `business_document_policy` generisch, ohne private Defaults

## Erwartetes LED-Ergebnis

- `document_type=order_confirmation`
- `art=ai`
- `payment_field=paypal`
- `target=unklar`
- Dateiname sinngemäß `260519_d_ai_bestellbestaetigung-…_29.01_paypal.pdf`

## Böttcher-Regression

Echte Rechnung ohne sicheren Zahlungsweg bleibt `invoice` / `er_ai_…_unklar` (nicht vobaai).

## Nicht verändert

- Hadi/SOMAA-Profil, interne Launcher-App
- keine produktive Verarbeitung, kein Push
