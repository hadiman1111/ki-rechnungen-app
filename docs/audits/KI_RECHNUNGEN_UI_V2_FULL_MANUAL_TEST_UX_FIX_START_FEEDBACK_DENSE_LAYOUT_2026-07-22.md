# KI_RECHNUNGEN_UI_V2_FULL_MANUAL_TEST_UX_FIX_START_FEEDBACK_DENSE_LAYOUT_2026-07-22

## 1. Task ID

`KI_RECHNUNGEN_UI_V2_FULL_MANUAL_TEST_UX_FIX_START_FEEDBACK_DENSE_LAYOUT_01`

## 2. User observation

Nach Ordnerwahl und Klick auf „Sandbox-Lauf starten“:

- kein sichtbarer Verarbeitungs-/Ladezustand
- Ergebnisbereich blieb leer
- Workflow-Karte zeigte dauerhaft lange Erklärtexte
- Zeilen-/Kartenabstände zu groß
- UI wirkte wie Dokumentation statt Arbeitsfläche

## 3. Diagnosis

1. **Übermäßige Hilfetexte:** Workspace `compact_hint_block` mit vielen Sandbox-Zeilen; Settings/Review/Profile mit großen Banner-/Hint-Blöcken; Export mit 6 permanenten `helper_text`-Zeilen.
2. **Großes Spacing:** `page_scaffold` 24px, Header-Margin 28px, empty-state große Padding.
3. **Aus Default-Ansicht zu entfernen:** Workflow-Bullet-Listen, wiederholte Safety-Sätze, SaaS-/Dry-Run-Langtexte, Entwickler-Next-Steps.
4. **Nach Start-Klick:** `apply_start_processing` → Adapter → unbound Core → Feedback nur als langer Alert weit vom CTA.
5. **Zustände:** `idle/blocked/failed/completed` vorhanden, aber kein sichtbares `checking`.
6. **Progress/Motion:** kein Spinner, kein Zwischenzustand am CTA.
7. **Warum „nichts passiert“:** kein sofortiger Statuswechsel nahe am Button; Ergebnis bleibt leer weil Core unbound.
8. **UI-only:** Feedback-Zustand, Verdichtung, Collapse von Erklärungen.
9. **Core-Bridge erforderlich:** echte Sandbox-/Dry-Run-Ausführung (`sandbox_core_runner` unbound).

## 4. Start-button feedback

- Neuer Interaktionsstatus: `idle → checking → blocked|sandbox_not_connected|completed|failed`
- Sofort: „Prüfung läuft …“ via `mark_start_checking` + Refresh vor Adapterlauf
- Endzustand prominent über `compact_run_status_panel`
- Primärgrund sichtbar; Sekundärdetails hinter „Details anzeigen“
- Keine Fake-Ergebnisse, keine Originalordner-Nutzung

## 5. Workspace

- Workflow-Bullet-Block entfernt
- Kompaktes Laufstatus-Panel neben CTA-Fluss
- Empty-State: „Noch kein Laufergebnis.“
- Fünf-Fragen-Bericht als `dense_card` + `compact_info_row`
- Export-Disclaimer kompakt; Langtexte collapsed

## 6. Profiles

- Keine SaaS-Entwurfs-Wording-Regression
- Eine kompakte Hinweiszeile
- Policy-Langtexte hinter Details

## 7. Configurations

- Eine kompakte Hinweiszeile statt großer Hint-Rows
- Policy-Langtexte hinter Details

## 8. Review

- Empty-State: „Keine Prüffälle vorhanden.“
- Banner/Langtexte collapsed

## 9. Settings

- Eine Produktstatus-Zeile: „Lokale Pilotversion · nicht SaaS-ready · produktiv gesperrt“
- Capability-Matrix bleibt; Langtexte hinter Details

## 10. Export/Reporting

- Kompakter Disclaimer: „Exportvorschau · kein produktiver DATEV-/Cloud-Export“
- Ausführliche Export-Hinweise nur in Details

## 11. Explanations moved/removed from default UI

Entfernt/collapsed:

- Sandbox-/Workflow-Bullet-Wand
- Onboarding-Checklist als Default
- Mehrfach wiederholte Export-/Safety-Sätze
- Review-/Settings-Langbanner
- Draft-List Import/Export/Delete-Hilfen (collapsed)

## 12. Compact safety semantics remaining

Chips/Statuszeilen behalten:

- lokale Pilotversion
- Sandbox/kopierte Daten
- produktiv gesperrt
- Originalordner geschützt
- Export nur Vorschau
- nicht SaaS-ready
- Dateiname ≠ Wahrheit (in Details)
- unklare Fälle zur Prüfung

## 13. Real processing wired?

Nein.

## 14. Exact blocker

`CORE_BRIDGE_REQUIRED_FOR_REAL_SANDBOX_EXECUTION`  
(`sandbox_core_runner_unbound` / Track-B Sandbox nicht sicher angebunden)

## 15. Files changed

- `invoice_tool/ui_v2/components.py`
- `invoice_tool/ui_v2/state.py`
- `invoice_tool/ui_v2/pages/workspace.py`
- `invoice_tool/ui_v2/pages/profiles.py`
- `invoice_tool/ui_v2/pages/configurations.py`
- `invoice_tool/ui_v2/pages/review.py`
- `invoice_tool/ui_v2/pages/settings.py`
- `invoice_tool/ui_v2/review_workflow.py`
- `invoice_tool/ui_v2/export_reporting.py`
- `invoice_tool/ui_v2/saas_profile_draft_list_view.py`
- `tests/test_ui_v2_manual_test_ux_dense_layout.py` (neu)
- weitere `tests/test_ui_v2_*.py` Anpassungen
- dieses Audit-Dokument

## 16. Tests run and results

Focused suite: passed  
Full Track-B UI-v2 + SaaS UI-v2: **454 passed, 44 skipped**

## 17. No Track A change

Bestätigt.

## 18. No processing-core change

Bestätigt.

## 19. No productive processing

Bestätigt.

## 20. No original folders touched

Bestätigt.

## 21. Manual next test instruction

1. Track-B UI-v2 starten.
2. Eingangs- und Ausgabeordner wählen.
3. „Sandbox-Lauf starten“ klicken.
4. Erwartung: sofort „Prüfung läuft …“, danach kompakt „Sandbox nicht verbunden“ / Blockiert mit Primärgrund; Details einklappbar; kein Fake-Ergebnis; keine Originalmutation.

`STOPPED_AFTER_KI_RECHNUNGEN_UI_V2_MANUAL_TEST_UX_FIX_START_FEEDBACK_DENSE_LAYOUT — AWAITING_MANUAL_RETEST`
