# Track-B Simple User Review Mode (2026-07-24)

## Purpose

After the automated smoke oracle proved Track-B workflow correctness and the
review surface was decluttered, turn the remaining developer/review dump into a
**simple user review mode**.

The user should not need to read `payment_field`, `matching_reason`,
`final_write_allowed`, configuration IDs, or other technical flags.

## User questions (primary surface)

1. **Was wurde erkannt?** — Lieferant, Datum, Betrag, Zahlungsart, Dokumentart  
2. **Was ist unklar?** — plain German reasons  
3. **Welcher Dateiname wird vorgeschlagen?** — preview filename only  
4. **Was muss ich entscheiden?** — one decision prompt + relevant actions  
5. **Wird etwas final geschrieben?** — **Nein — nur Vorschau/Sandbox**  
6. **Welche Fälle sind bereit?** — ready-case summaries  
7. **Welche Fälle bleiben zur Prüfung?** — still-in-review summaries  

Technical details, oracle command, dry-run / sandbox CTAs and diagnosis copy
remain available under **Technische Details** / optional advanced tools —
collapsed by default.

## What stays unchanged

- Terminal oracle remains the fachliche regression gate  
- Extraction / matching / dry-run / sandbox-final-write / safety gates  
- No productive processing  
- No real invoice folders  
- No Track-A UI or processing-core changes  
- No release tag changes  

## Badges (German)

| Badge | Meaning |
|---|---|
| PayPal | PayPal detected / PayPal guidance |
| Unklar | Needs review |
| Zahlung unklar | Payment not safely recognized |
| Keine AMEX | Card without AMEX proof |
| Storno | Credit note |
| Bereit | Ready for later preview finalization |
| Blockiert | Blocked |

## Layout marker

`track_b_simple_user_review_mode_v1`

## Tests

`tests/test_track_b_simple_user_review_mode.py` plus the existing declutter and
oracle suites.

## Product status after task

`TRACK_B_SIMPLE_USER_REVIEW_MODE_READY`
