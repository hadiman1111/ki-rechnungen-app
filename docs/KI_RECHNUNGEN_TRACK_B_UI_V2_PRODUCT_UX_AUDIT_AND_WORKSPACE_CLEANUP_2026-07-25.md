# Track-B UI-v2 Product UX Audit and Workspace Cleanup (2026-07-25)

## Purpose

Make the Arbeitsbereich a simple operational surface again: profile/config summary, folder cards with file pairs, primary CTA, optional compact status — without developer/test/evidence sections competing with the product flow. Fix output-placeholder dead ends and filename-edit focus.

## Product-owner live GUI findings

- Workspace still felt like a second diagnostic/configuration page.
- Output placeholders such as „Noch nicht geändert“ were clickable and led to dead ends.
- „Dateiname bearbeiten“ did not keep the edit field reliably in view.
- Developer / Test & Nachweis / Letzte Ergebnisse / detailed config tabs competed with the primary workflow.

## Workspace scope decision

Primary workspace ends after:

1. Header + flow breadcrumb  
2. Profil | Konfiguration summary  
3. Eingangs-/Ausgangsordner with file pairs  
4. „Belegnamen jetzt ändern“ + safety line  
5. Compact status (optional)  
6. Secondary „Zur Prüfung öffnen“

Developer/test/evidence surfaces render only when Track-B dev defaults are active (`show_dev_surfaces`).

## What was removed/hid from workspace

| Surface | Decision |
|--------|----------|
| Entwickler / Diagnose | Hidden from primary; only under `show_dev_surfaces` |
| Test & Nachweis | Hidden from primary; only under `show_dev_surfaces` |
| Verbose completed run details | Moved to advanced/dev |
| Export/report panels | Advanced/dev only |
| Zielordner / Letzte Ergebnisse tabs | Advanced/dev only |

## „Letzte Ergebnisse“ decision

Removed from primary workspace. Replaced by a short compact status line, e.g.:

- `5 Dokumente gefunden · 0 geändert · 5 noch nicht geändert`
- after run: `5 Dokumente geprüft · 2 Vorschläge · 3 zur Prüfung`

Full result lists remain available only in the folder cards (file pairs) and under developer surfaces when enabled.

## Configuration-details placement

Detailed destination/config listings stay under **Konfigurationen** (and advanced workspace tabs when `show_dev_surfaces`). Workspace shows only the active profile/config summary with „Bearbeiten“.

## Output placeholder clickability fix

- Placeholders (`Noch nicht geändert`, `Noch kein Vorschlag`, `Bitte Ausgangsordner wählen`, checking) are **not** clickable.
- No pointer cursor, no hover action, no action icon on placeholders.
- Valid proposed/review rows are clickable only when a source/detail target exists.
- Action opens „Zur Prüfung“ for the source (proposal preview — no fake file open).

## Output hover/action icon behavior

- Actionable rows: `MouseCursor.CLICK`, subtle hover background, right-aligned `FACT_CHECK_OUTLINED` icon.
- Tooltips: „Vorschlag ansehen“ / „Zur Prüfung öffnen“ / „Datei anzeigen“ (when a real file exists).

## Filename edit focus/scroll fix

In „Zur Prüfung“, „Dateiname bearbeiten“ now replaces the filename preview **in place** in the same detail section, with `autofocus=True` and focus/visibility markers. No second distant form below the actions.

## Settings / developer diagnosis decision

- Nav label remains **Entwickler / Diagnose** (not „Erweiterte Einstellungen“).
- Collapsed under ENTWICKLER in the sidebar.
- Settings page is honestly labeled as diagnosis — short safety summary + collapsed diagnostic details. No empty user-settings façade.

## Full UI-v2 UX audit findings

### Fixed in this task

1. Dev/Test/Evidence no longer primary workspace content  
2. Letzte Ergebnisse de-emphasized / removed from primary  
3. Detailed config lists not primary in workspace  
4. Output placeholders non-clickable  
5. Output action icon + hover only when actionable  
6. Filename edit in place with focus marker  
7. Settings/dev labeled honestly as Entwickler / Diagnose  

### Follow-up (not fixed)

1. Remaining „Sandbox“ wording in some blocked/status messages (internal honesty path) — keep product CTA clean; full copy sweep later  
2. Stricter hide of ENTWICKLER nav unless `KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1` (currently collapsed always; still reachable)  
3. Live GUI visual QA of hover on all Flet versions  
4. Optional scroll-into-view API if autofocus alone is insufficient on some platforms  

## Safety guarantees

- No productive processing  
- No `run_once`  
- No real invoice folders  
- No production final-write  
- Originals unchanged  
- Track A untouched  
- Processing core untouched  
- Release tags unchanged  
- Document preview / output actions non-mutating  

## Tests

`tests/test_track_b_workspace_product_cleanup.py` plus related Track-B UI-v2 suites (see audit).

## Oracle

Result: `TRACK_B_AUTOMATED_SMOKE_ORACLE_PASS`

Command:

`KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python scripts/dev/track_b_automated_smoke_oracle.py`

## Next step

Product-owner live GUI pass on Arbeitsbereich: confirm no primary Dev/Test sections, placeholders not clickable, filename edit stays in view. Then continue Track-B polish only if new PO findings appear.
