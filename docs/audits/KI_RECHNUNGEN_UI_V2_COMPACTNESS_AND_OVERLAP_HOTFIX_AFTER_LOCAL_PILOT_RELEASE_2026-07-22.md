# KI_RECHNUNGEN_UI_V2_COMPACTNESS_AND_OVERLAP_HOTFIX_AFTER_LOCAL_PILOT_RELEASE_2026-07-22

## 1. Task ID

`KI_RECHNUNGEN_UI_V2_COMPACTNESS_AND_OVERLAP_HOTFIX_AFTER_LOCAL_PILOT_RELEASE_01`

## 2. Purpose

Nach dem lokalen Pilot-Release (`product-v1-local-pilot-2026-07-22`) die Track-B UI-v2 Hinweise kompakter und lesbarer machen, missverständliche SaaS-Wortlaute entfernen und Layout-Überlappungen bei Eingabefeldern/Buttons verhindern — ohne Produktlogik, Track A oder Processing-Core zu ändern.

## 3. User screenshots / observations summarized

- Zu viele große Status-/Readiness-Karten verbrauchen vertikalen Platz.
- Onboarding-/Status-Hinweise wiederholen sich.
- Profil-/Konfigurations-/Einstellungsseiten zeigen verbose Readiness-Tabellen.
- Formulierungen wie „SaaS-Profilentwurf“ / „Lokale SaaS-Entwürfe“ sind für lokale Pilottests verwirrend.
- Eingaben/Buttons wirken beengt oder können optisch überlappen.

## 4. What was too verbose

- Arbeitsbereich: Onboarding als viele große `make_metadata_row("Status", …)`-Zeilen plus Checkliste als Tabellenzeilen.
- Arbeitsbereich: mehrere gestapelte `inline_warning`-Karten für Sandbox-Readiness.
- Einstellungen: große Settings-Panels mit vielen Hinweis-Zeilen und voller Capability-Tabelle.
- Profile/Konfigurationen/Policy-Editor: wiederholte „Hinweis“-Tabellenzeilen.
- Profilentwürfe: SaaS-lastige Labels trotz lokaler Pilotversion.

## 5. What was compacted

- Neue Compact-Helfer in `components.py`:
  - `compact_status_banner`
  - `compact_info_row`
  - `compact_hint_block`
  - `compact_checklist_block`
  - `compact_capability_matrix`
  - `dense_card`
- Arbeitsbereich: Compact-Banner + Checkliste + ein Hinweisblock statt großer Status-Tabelle / Warnungsstapel.
- Einstellungen: Compact-Banner, dense Statuskarte, Capability-Chips, kompakte Hint-Blöcke.
- Profile/Konfigurationen/Policy-Editor: kompakte Hint-Blöcke statt wiederholter Hinweis-Tabellen.

## 6. Wording changes

| Vorher | Nachher |
|---|---|
| SaaS-Profilentwurf (lokal) | Lokaler Entwurf |
| Lokale SaaS-Entwürfe | Lokale Profilentwürfe |
| Noch keine Cloud-Synchronisierung. | Nicht Cloud-synchronisiert. |
| SaaS-/UI-v2-Variante … | lokaler UI-v2-Profilentwurf … |
| lokaler SaaS-Entwurf (Fehlertexte) | lokaler Entwurf |

Kein SaaS-ready-Claim, kein produktiver DATEV-/Cloud-Export-Claim.

## 7. Overlap prevention

- Exportpfad im Arbeitsbereich: Label oberhalb (`form_field_group`) + `hint_text` statt floating `label=`.
- Profilentwurf Rename/Import/Export: Label-/Hint-Text oberhalb, Felder mit `hint_text`, Buttons darunter in eigenen Rows, etwas mehr Spacing.
- Compact-Karten mit reduziertem Padding, ohne Controls übereinander zu stapeln.

## 8. Files changed

