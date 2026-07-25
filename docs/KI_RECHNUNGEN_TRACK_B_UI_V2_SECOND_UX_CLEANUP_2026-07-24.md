# Track-B UI-v2 Second UX Cleanup (2026-07-24)

## Purpose

Make UI-v2 feel like a simple product workflow, not an internal development dashboard — based on live product-owner GUI review after the Information Architecture Cleanup.

## Product-owner live GUI findings

- Menu row spacing too large; „Erweiterte Einstellungen“ looked like user settings but only held diagnostics
- Profile and configuration shown as separate large blocks instead of one summary band
- Folder buttons did not adapt wählen/ändern; run CTA buried „nur Vorschau“ in the button label
- Green completed/details box dominated instead of original ↔ proposed filename pairs
- Profile/Configuration pages still showed drafts, import/export and internal hints as primary
- Review used „Fälle“, duplicate short lists, supplier-only names, and no document open action

## Settings / advanced decision

No real user-editable settings exist.  
„Erweiterte Einstellungen“ was renamed to **Entwickler / Diagnose**, moved under collapsed secondary nav group `ENTWICKLER`, and is not part of the core workflow.

## Compact menu result

Sidebar nav rows use compact padding/density (`MENU_COMPACT_ROW_MARKER`). Developer diagnosis remains accessible but collapsed by default.

## Workspace profile/config shared frame

One shared summary frame (`WORKSPACE_SHARED_SUMMARY_MARKER`) with two equal columns and identical **Bearbeiten** buttons (navigate to Profile / Konfigurationen).

## Folder wählen/ändern behavior

- Empty → „Eingangsordner wählen“ / „Ausgangsordner wählen“
- Selected → „… ändern“, green checkmark, distinct input/output colors
- Display path may truncate; full path remains via tooltip/`full=` data

## Run CTA result

Section **Belege prüfen**, primary CTA **Belege jetzt prüfen**, helper **Nur Vorschau — Originale bleiben unverändert.**  
Running: „Prüfung läuft…“ + folder activity marker. No auto-run.

## Workspace paired file list result

Under the CTA: **Eingangsdateien** | **Vorgeschlagene Ausgabedateien** on the same row.  
Placeholder before first result: **Noch kein Ergebnis vorhanden.**  
Green completed/details box is secondary/collapsed only.

## Profile simplification result

Slim active-profile summary band with „aktiv = wird bei der Prüfung verwendet“.  
Primary: profile list + **Profil erstellen**. Drafts/import/export under collapsed advanced.

## Configuration simplification result

Mirrors profile structure. **Neue Konfiguration erstellen** / **Konfiguration erstellen**.  
Edit form without side scrollbar. Drafts/import/export collapsed.

## Review cleanup result

- No internal sandbox heading as primary
- „Dokumente“ instead of „Fälle“ as primary list wording
- Duplicate short text lists removed from primary
- Full original filename + secondary supplier/date/amount
- Side-by-side Originaldatei / Vorgeschlagener Dateiname; expand detail below
- Clean filenames (no REVIEW_REQUIRED / SUGGESTED)

## Document preview/open behavior

**Dokument anzeigen** opens the controlled input file with the system viewer when resolvable.  
Non-mutating (`REVIEW_DOCUMENT_PREVIEW_MARKER`). No OCR, rename, move, or productive write.  
If the file is missing: clear feedback + marker (PARTIAL for in-app PDF rendering — system open fallback).

## Clean filename result

`clean_user_facing_filename` remains the user-facing display path for proposed names.

## Safety guarantees

- No productive processing / no `run_once`
- No real invoice folders
- No production final-write
- Track A / processing-core / release tags unchanged
- Oracle still passes

## Tests

`tests/test_track_b_ui_v2_second_ux_cleanup.py` (66 checks) plus prior Track-B review/IA/oracle/protection suite and UI-v2/SaaS UI-v2 suites.

## Oracle rerun

`KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python scripts/dev/track_b_automated_smoke_oracle.py`

## What remains

- True in-app PDF preview panel (system open is the safe fallback)
- Optional further declutter of destination/result tabs under Test & Nachweis
- Live PO visual confirmation of the paired file list after push
