# KI_RECHNUNGEN_RECIPIENT_DUPLICATE_AND_ANTHROPIC_RULE_FIX_01

**Datum:** 2026-07-14  
**Initial classification:** READY_FOR_RECIPIENT_DUPLICATE_AND_ANTHROPIC_FIX  
**Final classification:** RECIPIENT_DUPLICATE_AND_ANTHROPIC_RULE_FIX_PASS

## Preflight

| Item | Wert |
|---|---|
| Branch | main |
| HEAD | 6399cb82c5e2dc062691128f232e90df6567146e |
| Upstream | origin/main (0 ahead / 2 behind) |
| Aktive Git-Operation | keine |
| AUTO_MERGE | nein |
| Profilpfad | `~/Library/Application Support/KI-Rechnungen/profile_config.local.json` |
| Profilhash vorher | `e1aa0110be47de17bb8b7c0b01229595351f11c007b25fc6a34bd3a47ad59713` |
| Profilbackup | `profile_backups/profile_config.local.json.20260714_112242.bak` |
| Profilhash nachher | `14a69e7faa7ba711af591b9bcea4d434faa37bd260895b4bbfb52ff104962aee` |
| Profilcompiler | `validate_profile()` → `[]` (OK) |
| Scan-Modell | `scan_model_id: rechnungen` |
| CFG-001 Runtime | `False` (legacy_relative targets) |

## A — Recipient Guard

### Root Cause

1. `default_art = private` in `office_rules.json`
2. Kein SOMAA-Business-Kontext auf Fremdempfänger (Marc Goldhammer)
3. `payment_field = unklar`
4. Output-Route-Regel `private-keep-folder-despite-unclear-attributes` (art=private + payment=unklar → Ordner private)

### Fix

- Neues Modul `invoice_tool/recipient_guard.py`
- Profilfeld `recipient_policy` mit Business-/Private-Allowlists
- Guard aktiv nur wenn `recipient_policy` konfiguriert ist
- Fremd-/fehlender Empfänger → `art=unklar`, `payment_field=unklar`, Zielordner `unklar`
- Positive Private weiterhin über Prioritätsregel Rötestraße oder Private-Allowlist

### Martin Kohnle (isoliert)

- Output: `unklar/260621_er_unklar_martin-kohnle_3172.31_unklar.pdf`
- Nicht private, art=unklar

## B — Same-Run-Duplikat-Lifecycle

### Root Cause

`_create_duplicate_report()` beendete den Pfad nach Report-Erstellung ohne Archivierung; `run_seen_fingerprints` verhinderte nur Doppelverarbeitung.

### Fix

- `archive_same_run_duplicate()` in `file_lifecycle.py`
- Ziel: `<source_root>/archiv/<run_id>/duplikate/<original_filename>`
- Kollision: `__duplikat_N`
- Report-Felder: `source_lifecycle_status`, `source_archive_path`, `source_archive_result`, `source_archive_error`

### RE0072 (isoliert)

- Eine Ausgabe in `ai/`
- Archiv: `archiv/<run_id>/Rechnung_RE0072.pdf` + `duplikate/Rechnung_RE0072_29.06.2026.pdf`
- Null PDFs direkt im Eingang nach Lauf

## C — Anthropic-Profilregel

### Root Cause

Keine exklusive Lieferantenregel; parallele Pfade über Business-Kontext/Transfer-Regeln konnten zusätzliche EP-Ausgabe erzeugen. Vendor-Compiler matchte ggf. auch Fließtext.

### Fix

- Profil-Vendor `anthropic-ep-amex-1005` mit `match_scope: supplier`, `exclusive: true`
- Runtime `supplier_routing.py` setzt art=ep, payment=amex-1005, Zielordner=amex
- Vendor-Compiler überspringt `match_scope=supplier` bei payment_detection_rules

### Anthropic (isoliert, Invoice-MQYKKQPM-0003.pdf)

- Eine Ausgabe: `amex/260623_er_ep_anthropic-pbc_90.00_amex-1005.pdf`
- Keine EP-Parallelausgabe, keine vobaep-Zuordnung
- Provenienz im Routing-Trace als `SupplierProfileRule` / `profile_rule`

## Geänderte Dateien

- `invoice_tool/recipient_guard.py` (neu)
- `invoice_tool/supplier_routing.py` (neu)
- `invoice_tool/file_lifecycle.py`
- `invoice_tool/processing.py`
- `invoice_tool/profile_compiler.py`
- `tests/test_recipient_duplicate_anthropic_fix.py` (neu)
- `tests/test_file_lifecycle.py` (Same-run-Erwartung aktualisiert)
- Lokales Profil (Backup siehe oben)

## Tests

- `tests/test_recipient_duplicate_anthropic_fix.py`: 6/6 PASS
- `tests/test_profile_compiler.py`: PASS
- `tests/test_file_lifecycle.py`: Same-run-Test aktualisiert PASS

## Reale Ordnerintegrität

Hashes von Referenzkopien und historischen Ausgaben unter `/Users/hadi_neu/Desktop/RECHNUNGEN` vor/nach Lauf unverändert (siehe `09_Evidence/summary.log` im isolierten Testroot).

## Geschützte Dateien

- `app_ui_v2.py` SHA-256 unverändert: `363768353192b718ef03df54349a172cf3214f8735477f289a388f6255fccbd5`

Kein Commit. Kein Push.
