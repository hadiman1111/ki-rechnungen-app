# Audit: Track-B Core Bridge Real Sandbox Run Wiring

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01`

## 2. Masterplan position

Prompt **3/34**

## 3. HEAD before/after

- Before: `c96fc128eb5b53f528c9f901270ff1f1b2a3426d`
- After: 

## 4. Diagnosis

1. **Bisheriger Blocker:** `core_bridge` endete bei `REQUIRES_CORE_DRY_RUN_CONTRACT` / „Sandbox nicht verbunden“.
2. **Jetzt aufzurufende Funktion:** `invoice_tool.core_dry_run.run_core_dry_run_sandbox`.
3. **Request-Bau:** aus Sandbox-Args → `CoreBridgeRequest` → `CoreDryRunRequest` mit dry_run/no_mutation/Confirmations.
4. **Auflösung:** Workspace-Ordner + aktive Profil-/Konfigurationsauswahl + Sandbox-Root.
5. **Safety-Flags:** dry_run=true, no_mutation=true, productive_mode_requested=false, Confirmations nur nach Gate.
6. **Mapping:** CoreDryRunResult → BridgeResult → ProcessingRunState (Counts, Warnings, Safety).
7. **Jetzt sichtbar:** Status, Counts, planned destinations data-only, Safety-Proof, ehrliche PDF-Review.
8. **Prompt 4/34:** tieferes Review-UX / Result-Detailmapping.
9. **Mutationsschutz:** kein `run_once`, Source-Snapshot im Core-Dry-Run, Bridge lehnt Originalpfade ab, Output-Writes im Dry-Run default aus.

## 5. Files changed

Siehe Commit-Diff (Track-B ui_v2 + Tests + Docs). Processing-core (`run.py`/`processing.py`/…) unverändert.

## 6. Core dry-run API call wired

**yes** — `run_core_dry_run_sandbox`

## 7. Request fields

`input_dir`, `output_dir`, profile/config ids, `dry_run=true`, `no_mutation=true`, Confirmations, `productive_mode_requested=false`, optional `run_id`, `sandbox_root`.

## 8. Safety gates

Missing input/output, same path, original-looking, missing profile/config, productive, outside sandbox, non-dir paths — jeweils ohne Core-Call.

## 9. Mapping behavior

Status/run_id/recognized/review/error/planned/warnings/safety_proof → ProcessingRunState; keine erfundenen Rows.

## 10. Workspace status after click

„Prüfung läuft …“ → abgeschlossen / mit Prüffällen / fehlgeschlagen / kompakter Blocker + Counts + Safety-Proof.

## 11. Export/reporting behavior

Preview-only; kann realen Dry-Run-State spiegeln (`sourced_from_real_dry_run`).

## 12. Mutation prevention proof

tmp_path-Tests: Original- und Inbox-Bytes unverändert; planned paths nicht geschrieben; kein `run_once`.

## 13. Track A preservation proof

Geschützte Track-A-UI-Dateien nicht geändert; `test_track_a_internal_app_protection` grün.

## 14. Tests run/results

Focused: 94 passed  
Full UI-v2: 514 passed, 44 skipped  
`git diff --check`: clean

## 15. No productive processing

yes

## 16. No real invoice folders touched

yes (nur pytest `tmp_path`)

## 17. No release tag changes

yes

## 18. Remaining prompts

31

## 19. Exact next task

`KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_01`
