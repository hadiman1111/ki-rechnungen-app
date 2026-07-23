# Track-B Export- und Reporting-Vorschau Polish

**Task ID:** `KI_RECHNUNGEN_TRACK_B_EXPORT_REPORTING_PREVIEW_POLISH_01`  
**Masterplan:** Prompt 5/34  
**Date:** 2026-07-22

## Purpose

Die Track-B Export-/Reporting-Vorschau an den echten Dry-Run-State aus Prompt 4/34 anbinden und ehrlich als Vorschau darstellen — ohne produktive Verarbeitung, ohne finale Dateischreibung, ohne Local-Pilot- oder SaaS-Ready-Claim.

## What changed

- `invoice_tool/ui_v2/export_reporting.py` — Preview-Report-Modell mit Sandbox-Pfaden, Profil/Konfiguration, Counts, Safety-Proof, Warnungen, Preview-Text
- `invoice_tool/ui_v2/pages/workspace.py` — Export-Vorschau-Panel nutzt denselben Dry-Run-State inkl. Kontext
- `invoice_tool/ui_v2/pages/review.py` — leichte Preview-Summary ohne Final-Aktion
- Tests: `tests/test_ui_v2_export_reporting_preview_polish.py`

## Preview report behavior

`build_export_preview_report(ProcessingRunState, ExportPreviewContext?)` liefert:

| Feld | Inhalt |
|------|--------|
| Titel | Export-Vorschau |
| run_id / status | aus Dry-Run-State |
| Sandbox Ein-/Ausgang | aus Workspace-Kontext |
| Profil/Konfiguration | aus Workspace-Selektion |
| Counts | erkannt / Prüfung / Fehler / Warnungen / geplante Ziele |
| Safety-Proof | Originale unverändert · Produktiv gesperrt · Export Vorschau |
| Zielzeilen | preview-only, nicht angewendet |
| Review-/Fehler-/Warnungs-Summary | ehrlich aus State |
| Kein Lauf | „Noch kein Sandbox-Lauf vorhanden.“ — keine Fake-Zeilen |

Leere, all-review-, gemischte und fehlgeschlagene Läufe werden über `outcome_kind` ehrlich abgebildet. Optionaler In-Memory-Text via `render_export_preview_text`. Dateischreiben nur auf expliziten lokalen Pfad (JSON/CSV), nie in Originalordner.

## Preview-only wording

- Export-Vorschau
- Keine Dateien wurden final geschrieben.
- Originale unverändert.
- Produktive Verarbeitung gesperrt.
- Zielpfade sind Vorschläge aus dem Sandbox-Dry-Run.
- Diese Vorschau ersetzt keinen finalen Produktivlauf.
- Local-Pilot-Ready / SaaS-Ready explizit „nicht erreicht“

## Workspace integration

- Abschnitt „Export-Vorschau“ liest `processing_run_state`
- Zeigt Sandbox-Pfade, Profil/Konfiguration, Counts, Safety-Proof
- Export-Button nur bei vorhandenem Sandbox-Lauf
- `apply_workspace_export_preview` schreibt mit Kontext, startet keine Verarbeitung

## Review integration

- `ReviewPageVM.export_preview_summary` zeigt kompakte Vorschau-Counts
- `final_actions_blocked=True`, Aktionen disabled
- Keine Übernehmen-/Buchen-/Final-Aktion

## Safety proof

Sicherheitsnachweis bleibt Teil von Report, Workspace-Panel und Review-Details.

## What remains for Prompt 6/34

Local-Pilot Acceptance Gate — produktive Freigabe, echte Pilotkriterien, Status `LOCAL_PILOT_READY` nur nach Gate.

## Why local pilot is still pending

Kein Acceptance-Gate, keine produktive Verarbeitung, keine Originalordner-Mutation, keine final geschriebenen Rechnungen, kein Pilot-/SaaS-Claim.

## Tests

- `tests/test_ui_v2_export_reporting_preview_polish.py`
- Bestehende Mapping-/Bridge-/Workspace-/Core-Dry-Run-/Track-A-Schutz-Tests
- Vollständige `tests/test_ui_v2_*.py` und `tests/test_saas_ui_v2_*.py`

## Product status after task

`TRACK_B_EXPORT_REPORTING_PREVIEW_AVAILABLE_PENDING_ACCEPTANCE_GATE`
