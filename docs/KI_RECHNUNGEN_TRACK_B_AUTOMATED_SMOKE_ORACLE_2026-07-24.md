# Track-B Automated Smoke Oracle (2026-07-24)

## Purpose

Replace cumbersome manual UI click verification with a **deterministic, terminal-driven smoke oracle** for the controlled Track-B workflow.

## Why manual UI smoke is replaced

The UI-v2 review/debug surface is still a development UI: too much debug text, hard navigation, unclear actions. Manual visual checking is too slow and unreliable for the product owner. The oracle proves **document correctness, PayPal matching, dry-run, and sandbox final-write** without clicking through the UI.

## Controlled input / output

- Input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`
- Output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`
- PayPal target: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/geplant/paypal`

Never real invoice folders. Never production finals.

## What the oracle verifies

1. Preflight (worktree, git, controlled folders, five PDFs, safety flags)
2. Preview / document evidence (reuse latest sufficient `preview-export-*` or block)
3. PayPal rule (`payment_field ist paypal`) — idempotent, no silent business category, no AMEX for generic card
4. Rematch: LUMITOP + 1A-Bootshop → PayPal; Böttcher card ≠ AMEX; Luxvenum + Böttcher Storno → Unklar / missing_payment_field; art=storno
5. Controlled automated review decision (`automated_smoke_review_decision=true`) — not a manual UI confirmation
6. Finalization preview (ready/blocked/still-review counts; `final_write_allowed=false`)
7. Dry-run package under controlled output only
8. Sandbox final-write under controlled output only (copy only)
9. Evidence Markdown + JSON under `automated-smoke-evidence-<timestamp>/`

## PayPal rule behavior

- Condition: `payment_field ist paypal`
- Target: controlled `.../output/geplant/paypal`
- Filename pattern: `{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf`
- Idempotent: existing active PayPal config is reused; no duplicates
- No silent business category assignment

## Document verification

| Document | Expected |
|---|---|
| FA011466.pdf | LUMITOP / paypal / PayPal |
| Rechnung RE-202605-14594.pdf | 1A-Bootshop.de / paypal / PayPal |
| 320262919974.pdf | Böttcher card / not AMEX |
| Rechnung-2026156019-102201.pdf | Luxvenum / missing payment / Unklar |
| 420260091336.pdf | Böttcher Storno / missing payment / Unklar / art=storno |

## Finalization preview / dry-run / sandbox final-write

Uses UI-v2 safe modules only:

- `finalization_preview_batch`
- `finalization_dry_run_package`
- `controlled_final_write_sandbox`

## Safety guarantees

- No `run_once`
- No productive processing
- No production final-write (`final_write_allowed_for_production=false`)
- No real invoice folders
- Originals unchanged (SHA256 before/after)
- No Track A / processing-core changes
- No release tag changes

## What remains manual / UX-only

- Visual usability of the UI-v2 review surface
- Navigation clarity / reduced debug clutter
- Human CTA discoverability in the GUI

## Not SaaS-ready

This oracle does **not** claim SaaS-ready or production-ready.

## Exact command to rerun

```bash
cd "/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python \
  scripts/dev/track_b_automated_smoke_oracle.py
```

## Status lines

- `TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS`
- `TRACK_B_AUTOMATED_SMOKE_ORACLE_PARTIAL_UI_USABILITY_ONLY`
- `TRACK_B_AUTOMATED_SMOKE_ORACLE_PARTIAL_FINALIZATION_BLOCKED`
- `TRACK_B_AUTOMATED_SMOKE_ORACLE_BLOCKED`
- `TRACK_B_AUTOMATED_SMOKE_ORACLE_FAIL_UNSAFE`
