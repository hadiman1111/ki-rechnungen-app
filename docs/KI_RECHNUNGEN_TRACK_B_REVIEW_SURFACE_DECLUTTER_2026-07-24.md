# Track-B Review Surface Declutter (2026-07-24)

## Purpose

After the automated smoke oracle proved Track-B workflow correctness, declutter the UI-v2 review/debug surface into a usable development / product-preview review screen.

## Before / after UI problem

**Before:** Technical dump with too much debug text by default, buried decisions, hard-to-scan labels, cumbersome manual clicking. Acceptable only as developer evidence surface.

**After:** Clear review workflow with compact cards, sectioned detail view, plain-German reasons, relevant actions only, copy helpers, and technical details collapsed by default.

## New review list

Each item is a compact card showing:

- Original filename, supplier, date, amount, payment field
- Art (Rechnung / Storno), configuration, status badges
- Suggested filename, primary action, safety line

Status badges include: PayPal, Unklar, Missing payment, Not AMEX, Storno, Ready for finalization, Blocked.

## New detail sections

1. **Kurzprüfung** — recognized fields and status  
2. **Vorschlag** — suggested filename, planned target, preview note  
3. **Warum zur Prüfung?** — plain German reasons  
4. **Nächste Aktion** — only relevant buttons  
5. **Finalisierung** — readiness, dry-run / sandbox status, `final_write_allowed=false`  
6. **Technische Details** — collapsed by default  

## Technical details collapsed

Raw matching reasons, condition results, hashes/flags and debug fields live under **Technische Details** (`initially_expanded=False`).

## Copy actions

- Prüffall als Text kopieren  
- Technische Diagnose kopieren  
- Oracle-Befehl kopieren  

## Oracle command visibility

Dev-only box: **Automatischer Smoke-Test verfügbar**

```bash
KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python scripts/dev/track_b_automated_smoke_oracle.py
```

No auto-run from the UI.

## er_er note

If a suggested filename contains `_er_er_`, show:

> Hinweis: Das aktuelle technische Muster enthält einen festen er-Präfix und die Dokumentart. Das wird später vereinfacht.

Canonical filename pattern is **not** changed in this task (oracle still verifies the existing pattern).

## Safety guarantees

- No `run_once`
- No productive processing
- No production final-write
- No real invoice folders
- Originals unchanged by UI actions
- Track A UI and processing-core untouched
- No release tag changes

## No product logic change

Extraction, matching, dry-run, sandbox-final-write, safety gates, and oracle behavior remain unchanged. This task is presentation / review UX only.

## Tests

`tests/test_track_b_review_surface_declutter.py` covers compact cards, detail sections, collapsed tech details, conditional PayPal CTA, Böttcher/not-AMEX, missing payment, Storno, safety line, copy actions, empty state, er_er note, and safety/protection checks.

## Remaining UX work

- Further reduce secondary draft/remediation panels
- Visual polish / spacing in live Flet window
- Optional guided wizard for first-time PayPal rule creation
- Later: simplify `er_er` filename pattern (separate task; oracle expectations must move with it)
