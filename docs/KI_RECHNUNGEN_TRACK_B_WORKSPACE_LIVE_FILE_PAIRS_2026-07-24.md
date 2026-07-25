# Track-B Workspace Live File Pairs (2026-07-24)

## Purpose

Make the Arbeitsbereich a live working area: show input files immediately after
Eingangsordner selection, keep aligned output/proposal rows, and update proposed
filenames when „Belege jetzt prüfen“ runs — without productive processing.

## Live GUI finding

After the second UX cleanup, file pairs only appeared after a check/result.
Selecting an Eingangsordner did not show the documents in that folder.
The primary result was still too easy to read as a disconnected status box
instead of the side-by-side original ↔ proposed mapping.

## Immediate input file listing

- On Eingangsordner selection, UI-v2 lists top-level PDF basenames (read-only).
- Helper: `invoice_tool/ui_v2/workspace_input_listing.py`
- Heading: **Eingangsdateien**
- Count: „X Dateien gefunden“
- Empty: „Keine Belege im Eingangsordner gefunden.“
- Archive/technical subfolders are not entered (`archiv`, `archive`, `technisch`, …)
- No OCR, no mutation, no core runner calls, no auto-run

## Output placeholder behavior

- Heading: **Vorgeschlagene Ausgabedateien**
- Without Ausgangsordner: „Bitte Ausgangsordner wählen.“
- With Ausgangsordner, before check: „Noch nicht geprüft“
- No fake proposed filenames before a check

## Just-in-time / post-result proposal update

- Running: folder cards show activity + „Prüfung läuft…“; rows show „Wird geprüft …“
- After the bounded adapter returns: proposed filenames fill on the same rows
- True mid-run incremental UI refresh is **PARTIAL** — the start path is
  synchronous (`mark_start_checking` → adapter → refresh). No fake progress.
- Right side remains „Vorgeschlagene Ausgabedateien“ (not written files)

## Side-by-side mapping

- Stable order from input listing
- Same row: original left ↔ proposal/status right
- Marker: `workspace_live_file_pairs_v1` / `WORKSPACE_FILE_PAIR_MARKER`

## Row interactions

- Original: **Dokument anzeigen** (system open/reveal, non-mutating)
- Proposed/row: navigate to **Zur Prüfung** with document focus when possible
- Full names via tooltip / `file_pair_*_full` data markers despite truncation

## Document preview/open behavior

- Reuses review open helper; workspace marker `WORKSPACE_DOCUMENT_SHOW_MARKER`
- Non-mutating: no OCR, rename, move, delete, productive write
- Controlled input folder resolution only

## Result box removal/de-emphasis

- File-pair panel is the primary result surface (counts + safety line integrated)
- Green completed details stay collapsed under **Test & Nachweis**
- **Zur Prüfung öffnen** remains secondary (`primary=False`)

## Safety guarantees

- No productive processing
- No `run_once`
- No real invoice folders
- No production final-write (`FINAL_WRITE_ALLOWED_IN_THIS_PHASE = False`)
- Originale unverändert
- Track A / processing-core / release tags unchanged
- Listing and document open are non-mutating

## Tests

- `tests/test_track_b_workspace_live_file_pairs.py` (primary)
- Plus second UX / IA / review / oracle / Track-A protection suite

## Oracle rerun

```bash
KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python \
  scripts/dev/track_b_automated_smoke_oracle.py
```

Result: `TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS`

## No productive processing / no real invoice folders

Confirmed. Controlled tree only:
`/Users/hadi_neu/Desktop/KI-Rechnungen-Test/{input,output}`

## No Track A / Core changes

Protected Track-A UI and processing-core files were not modified.

## Release tags unchanged

- `internal-working-version-2026-07-21`
- `product-v1-local-pilot-2026-07-22`

## What remains

- True row-by-row incremental UI updates during a long adapter run (PARTIAL)
- Optional in-app PDF renderer (system open remains the safe fallback)
