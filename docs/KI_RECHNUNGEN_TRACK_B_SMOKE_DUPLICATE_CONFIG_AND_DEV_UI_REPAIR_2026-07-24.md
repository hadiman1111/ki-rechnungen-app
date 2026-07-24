# Track-B Smoke — Duplicate Config + Dev UI Repair (2026-07-24)

## Purpose

Unblock manual Track-B smoke for PayPal configuration creation (FA011466 / LUMITOP)
without enabling productive processing, without touching Track A/core, and without
mutating real invoice folders.

## Smoke blocker

Saving a PayPal rule from Review guidance failed with:

> Doppelte aktive Regel für „Privat“ in „Privat“ und „Privat“

The UI treated an unrelated Privat profile issue as a PayPal save blocker.

## Duplicate config diagnosis

- Active configs load from UI-v2 / canonical profile store:
  `~/Library/Application Support/KI-Rechnungen/profiles_v2/<profile_id>/`
- Active profile at smoke time: `local`
- Privat config values include aliases `private`, `privat`, `Privat`, `Private Rechnung`
- `privat` and `Privat` normalize to the same routing value
- Bundle validation (`validate_duplicate_active_rules` + target-routing) then reports
  a self-alias collision as „doppelte aktive Regel … Privat und Privat“
- This is **not** an exact duplicate of two Privat configs and **not** a PayPal conflict
- PayPal draft (`payment_field ist paypal`, controlled target) itself was valid

## Repair behavior

1. Track-B duplicate analysis by stable key:
   `name + condition + target + filename_pattern`
2. Exact duplicates → `duplicate_exact_active_config` (blocking + remediation)
3. Same name / different condition → `duplicate_name_warning` (non-blocking)
4. Intra-config alias collisions (Privat/privat) → profile warning, **do not block**
   unrelated PayPal saves
5. UI-v2 write adapter uses Track-B-aware bundle validation for rule saves
6. Dev remediation actions (explicit click only, UI-v2 state only):
   - „Doppelte Konfigurationen anzeigen“
   - „Exakte Duplikate deaktivieren“

## PayPal smoke action

„PayPal-Regel speichern und Matching neu berechnen“

- Requires explicit confirmation
- Requires controlled output target under
  `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` (or child)
- Condition: `payment_field ist paypal`
- Pattern: `{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf`
- No silent business category
- No card→AMEX mapping
- Preview matching rerun only — no `run_once`, no final write

## Dev UI cleanup

Review detail / rule editor:

- Labels above fields (`form_field_group`) — no overlapping label/input
- Wider / taller inputs
- Sticky action row (top + bottom of draft panel)
- Actions:
  - Konfiguration speichern
  - Speichern und Matching neu berechnen
  - PayPal-Regel speichern und Matching neu berechnen
  - Prüffall als Text kopieren
  - Diagnose kopieren
  - Finalisierungs-Trockenlauf erstellen
  - Sandbox-Finalschreiben testen
- Layout marker: `track_b_smoke_dev_ui_layout_v1_no_overlap`

## Copy-text / debug action

Copied text includes source file, suggested filename, matching status, guidance,
proposed config, target folder, safety flags, review decision, finalization state.
Diagnose copy includes `final_write_allowed_for_production=false` and duplicate report.

## Safety guarantees

- No productive processing
- No `run_once`
- No real invoice folders
- No production final-write (`final_write_allowed_for_production=false`)
- No Track-A protected UI/core edits
- No release tag changes
- Duplicate remediation never silently deletes; only deactivates exact extras after click

## What is now proven

- PayPal rule can be saved despite Privat alias noise
- Exact duplicate detection + explicit remediation path exists
- PayPal smoke action rematches LUMITOP / 1A-Bootshop to PayPal in preview
- Generic card stays non-AMEX; missing payment_field stays Unklar
- Copy/debug helpers and layout markers are present
- Focused Track-B / Track-A protection tests pass

## What remains manual

1. Open UI-v2 Review with controlled folders
2. Open FA011466 → create PayPal draft
3. Set target to
   `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/geplant/paypal`
4. Click „PayPal-Regel speichern und Matching neu berechnen“
5. Verify LUMITOP + 1A-Bootshop → PayPal
6. Build finalization preview → dry-run package → sandbox final-write test

## Test results

Focused suite (this task):

- `tests/test_track_b_smoke_duplicate_config_and_dev_ui_repair.py`
- `tests/test_track_b_saas_readiness_final_audit_docs.py`
- `tests/test_track_b_controlled_final_write_sandbox_implementation.py`
- `tests/test_track_b_configuration_rule_apply_and_rerun_preview.py`
- `tests/test_track_a_internal_app_protection.py`

Plus Track-B / SaaS UI-v2 suite and `git diff --check`.

## No productive processing

Confirmed in repair modules and tests.

## No real invoice folders

Confirmed — only controlled `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/...`.

## Not SaaS-ready

This is a Track-B manual-smoke unblocker, not a SaaS readiness claim.

## Next manual smoke step

Retry PayPal config save from FA011466 with controlled target
`.../output/geplant/paypal`, then rematch and continue finalization dry-run / sandbox write.
