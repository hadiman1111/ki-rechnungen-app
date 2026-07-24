# Track-B Filename Pattern Simplification (2026-07-24)

## Purpose

Remove the confusing double `er_er` segment from Track-B/UI-v2 suggested filenames.
Document type (`{art}`) must appear only once.

## Old pattern

```text
{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf
```

## Problem with er_er

The pattern contained a fixed literal `er` **plus** the `{art}` placeholder.
For normal Eingangsrechnung, `{art}` is also `er`, producing names like:

```text
2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf
```

Storno became `…_er_storno_…`, which also looked redundant.

## New pattern

```text
{invoice_date}_{art}_{supplier}_{amount}_{payment_field}.pdf
```

## Examples before / after

| Case | Before | After |
|------|--------|-------|
| LUMITOP | `2026-05-11_er_er_LUMITOP_476,00_paypal.pdf` | `2026-05-11_er_LUMITOP_476,00_paypal.pdf` |
| 1A-Bootshop | `2026-05-15_er_er_1A-Bootshop.de_105,75_paypal.pdf` | `2026-05-15_er_1A-Bootshop.de_105,75_paypal.pdf` |
| Böttcher card | `2026-05-23_er_er_Böttcher_AG_84,39_card.pdf` | `2026-05-23_er_Böttcher_AG_84,39_card.pdf` |
| Luxvenum missing payment | `2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf` | `2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf` |
| Böttcher Storno | `2026-06-18_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf` | `2026-06-18_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf` |

## Storno behavior

Storno uses `art=storno` once:

```text
2026-06-18_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf
```

Not `…_er_storno_…`.

## PayPal behavior

PayPal rule creation / oracle PayPal draft uses the simplified pattern.
Output examples:

```text
2026-05-11_er_LUMITOP_476,00_paypal.pdf
2026-05-15_er_1A-Bootshop.de_105,75_paypal.pdf
```

Matching semantics, payment detection, and PayPal condition logic are unchanged.

## Missing payment behavior

Missing payment marker remains `FEHLT_payment_field`:

```text
2026-05-11_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf
```

## Oracle update

Automated smoke oracle expected filenames use the simplified pattern and must still
end with `TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS`.

## Review UI

`_er_er_` is **not** current expected behavior.
If a legacy preview artifact still contains `_er_er_`, the review surface shows:

> Altes technisches Muster aus früherem Preview-Export.

## Safety guarantees

- Originals unchanged
- No productive final-write
- No `run_once`
- No real invoice folders
- Sandbox / controlled output only
- Track A UI and processing-core untouched
- Track-A `SOMAA_CANONICAL_FILENAME_TEMPLATE` in `configuration_model.py` unchanged
- No release tag changes

## No product logic change beyond filename pattern

Extraction, payment detection, matching semantics, Dry-Run/Sandbox safety, and
productive gates remain unchanged. Only the Track-B/UI-v2 filename pattern
(and its review/oracle expectations) are simplified.

Legacy stored patterns that still equal
`{invoice_date}_er_{art}_{supplier}_{amount}_{payment_field}.pdf`
are normalized to the simplified pattern when loaded/used in UI-v2.

## No productive processing

This task does not enable productive processing or write production final files.

## No real invoice folders

Controlled folders only (`/Users/hadi_neu/Desktop/KI-Rechnungen-Test/...`).

## Not SaaS-ready

Filename declutter for Track-B local/dev preview only — not a SaaS readiness claim.

## Remaining UX work

- Further review-surface polish beyond filename clarity
- Optional migration UX if old preview-export folders are shown next to new suggestions
- Keep terminal oracle as regression gate after UX changes
