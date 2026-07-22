# Audit — Core Dry-Run Sandbox API Contract

## Task ID

`KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`

## Masterplan position

Prompt **1/34**

Exact next task:

`KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01`

## Current corrected status

`NOT_LOCAL_PILOT_READY_CORE_DRY_RUN_API_REQUIRED`

## Diagnosis

1. **Track-A/Internal-Einstieg:** `invoice_tool.run.run_once(source, output, *, config_path, profile_path)` — genutzt von Track-A-GUI und Internal Launcher.
2. **Warum `run_once` unsicher für Track-B-Dry-Run ist:** kein `dry_run`/`no_mutation`; schreibt Outputs; archiviert Quellen; legt App-Support-Artefakte an; startet Extraktion/OCR/AI-Pfad.
3. **Zu verhindernde Mutationen:** Source move/rename/delete/archive; Writes außerhalb Sandbox-Output; Produktivmodus; echter DATEV/Cloud-Export; private Defaults; Filename-as-Truth.
4. **Erlaubte Artefakte nur in Sandbox-Output:** strukturierte Results/Reports, data-only planned destinations, optionale Evidence unter `output_dir`.
5. **Track-B benötigt:** run id/status, recognized/review/errors, planned destinations, summary, warnings, safety_proof.
6. **Pre-Processing-Guards:** dry_run/no_mutation/copied confirmation/original exclusion/profile+config/path heuristics/sandbox_root.
7. **Post-Run-Proof:** `CoreDryRunSafetyProof` + FS-Beweise in Prompt-2-Tests.
8. **Kein lokaler Pilot vor API:** ohne echten kopierten-PDF-Lauf mit No-Mutation ist Pilot-Status falsch (Statuskorrektur).

## Contract created

- Modul: `invoice_tool/ui_v2/core_dry_run_contract.py`
- Docs: `docs/KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_2026-07-22.md`
- Testplan: `docs/KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_TEST_PLAN_2026-07-22.md`

## Tests added

- `tests/test_ui_v2_core_dry_run_contract.py`
- optional Alignment: `tests/test_track_a_internal_app_protection.py` (Track-B-Entry-Liste)

## Docs created

- Contract, Testplan, dieses Audit

## No processing-core modification

Unverändert gelassen:

- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`
- `invoice_tool/run.py`

## No Track A modification

Geschützte Track-A-UI-Dateien nicht geändert. Bekannte Legacy-Dirty-Dateien bleiben unstaged:

- `invoice_tool/ui_profile_dialog.py`
- `invoice_tool/ui_document_rules.py`

## No productive processing

Kein Produktivmodus, kein `run_once`-Aufruf, keine OCR/AI, keine PDF-Verarbeitung in diesem Task.

## No real invoice processing

Keine Originalordner, keine echten Rechnungs-PDFs verarbeitet.

## Remaining prompts

**33** (Prompt 2–34)

## Exact next task

`KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01`
