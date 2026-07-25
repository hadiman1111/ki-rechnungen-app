# Track B — Review Detail Visibility & Compact Cards (2026-07-25)

## Scope

UI-v2 „Zur Prüfung“ only: scroll/anchor visibility, compact detail cards,
filename-edit in place. No Track-A, no processing-core, no productive run.

## Changes

1. Selected review item gets a stable scroll anchor (`review-detail-anchor-*`).
2. Opening a detail requests `Column.scroll_to(key=...)` so the file starts near the top.
3. Inline detail remains directly under the selected card (no distant panel).
4. Detail cards split into compact sections: Status, Empfehlung, Was muss ich entscheiden?, Was wurde erkannt?, Dateiname.
5. Filename edit shows Speichern/Abbrechen next to the field with autofocus.
6. Technical dumps stay under collapsed Test & Nachweis.

## Limitation

If Flet `scroll_to` is unavailable (headless/tests), visibility still relies on
inline detail under the selected card — no distant panel jump.

## Safety

- no run_once
- no productive final write
- no real invoice folders
- Track A / processing core untouched
