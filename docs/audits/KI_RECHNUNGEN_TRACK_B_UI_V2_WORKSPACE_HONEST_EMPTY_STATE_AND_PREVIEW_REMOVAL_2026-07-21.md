# KI_RECHNUNGEN_TRACK_B_UI_V2_WORKSPACE_HONEST_EMPTY_STATE_AND_PREVIEW_REMOVAL_2026-07-21

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_WORKSPACE_HONEST_EMPTY_STATE_AND_PREVIEW_REMOVAL_01`

## 2. Purpose

Track-B-only: UI-v2 Workspace ehrlich machen — Preview/AMEX/Privat-Mocks entfernen, Empty States und klare „noch kein Lauf“-Kommunikation. Kein Processing-Core, kein Track A, keine produktive Verarbeitung.

## 3. Files changed

| Path | Change |
|------|--------|
| `invoice_tool/ui_v2/pages/workspace.py` | Preview/Mocks entfernt; ehrlicher Empty State |
| `invoice_tool/ui_v2/rendering_checks.py` | Workspace-Assertions an Empty State angepasst |
| `tests/test_ui_v2_workspace_empty_state.py` | Neu: Non-GUI Honesty-Tests |
| `tests/test_ui_v2_rendering_recovery.py` | Workspace-Erwartungen angepasst |
| `tests/test_ui_v2_design_fidelity.py` | Workspace-Erwartungen angepasst |
| `docs/audits/KI_RECHNUNGEN_TRACK_B_UI_V2_WORKSPACE_HONEST_EMPTY_STATE_AND_PREVIEW_REMOVAL_2026-07-21.md` | Dieses Audit |

## 4. Removed / reworded preview / mock / private-looking runtime content

### Occurrence classification (Track-B inspect)

| Location | Markers | Class |
|----------|---------|-------|
| `invoice_tool/ui_v2/pages/workspace.py` (vorher) | `_PREVIEW_*`, AMEX, Privat, American Express, Desktop-Pfad, fake result rows | **A. MUST_REMOVE_FROM_RUNTIME_UI** — entfernt |
| `invoice_tool/ui_v2/saas_profile_*.py` | SOMAA/Hadi/AMEX als **Block-Marker** gegen private Defaults | **E. FALSE_POSITIVE** (Guard, kein Prefill) |
| `invoice_tool/ui_v2/filename_editor.py` / adapters | `preview_filename` = Dateinamenmuster-Beispiel | **D. NEEDS_GENERIC_REWORDING** (nicht Workspace-Lauf; unverändert in diesem Task) |
| `invoice_tool/ui_v2/pages/configurations.py` | Label „Beispiel“ für Filename-Pattern | **D / E** — Pattern-Beispiel, kein Lauf-Ergebnis |
| `invoice_tool/ui_v2/rendering_checks.py` | SOMAA/Privat/AMEX in Profil-/Konfig-Fidelity-Checks | **D** — Workspace-Teil angepasst; Profil/Konfig-Checks bleiben lokaldatenabhängig |
| `tests/test_saas_ui_v2_*.py` | PRIVATE_MARKERS in Assertions | **B. OK_IN_TEST_ONLY** |
| Dieses Audit | Marker-Namen zur Dokumentation | **C. OK_IN_AUDIT_OR_DOC_ONLY** |

### Removed from runtime workspace

- `_PREVIEW_INPUT_PATH` (`~/Desktop/Programm Belegerfassung/...`)
- `_PREVIEW_MAPPINGS` (amex/Privat/Event-Production Fake-Zuordnungen)
- `_PREVIEW_RESULTS` (fake invoice rows inkl. American Express / Privat)
- `use_preview`-Pfad inkl. erfundenen OK/Fehler-Zählern (12/4)
- Nutzung von `list_input_pdf_filenames` zur Preview-Zuordnung (filename-as-truth)

## 5. New empty-state behavior

Wenn **keine** echten UI-v2-Run-Ergebnisse (`workspace.results`) vorliegen:

- Inline-Warnung: „Kein Lauf gestartet. Keine Ergebnisse vorhanden.“
- Tab „Letzte Ergebnisse“: Empty State mit
  - Titel: „Noch kein Verarbeitungslauf in dieser Oberfläche.“
  - Detail zu Lauf-Adapter, echtem Lauf, Prüfbereich
- Keine Fake-Rechnungszeilen, keine Fake-Zahlungsarten, keine privaten Pfade
- Keine OK/Fehler-Badges und kein „Neu starten“, solange kein echter Lauf vorliegt
- Mapping-Liste nur aus echten erfolgreichen Ergebnissen

Reine Hilfs-API für Tests: `workspace_honesty_copy(has_real_results=...)`.

## 6. Tests added / updated

- **Neu:** `tests/test_ui_v2_workspace_empty_state.py`
  - keine Preview/Private-Marker im Workspace-Source
  - Empty-State-Copy sagt klar: kein Lauf
  - keine Verarbeitungs-Claims ohne Run-Daten
  - kein Import von Processing-Core / Track A
  - Import lädt Processing-Core nicht nach
- **Aktualisiert:** `tests/test_ui_v2_rendering_recovery.py`, `tests/test_ui_v2_design_fidelity.py`

## 7. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_workspace_empty_state.py \
  tests/test_saas_ui_v2_classification_policy.py \
  tests/test_saas_product_model.py \
  tests/test_saas_ui_v2_profile_store.py \
  tests/test_saas_ui_v2_profile_state.py \
  tests/test_saas_ui_v2_profile_surface.py
→ 55 passed

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
→ 114 passed, 44 skipped
```

Kein GUI-Window-Test, kein Build, keine PDF-Verarbeitung.

## 8. Generalization confirmation

Workspace zeigt keine Hadi/SOMAA/Bismarck/AMEX/voba/Privat-Preview-Laufdaten und keine lokalen Desktop-Pfade als Demo-Ergebnisse. Empty States sind generisch für das allgemeine Produkt (UI-v2).

## 9. Track A not touched confirmation

Nicht geändert: `app_main.py`, `app_internal_launcher.py`, `invoice_tool/gui.py`, `ui_shell.py`, `ui_workspace.py`, Legacy-UI-Module.

Bekannte lokale Dirty-Dateien bleiben unstaged: `invoice_tool/ui_profile_dialog.py`, `invoice_tool/ui_document_rules.py`.

## 10. No processing-core change confirmation

Nicht geändert: `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, `run.py`.

## 11. Remaining gaps

- **P0-01** Bounded processing service contract (UI-v2 ↔ Lauf)
- **P0-03** Policy-to-runtime bridge
- **P1** Review/Settings-Navigation
- **P1** Policy-Editor-Controls

## 12. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_BOUNDED_PROCESSING_SERVICE_CONTRACT_01` — schmalen, Track-B-sicheren Lauf-Adapter-Vertrag definieren (ohne Processing-Core-Umbau, ohne Track-A-Pollution), damit der Workspace nach einem echten Lauf echte Ergebnisse binden kann.
