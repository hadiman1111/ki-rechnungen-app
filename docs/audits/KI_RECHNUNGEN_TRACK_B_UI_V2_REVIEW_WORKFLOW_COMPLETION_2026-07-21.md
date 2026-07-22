# KI-Rechnungen Track B UI-v2 — Review Workflow Completion

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_REVIEW_WORKFLOW_COMPLETION_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Review Workflow Completion  
**Masterplan position:** Prompt 3 of 12 bis Produktversion 1 / lokale Pilotfähigkeit

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_REVIEW_WORKFLOW_COMPLETION_01`

## 2. Masterplan position: Prompt 3 of 12

Dieses Task vervollständigt den Track-B UI-v2 Prüfworkflow („Zur Prüfung“),
damit Prüffälle aus `ProcessingRunState.review_items` ehrlich und getrennt
von Ergebnissen/Fehlern angezeigt werden — ohne Dateimutationen und ohne
produktive Ausführung.

## 3. Purpose

1. Prüffälle aus `ProcessingRunState` anzeigen  
2. Grund / Nachweis / nächsten Schritt erklären  
3. Review, Results und Errors getrennt halten  
4. Nur sichere, deaktivierte/readiness-only UI-Aktionen  
5. Keine Persistenz manueller Entscheidungen  
6. Keine Dateimutationen / kein PDF-Processing  
7. Produktive Ausführung blockiert halten  
8. Track A unverändert lassen  

## 4. What changed

Neu:

- `invoice_tool/ui_v2/review_workflow.py` — reine View-Model-Helfer  
- `tests/test_ui_v2_review_workflow.py`  
- dieses Audit-Dokument  

Aktualisiert:

- `invoice_tool/ui_v2/pages/review.py` — nutzt Review-Queue-VM, ehrlicher
  Leerzustand, Trennungshinweise, deaktivierte Prüfaktionen  

## 5. Review item model / view model behavior

Modul: `review_workflow.py`

- `build_review_item_view_model(...)` mappt nur gelieferte
  `ProcessingReviewItem`-Felder (+ optionale `source_run_id` vom Lauf)  
- `build_review_queue_view_model(...)` baut die Warteschlange ausschließlich
  aus `ProcessingRunState.review_items`  
- Generische Felder: Dokumentlabel/ID, Grund, Status, Nachweis,
  nächster Schritt, Lauf-ID, Severity/Status  
- Keine erfundenen Vendor-/Zahlungs-/Konto-/Business-/Private-Felder  
- Keine Filename-as-truth-Inferenz  

## 6. Review page behavior

- Zeigt Review-Count und generische Felder je Prüffall  
- Zeigt Grund / Nachweis / nächsten Schritt, wenn vorhanden  
- Zeigt explizit: keine Dateiänderung aus dieser Ansicht  
- Kein Dateiöffnen, kein PDF-Processing, kein Ordner-Scan  
- Keine produktive Ausführungs-Aktion  

## 7. Empty state behavior

Ohne Prüffälle:

- „Noch keine Prüffälle vorhanden.“  
- „Prüffälle entstehen erst aus einem echten Verarbeitungslauf.“  
- „Diese Ansicht verändert keine Dateien.“  

Keine Fake-Rechnungszeilen, keine privaten Defaults.

## 8. Review / result / error separation

- Review-Liste enthält nur `review_items`  
- Erfolgreiche Results werden nicht als Prüffälle gerendert  
- Errors werden nicht in die Review-Liste gemischt  
- Optionaler Hinweis:
  „Fehler werden getrennt von Prüffällen geführt.“  
  bzw. Results-Trennungshinweis, wenn Results vorhanden  

## 9. Workspace review count behavior

Unverändert ehrlich über `build_workspace_readiness_display_vm` /
`build_run_result_display_shell`:

- `result_count`, `review_count`, `error_count` getrennt  
- Hinweis „Details unter Zur Prüfung.“ wenn Review-Items existieren  
- keine Fake-Counter, keine Auto-Navigation  

## 10. Optional review action behavior

Deaktivierte Readiness-Shells:

- „Als geprüft markieren“ — noch nicht verbunden  
- „Entscheidung später speichern“ — noch nicht verbunden  
- „Nachweis prüfen“ — nur Hinweis, keine Dateiöffnung  

Regeln: keine Persistenz, keine Dateimutationen, kein PDF-Open,
keine produktive Aktion.

## 11. Why this does not process real PDFs

- Review-Seite und View-Models importieren keinen Processing-Core  
- Keine OCR/AI-Aufrufe  
- Keine Datei-IO außer Anzeige bereits gelieferter State-Felder  
- Aktionen sind disabled und ohne Persistenz-Handler  

## 12. Why this does not touch real invoice folders

- Kein Folder-Scan / Folder-Create  
- Keine Pfad-Defaults (kein Desktop/`/Users`/private Tokens)  
- Anzeige nur aus injiziertem `ProcessingRunState`  

## 13. Why this does not touch Track A

Nicht geändert / nicht staged:

- `app_main.py`, `app_internal_launcher.py`  
- Legacy-UI (`gui`, `ui_shell`, `ui_workspace`, `ui_review`, …)  
- Known legacy dirty files bleiben lokal unstaged  

## 14. Why this does not touch processing-core

Nicht geändert:

- `invoice_tool/processing.py`  
- `invoice_tool/routing.py`  
- `invoice_tool/routing_guards.py`  
- `invoice_tool/classification.py`  
- `invoice_tool/target_routing.py`  
- `invoice_tool/run.py`  

## 15. Tests added/updated

Neu:

- `tests/test_ui_v2_review_workflow.py`

Bestehend (weiter grün, unverändert oder kompatibel):

- `tests/test_ui_v2_review_navigation.py`  
- `tests/test_ui_v2_run_result_display_shell.py`  
- `tests/test_ui_v2_workspace_processing_contract.py`  
- `tests/test_ui_v2_sandbox_execution_wiring.py`  

## 16. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_review_navigation.py \
  tests/test_ui_v2_review_workflow.py \
  tests/test_ui_v2_run_result_display_shell.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_sandbox_execution_wiring.py
→ 70 passed

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
→ 283 passed, 44 skipped
```

## 17. Generalization confirmation

- keine Hadi/SOMAA/Bismarck/AMEX/voba Defaults  
- keine Desktop/`/Users`-Pfad-Defaults  
- kein Filename-as-truth  
- keine Fake Payment/Account/Business-Klassifikation  
- keine Fake-Prüffälle  
- keine Fake-Processing-Results  
- kein produktiver Execution-Toggle  
- kein Folder-Scan / Folder-Create  
- keine echte PDF-Verarbeitung  
- UI-Wording generisch  
- Track A unberührt  
- Processing/Routing/Classification-Core unberührt  

## 18. Current progress

| Item | Status |
|---|---|
| Prompt 3/12 complete | **yes** |
| Remaining prompts | **9** |

## 19. Remaining gaps

- profile/policy completion  
- export/reporting completion  
- Track A regression gate  
- synthetic E2E  
- copied-real-data validation  
- quality fixes  
- packaging/onboarding  
- pilot acceptance  
- final release gate  

## 20. Exact next task recommendation

**`KI_RECHNUNGEN_TRACK_B_UI_V2_PROFILE_POLICY_COMPLETION_01`**  
(Masterplan Prompt 4/12: Profile/Policy-Vervollständigung für Track-B UI-v2)

Alternativ, falls PO Export/Reporting priorisiert:

**`KI_RECHNUNGEN_TRACK_B_UI_V2_EXPORT_REPORTING_COMPLETION_01`**
