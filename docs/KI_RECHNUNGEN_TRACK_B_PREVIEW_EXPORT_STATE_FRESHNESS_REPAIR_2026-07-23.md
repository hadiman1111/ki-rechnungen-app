# Track-B Preview Export State Freshness Repair

**Task ID:** `KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_REPAIR_01`  
**Masterplan:** Prompt 24/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-reif**, **nicht produktionsreif**.

---

## Purpose

Preview Export muss immer denselben aktuellen Track-B-Run-/Review-State serialisieren, den die Review-UI zeigt. Stale Manifest-/Dry-Run-/Export-Ordner-Daten dürfen keinen Export mehr speisen.

---

## User manual evidence

Nach Prompt 23 zeigte die Review-UI korrigierte Werte (u. a. LUMITOP `476,00`, 1A-Bootshop `105,75`, Böttcher Storno `er_storno`, PayPal-/Card-Guidance). Der neueste Preview-Export-Ordner enthielt jedoch noch Pre-Prompt-21-Namen:

- LUMITOP `500,00`
- 1A-Bootshop `80,55`
- Böttcher Storno `er_er` statt `er_storno`

Ordner:

`/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/preview-export-track-b-dry-a9609610b265-20260723T105958144956Z`

---

## Baseline from Prompt 23

- Configuration-Coverage-Guidance ready.
- Controlled 5-PDF Guidance korrekt in der UI.
- Keine produktive Verarbeitung / keine realen Rechnungsordner.
- HEAD-Baseline: `9b10343946e89533278dd538b68412093277cc55`

---

## UI/export mismatch diagnosis

1. Review-UI und Preview Export lesen beide aus `ProcessingRunState`, aber der Export hatte **keinen Freshness-Guard** gegen die Review-UI-Erwartungen.
2. Ein älterer In-Memory-/Export-Lauf (`track-b-dry-a960…`) konnte stale `planned_destinations` behalten (Beträge/Art), während die UI nach erneutem Enrichment/Sandbox aktuelle Werte zeigte.
3. Preview Export rekonstruierte Dateinamen aus `planned_destinations` ohne Abgleich mit dem aktuellen Review-Naming-Snapshot.
4. Alte Preview-Export-Ordner wurden zwar nicht als Code-Quelle gelesen, aber es gab keine harte Sperre, sie als Input zu verwenden.
5. `run_id` kann gleich bleiben, während sich der State ändert — ohne `export_created_at` / Freshness-Metadaten war Stale schwer erkennbar.
6. Intern inkonsistenter State (z. B. `selected_art=storno` bei Dateiname `er_er`) wurde bisher nicht laut blockiert.

---

## Stale export root cause

**Root cause:** Preview Export serialisierte den übergebenen Run-State ohne (a) Refresh der aktuellen Sandbox-Enrichment-Daten und ohne (b) Abgleich mit dem Review-UI-Naming-Snapshot. Dadurch konnten Pre-Prompt-21-Werte (`500,00` / `80,55` / `er_er`) geschrieben werden, obwohl die UI bereits aktuelle Werte zeigte.

---

## Single source of truth repair

1. `build_review_ui_export_expectations(run_state)` — dieselbe Naming-Entscheidung wie die Review-UI.
2. `refresh_run_state_from_current_sandbox_input(...)` — vor Workspace-Export erneutes Local-Enrichment aus dem kontrollierten Input (keine Input-Mutation).
3. `apply_workspace_preview_export` aktualisiert `state.processing_run_state` auf den refreshed State und exportiert genau diesen.
4. Neue Exportordner pro Aktion (`preview-export-<run_id>-<timestamp>`), kein Reuse alter Exportordner als Quelle.

---

## Freshness guard

`validate_export_state_freshness(...)` prüft vor dem Schreiben:

- `preview_filename` / `rendered_filename`
- `selected_amount`
- `selected_payment_field`
- `selected_art`
- interne Widersprüche (z. B. Storno-Art vs. `er_er`-Dateiname)

Bei Mismatch: **`PREVIEW_EXPORT_STALE_STATE_BLOCKED`** — kein irreführendes Output-Paket.

---

## Export metadata

Manifest enthält u. a.:

| Feld | Wert |
|---|---|
| `state_source` | `processing_run_state.current` |
| `exported_from_current_state` | `true` |
| `previous_export_reused` | `false` |
| `source_run_id` | aktuelle Run-ID |
| `source_state_updated_at` | falls vorhanden |
| `export_created_at` | Export-Zeitstempel |
| `state_freshness_checked` | `true` |
| `state_freshness_result` | `pass` |

---

## Controlled verification result

Mit aktuellem Enrichment + Export (kontrollierte 5 PDFs):

| Beleg | Erwarteter Kern im Preview-Namen |
|---|---|
| LUMITOP | `476,00` / paypal |
| 1A-Bootshop | `105,75` / paypal |
| Böttcher Rechnung | `84,39` / card |
| Luxvenum | `154,95` / `FEHLT_payment_field` |
| Böttcher Storno | `68,94` / `er_storno` |

Workspace-Export mit absichtlich stale State refreshed auf genau diese Werte.

---

## Preview export before/after examples

**Before (stale):**

- `..._LUMITOP_500,00_paypal.pdf`
- `..._1A-Bootshop.de_80,55_paypal.pdf`
- `..._er_er_Böttcher_AG_68,94_FEHLT_payment_field.pdf`

**After (current):**

- `REVIEW_REQUIRED__SUGGESTED__2026-05-11_er_er_LUMITOP_476,00_paypal.pdf`
- `REVIEW_REQUIRED__SUGGESTED__2026-05-15_er_er_1A-Bootshop.de_105,75_paypal.pdf`
- `REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-06-18_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf`

---

## Safety guarantees

- Input-PDFs byte-unverändert
- kein `run_once`
- kein finaler Write/Move/Archive/Delete von Originalen
- Output nur unter kontrolliertem Sandbox-/Test-Output
- alte `preview-export-*`-Ordner als Input blockiert
- Track A / Processing-Core unverändert
- Release-Tags unverändert
- nicht SaaS-ready / nicht production-ready

---

## Remaining gap

- Manueller GUI-Smoke mit frischem Preview-Export nach Sandbox-Lauf (Prompt 25).
- Noch keine produktive Freigabe / kein finaler Export.

---

## Test result

Siehe Audit. Fokus: neuer Freshness-Test + bestehende Track-B-Export-/Matching-Tests.

---

## No productive processing

Ja — Preview/Sandbox only.

## No real invoice folders

Ja — nur kontrollierte Testpfade.

## Not SaaS-ready / Not production-ready

Explizit unverändert.

## Next step

`KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_01`
