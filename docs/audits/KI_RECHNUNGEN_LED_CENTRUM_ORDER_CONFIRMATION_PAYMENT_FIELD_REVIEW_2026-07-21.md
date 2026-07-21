# LED-Centrum Order Confirmation — Payment Field Review

Datum: 2026-07-21  
Task: `KI_RECHNUNGEN_LED_CENTRUM_ORDER_CONFIRMATION_PAYMENT_FIELD_REVIEW_01`  
HEAD vor Fix: `9b8f16c41bbe78d9980b4f5ed5d0630c43e86124`

## 1. Isolated run observed failure

Aus dem Isoliertlauf `20260721_123214` (PARTIAL):

| Beobachtung | Wert |
|---|---|
| Datei | `unklar/260519_d_ai_bestellbestaetigung-led_29.01_amex.pdf` |
| document_type | order_confirmation / `d_` — korrekt |
| art | ai — korrekt |
| Ziel | unklar — fachlich akzeptabel |
| payment_field | **amex** — falsch |
| Erwartet | paypal (Dateiname mit `paypal`, nicht `amex`) |

## 2. Root cause

1. **Warum amex?** Profil-Vendor `adobe-creative` wird als `payment_detection_rule` **vor** die Basisregeln (`explicit-paypal`) gehängt (`merge_rules_dicts` PREPEND).
2. **Welches Signal?** Hint `adobe` aus den Vendor-`recognition_hints`.
3. **Signalquelle?** Sichtbarer Dokumenttext im Footer („Adobe Reader … herunterladen“), **nicht** PDF-Metadaten, **nicht** Dateiname, **nicht** American-Express-Zahlungsevidenz, **nicht** Default-Business-AMEX.
4. **PayPal erkannt?** Ja im Belegtext: `Zahlungsmethode: PayPal`. Die Regel `explicit-paypal` hätte getroffen — wurde aber wegen First-Match nie erreicht.
5. **Warum Override?** First-Match der vorgelagerten Vendor-Regel `adobe-creative → amex`.
6. **Finale Zuweisung?** `detect_payment_method` → `InvoiceProcessor._process_business_non_invoice_document` übernimmt `payment_decision.payment_method` als `payment_field` / Dateinamens-Token.
7. **Gleiches Risiko anderswo?** Ja — jedes Nicht-Rechnungs- oder Rechnungsdokument mit expliziter Zahlungsart und gleichzeitigem Vendor-/Tool-Rauschen (Adobe/Microsoft-Footer o. Ä.).
8. **Cursor/Anysphere-Risiko?** Nein bei starker AMEX-Body-Evidenz (`Payment history American Express`) bzw. Vendor-Match ohne konkurrierendes explizites PayPal.

## 3. PayPal evidence

Sichtbarer Belegtext:

`Zahlungsmethode: PayPal`

## 4. AMEX false evidence source

- Vendor-Profil `adobe-creative` (`recognition_hints` enthält `adobe`)  
- Treffer auf Boilerplate „Adobe Reader“  
- Kein „American Express“, keine AMEX-Abbuchung, keine Kartenendung im Beleg

## 5. General payment evidence precedence rule

In `detect_payment_method` (`routing.py`):

1. Alle passenden Payment-Regeln sammeln (nicht nur First-Match).
2. **Explizite Zahlungsangaben im Dokumentkörper** (`Zahlungsmethode: …`, `Payment method: …`, `Zahlung erfolgte über …`) haben Vorrang — Auswertung nur auf `raw_text`, nicht auf Filename/Provider-Noise.
3. **Starke AMEX-Body-Evidenz** (`American Express`, `Abbuchung von AMEX`, Payment-History-Zeilen) bleibt gültig.
4. **Konflikt** explizites PayPal + starke AMEX-Body-Evidenz → kein stilles AMEX; Default/unknown.
5. **Schwaches Vendor-AMEX** ohne Body-Evidenz weicht explizitem PayPal/Bar.

UI-v2 `PaymentEvidencePolicy`:

- `explicit_document_payment_method_takes_precedence = true`
- `weak_vendor_amex_does_not_override_explicit_payment = true`

## 6. Non-invoice business document rule

Unverändert gültig:

- Bestellbestätigung bleibt Nicht-Rechnung (`order_confirmation`)
- Geschäftliche Zuordnung (art) bleibt möglich
- Explizite Zahlungsart bleibt erhalten
- Ziel weiterhin unklar/review (nicht buchbar)

## 7. Tests

- `tests/test_led_centrum_order_confirmation_payment_field_guard.py` (neu)
- Updates: `tests/test_saas_ui_v2_classification_policy.py`
- Focused + Regression: grün (siehe Commit-Report)

## 8. Regression risk

- Adobe-Rechnungen ohne konkurrierendes PayPal: Vendor-First-Match unverändert → amex möglich.
- Cursor/Anysphere mit echter AMEX-Payment-History: weiterhin ai/amex.
- Keine Hardcodes für LED-Centrum / „alle Bestellbestätigungen = PayPal“.

## 9. Cursor/Anysphere AMEX preserved

**Ja** — Tests und Logik behalten `ai`/`amex` bei realer AMEX-Evidenz.

## 10. Explicit non-claims

- not SaaS-ready  
- not full rule editor  
- no productive processing  
- no real invoice folder changes  
- no GUI/Shell-WIP, Launcher, Evidence, Venv oder Build-Artefakte committed  
