# KI_RECHNUNGEN_AMAZON_RULE_AND_DATEV_RECOGNITION_DIAGNOSIS_01

**Datum:** 2026-07-16 (Task-ID-Datum laut Vorgabe: 2026-07-14)  
**Initial classification:** READY_WITH_PREEXISTING_REPOSITORY_LIMITATIONS  
**Final classification:** AMAZON_RULE_AND_DATEV_DIAGNOSIS_PASS

## Preflight (Kurz)

| Item | Wert |
|---|---|
| Working directory | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Branch | `main` |
| HEAD | `6399cb82c5e2dc062691128f232e90df6567146e` |
| Upstream | `origin/main` |
| Ahead/behind | ahead 2 |
| Aktive Git-Operation | keine |
| AUTO_MERGE / Lock | nein |
| `.venv` / `.venv-flet085` | vorhanden |
| Profilpfad | `~/Library/Application Support/KI-Rechnungen/profile_config.local.json` |
| Profilhash vorher | `14a69e7faa7ba711af591b9bcea4d434faa37bd260895b4bbfb52ff104962aee` |
| Profilbackup | `profile_backups/profile_config.local.json.20260716_100011.bak` |
| Profilhash nachher | `9ff8e3bdbe7265bcbe798c275f37b20b7c6336a8456ec2b3220b7888399dff16` |
| Profilcompiler | `validate_profile()` → `[]`; `compile_profile_to_rules()` OK |
| Scan-Modell | `scan_model_id: rechnungen` |
| Vorher Amazon im Profil | keine ausdrückliche Amazon-Vendor-Regel |
| Vorher Amazon im Code | keine produktive Amazon-Routing-Regel (nur Drittanbieter-Libs) |
| Preexisting limitations | dirty worktree (viele uncommitted Dateien aus Vorarbeiten); `260714_Ausgabe` enthält fast keine Rechnungs-PDFs mehr (nur documents + `.DS_Store`) |

Evidence: `docs/audits/evidence/ki-rechnungen-amazon-rule-datev-recognition-diagnosis-2026-07-14/`

---

## A — Amazon Root Cause

### Warum keine ausdrückliche Amazon-Regel?

Im lokalen SOMAA-Profil existierten Vendor-Profile nur für Cursor/Microsoft/Adobe/EasyPark/Anthropic. Amazon fehlte.

### Warum gingen Amazon-Belege nach `ai` / `vobaai`?

Aus Real-Run `20260714_085812` (Decision-Trace / Routing-Summary):

1. **Art:** Business-Context-Regel `somaa-unspecified` (Keyword `somaa` im Text) → `art=ai`
2. **Payment:** Payment-Regel `somaa-default-bank` (Signal `somaa`, nicht explizit) → Methode `transfer`
3. **Final Assignment:** `transfer-ai` → `payment_field=vobaai`, `konto=vobaai`
4. **Zielordner:** Output-Route `vobaai-to-ai` → Ordner `ai`

Kein Vendor-Match, keine AMEX-Zuordnung. Empfänger war typischerweise SOMAA/Bismarck (korrekt AI-Kontext), aber Zahlungsweg wurde fälschlich als Volksbank-Default gesetzt.

### Marketplace-Sonderfall

Bei mehreren Amazon-PDFs extrahiert die KI den **Marketplace-Verkäufer** als `supplier` (z. B. SP United), obwohl Amazon der Rechnungsaussteller/Plattform-Issuer ist. Deshalb reicht `match_scope=supplier` allein nicht; es braucht eng begrenzte `issuer_hints` (Amazon EU / `www.amazon.de/contact-us`), **nicht** nacktes `amazon`.

### Recipient Guard

Exclusive Supplier-Regeln umgehen den Recipient Guard. Daher: Amazon-Regel nur mit `required_recipient_hints` (SOMAA / Bismarck). Ohne positiven SOMAA-/Architektur-Empfängernachweis greift die Regel nicht.

---

## A — Amazon-Regel (Profil)

### Vorher

Keine `amazon-*` Vendor-Regel.

### Nachher

`vendor_profiles[]` Eintrag `amazon-ai-amex`:

- `match_scope: supplier`
- `issuer_hints`: Amazon-EU-Aussteller + Amazon.de-Kontaktfußzeile (Marketplace)
- `required_recipient_hints`: `somaa`, Architektur-/Bismarck-Marker (kein reiner Privatname)
- `category / art: ai`
- `payment_field: amex`
- `target_folder: amex`
- `exclusive: true`
- **keine** `payment_reference` / Kartenendung

Semantik-Diff:

- PDR-Compiler unverändert (Amazon `match_scope=supplier` wird wie Anthropic **nicht** in `payment_detection_rules` kompiliert)
- Runtime: `supplier_routing.py` matched Supplier **oder** Issuer; optional Recipient-Gate

### Code (eng begrenzt)

- `invoice_tool/supplier_routing.py`: `issuer_hints`, `required_recipient_hints`
- `profile_config.schema.json`: VendorProfile-Felder dokumentiert
- Tests: `tests/test_amazon_supplier_rule.py`

Kein Hardcoding von Amazon außerhalb profilgetriebener Vendor-Felder.

---