- `invoice_tool/ui_v2/components.py`
- `invoice_tool/ui_v2/onboarding.py`
- `invoice_tool/ui_v2/pages/workspace.py`
- `invoice_tool/ui_v2/pages/settings.py`
- `invoice_tool/ui_v2/pages/profiles.py`
- `invoice_tool/ui_v2/pages/configurations.py`
- `invoice_tool/ui_v2/policy_editor_controls.py`
- `invoice_tool/ui_v2/saas_profile_persistence_view.py`
- `invoice_tool/ui_v2/saas_profile_draft_list_view.py`
- `invoice_tool/ui_v2/state.py`
- `invoice_tool/ui_v2/saas_profile_store.py`
- `tests/test_ui_v2_compactness_and_overlap_hotfix.py` (neu)
- `tests/test_ui_v2_onboarding_readiness.py`
- `tests/test_saas_ui_v2_profile_persistence_view.py`
- `tests/test_saas_ui_v2_profile_draft_list.py`
- `tests/test_saas_ui_v2_profile_draft_import_export.py`
- `tests/test_saas_ui_v2_profile_draft_rename_delete.py`
- `docs/audits/KI_RECHNUNGEN_UI_V2_COMPACTNESS_AND_OVERLAP_HOTFIX_AFTER_LOCAL_PILOT_RELEASE_2026-07-22.md`

## 9. Tests run and results

Focused:

```bash
.venv/bin/python -m pytest \
  tests/test_ui_v2_compactness_and_overlap_hotfix.py \
  tests/test_ui_v2_onboarding_readiness.py \
  tests/test_ui_v2_pilot_acceptance_gate.py \
  tests/test_ui_v2_product_v1_release_gate.py \
  tests/test_ui_v2_settings_navigation.py \
  tests/test_ui_v2_workspace_processing_contract.py
```

Ergebnis: **79 passed**

Full Track-B UI-v2:

```bash
.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
```

Ergebnis: **421 passed, 44 skipped**

## 10. Confirmation: no Track A change

Track-A protected files wurden nicht gestaged/geändert. Bekannte Legacy-Dirty-Dateien (`ui_profile_dialog.py`, `ui_document_rules.py`) bleiben unstaged.

## 11. Confirmation: no processing-core change

Keine Änderungen an `processing.py`, `routing.py`, `routing_guards.py`, `classification.py`, `target_routing.py`, `run.py`.

## 12. Confirmation: no productive processing

Kein Produktiv-Ausführungs-Schalter, keine Produktivfreigabe, keine Originalordner-Verarbeitung, kein OCR/AI-Lauf, kein Build.

## 13. Confirmation: release remains local pilot with limitations

Release-Tag `product-v1-local-pilot-2026-07-22` unverändert. UI bleibt ehrlich: lokale Pilotversion, Sandbox/Kopie, Produktiv gesperrt, Originalordner geschützt, Export nur Vorschau, nicht SaaS-bereit.

## 14. Exact next manual test instruction

1. UI-v2 lokal starten (ohne Build, ohne echte PDFs).
2. Arbeitsbereich öffnen: Compact-Banner mit den fünf Pilot-Chips prüfen; keine große Status-Tabelle.
3. Profile öffnen: „Lokale Profilentwürfe“ / „Lokaler Entwurf“ / „Nicht Cloud-synchronisiert“ prüfen; Rename-/Export-Felder ohne Label-Überlappung.
4. Konfigurationen öffnen: kompakte Hinweisblöcke statt vieler Hinweis-Tabellenzeilen.
5. Einstellungen öffnen: kompakte Status-/Capability-Darstellung; keine SaaS-ready- oder DATEV-Produktivexport-Behauptung.
6. Bestätigen: Scroll funktioniert, Buttons/Felder überlappen nicht.

`STOPPED_AFTER_KI_RECHNUNGEN_UI_V2_COMPACTNESS_AND_OVERLAP_HOTFIX — AWAITING_MANUAL_RETEST`
