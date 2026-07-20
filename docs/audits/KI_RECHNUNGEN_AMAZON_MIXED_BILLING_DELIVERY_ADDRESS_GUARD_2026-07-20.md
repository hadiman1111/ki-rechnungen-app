# KI_RECHNUNGEN_AMAZON_MIXED_BILLING_DELIVERY_ADDRESS_GUARD_01

Datum: 2026-07-20  
Task: Amazon Mixed Billing/Delivery Address Guard  
HEAD vor Fix: `69231f4511a6a02270e62c46d72e74b8ef56302f`

## Root Cause

Beispiel: `260526_er_ai_amazon-eu-s-a-r-l-nied_36.99_amex.pdf`

1. **Welche Amazon-Regel?** Vendor-Profil `amazon-ai-amex` (`category=ai`, `payment_field=amex`, `target_folder=amex`, `exclusive=True`, `required_recipient_hints`: somaa/bismarck*).
2. **Rechnungs- vs. Lieferadresse?** Die Regel unterschied die Blöcke **nicht**.
3. **SOMAA nur Lieferadresse?** Ja — Treffer über `_recipient_search_text`, das bei Marker `rechnungsadresse` den **gesamten** `raw_text` (inkl. Lieferadresse) einbezieht.
4. **Rötestr. erkannt?** Als privates Signal im Dokument vorhanden, aber von der Amazon-Sonderregel nicht als Unsicherheit gewertet.
5. **payment_field=amex belegt?** Nein — kein Dokumentnachweis wie „American Express - 1005“. `amex` kam ausschließlich aus dem Vendor-Profil.
6. **Verantwortlich:** `resolve_supplier_profile_routing` + exclusive Early-Return in `InvoiceProcessor._process_invoice` (Routing-Guards wurden übersprungen).
7. **Output-Route:** exclusive Supplier-Match → `art=ai`, `payment_field=amex`, `zielordner=amex`.
8. **Trace:** `SupplierProfileRule=amazon-ai-amex`, `exclusive=True`, `value_not_extracted_from_document=True`.

Zusätzlich: `apply_mixed_address_guard` bewahrte bisher `payment_field in {amex, …}` auch bei gemischten Adresssignalen.

## Fix

1. **Adressblock-Parsing** in `routing_guards.py` (Rechnungs- vs. Lieferadresse).
2. **Mixed-Address-Decision** für private Rechnungsadresse + geschäftliche Lieferadresse → `unklar`.
3. **Supplier-Routing:** `required_recipient_hints` primär im Rechnungsadressblock; mixed billing/delivery blockiert Amazon-ähnliche Business/AMEX-Shortcuts.
4. **Processing:** Routing-Guards auch nach exclusive Vendor-Matches.
5. **UI-v2:** generische `address_policy` ohne private Defaults.

## Erwartetes Ergebnis (Beispielakte)

- nicht `ai`/`amex` als sichere Zuordnung
- `payment_field=unklar`, `target_folder=unklar`
- Dateiname ohne sicheres `ai`/`amex`

## Nicht verändert

- Hadi/SOMAA Arbeitsprofil / `profile_config.local.json`
- interne Launcher-App
- keine produktive Verarbeitung, keine realen Rechnungsordner
- kein Push