## A — Tests

| # | Fall | Ergebnis |
|---|---|---|
| 1 | Amazon + SOMAA/Bismarck | `art=ai`, `payment=amex`, Ordner `amex`, nicht vobaai |
| 2 | Amazon + fehlender Empfänger | Regel greift nicht |
| 3 | Amazon + fremder Empfänger | Regel greift nicht |
| 4 | Amazon + privat ohne SOMAA/Bismarck | Regel greift nicht |
| 5 | Amazon nur im Text, Lieferant nicht Amazon | Regel greift nicht |
| 6 | Marketplace-Aussteller (Seller≠Amazon) | Issuer-Hints → amex |
| 7/8 | Bestehende AMEX-/AI-Pfade | nicht angefasst |
| 9 | Anthropic | unverändert `ep` + `amex-1005` + Ordner `amex` |
| 10 | Recipient Guard Martin Kohnle | `force_unklar` |

Unit: **15 passed** (`test_amazon_supplier_rule` + `test_recipient_duplicate_anthropic_fix`).

### Isolierter Lauf

Testroot:  
`/Users/hadi_neu/Desktop/Programm Belegerfassung/20_SOMAA_Rechnungstest/Amazon_Datev_Diagnosis_20260716_100051/`

| Datei | Ergebnis |
|---|---|
| `amazon1.pdf` | `amex/…_amex.pdf` (Regel `amazon-ai-amex`, supplier) |
| `invoice_amazon rad.pdf` | `amex/…_amex.pdf` |
| `amazon2.pdf` (Erstlauf) | zunächst `ai/…_vobaai` (Issuer-Hint fehlte) |
| `amazon2.pdf` (Retest nach Issuer-Erweiterung) | `amex/…_amex.pdf` (`www.amazon.de/contact-us`) |

Keine erfundene Kartenendung in Dateinamen/`payment_field`.

---

## B — DATEV-Diagnose (ohne Korrektur)

### Material

9 Belege (Kopien): 2× Amazon, Anthropic, RE0072, Martin Kohnle, AMEX-Monatsabrechnung, Vodafone, Haufe, Eigenbeleg.

Real-Run-Mapping `20260714_085812`: für alle neun geprüften Original/Ausgabe-Paare gilt  
`original_sha256 == final_sha256`.

Aktuelle `260714_Ausgabe`-Ordnerintegrität: Rechnungsausgaben fehlen physisch (vor Task bereits), Mapping/Archiv/Kopie bleiben auswertbar.

### PDF-Veränderung durch Programm?

**Nein.** Ausgabe erfolgt per `shutil.copy2` (`processing.py`). Byte-Identität im Mapping bestätigt. Keine PDF-Metadaten-/Textlayer-Änderung durch das Programm nachweisbar.

Klassifikation dominant:

- `PROGRAM_OUTPUT_BYTE_IDENTICAL`
- `OUTPUT_BYTE_IDENTICAL_NO_PROGRAM_CAUSE_PROVEN`
- `DATEV_DATE_VALUE_NOT_AVAILABLE` / `PARTNER_VALUE_NOT_AVAILABLE` (keine DATEV-Screenshots/Werte vom Nutzer)

### Datumsanalyse (Hypothesen, nicht DATEV-behauptet)

Beispiel Amazon1:

- Rechnungs-/Lieferdatum: **27.05.2026**
- Bestelldatum: **26.05.2026** (−1 Tag relativ zum Rechnungsdatum)

Wenn DATEV das Bestelldatum statt Rechnungsdatum nimmt, erklärt das einen „Tag früher“-Effekt **ohne** Programmfehler und **ohne** PDF-Rewrite.

Haufe: Rechnungsdatum 17.05. / Zahlungsziel 18.05. — mehrere Datumskandidaten im Layout.

### Geschäftspartner

Amazon Marketplace: sichtbarer Aussteller/Plattform Amazon, extrahierter Supplier oft Marketplace-Seller → DATEV kann Layout-/Reihenfolge-bedingt den falschen Partner wählen. Programm ändert den PDF-Textlayer nicht.

### Explizit nicht implementiert

- keine pauschale +1-Tag-Korrektur
- keine PDF-Metadaten-Überschreibung
- keine OCR-/Textlayer-Manipulation

---

## Post-Integrity

| Check | Status |
|---|---|
| Profil kompiliert | OK |
| Recipient Guard aktiv | OK (`force_unklar` Kohnle) |
| Anthropic ep/amex-1005/amex | OK |
| Amazon SOMAA → ai+amex+amex | OK |
| Amazon fremd/unklar nicht auto ai/amex | OK (Unit) |
| Same-run-Duplikat-Lifecycle | unverändert (Regressionstests PASS) |
| UI-v2 / Launcher Hashes | unverändert (`app_ui_v2.py` `36376835…`) |
| Reale RECHNUNGEN Counts | Kopie 50/50, Archiv 47/47, Ausgabe 3/3 |
| Kein Commit / kein Push | bestätigt |

---

## Nächster Task (nicht ausgeführt)

`KI_RECHNUNGEN_FIRST_CONTROLLED_REAL_COPY_RUN_AND_LAUNCHER_RESULT_REVIEW_01`
