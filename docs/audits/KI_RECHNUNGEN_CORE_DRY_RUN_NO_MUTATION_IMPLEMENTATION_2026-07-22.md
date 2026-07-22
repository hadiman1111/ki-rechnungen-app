# Audit — Core Dry-Run No-Mutation Implementation

## 1. Task ID

`KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01`

## 2. Masterplan position

Prompt **2/34**

Exact next task:

`KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01`

## 3. HEAD before / after

- HEAD before: `1be4afd9faf13c45d93d3fa9d4ec652936a13a11`
- HEAD after: *(gesetzt nach Commit in diesem Task)*

## 4. Diagnosis

1. **Track-A/Internal processing:** `invoice_tool.run.run_once(source, output, *, config_path, profile_path)` → `InvoiceProcessor.process_all()`.
2. **Source archive/move/rename/delete:** `processing.py` (`_publish_and_archive`, `_archive_original`, `archive_original_safely`, `shutil.move` nach `<source>/archiv/<run-id>/`).
3. **Output writes:** `run_once` legt Documents-Basis unter Output an; Processor publiziert Zieldateien; Mapping/Logs unter App Support.
4. **App-Support artifacts:** `create_run_support_dir()` → `~/Library/Application Support/KI-Rechnungen/runs/<run-id>/`.
5. **Safe to reuse:** Contract-Validation; read-only Candidate-Scan; Text-Lesen; Snapshot-Vergleich; Result-/SafetyProof-Typen.
6. **Must not call in dry-run:** `run_once`, `InvoiceProcessor.process_all`, Archive-/Move-Helfer, DATEV/Cloud-Export, OCR/AI-Extraktoren gegen produktive Pfade.
7. **Classification/routing purity:** Bestehende Helper brauchen `ExtractedData`/`ProcessingPreset` und sitzen im mutierenden Produktivpfad — für Prompt 2 nicht direkt angebunden; begrenzte Text-Marker-Heuristik statt Fake-OCR.
8. **New dry-run boundary:** `invoice_tool.core_dry_run.run_core_dry_run_sandbox`.
9. **Track-A regression:** bestehende Processing-Core-Dateien unverändert; Protection-Tests + Contract-Tests grün.

## 5. Files changed

- `invoice_tool/core_dry_run.py` *(neu)*
- `tests/test_core_dry_run_no_mutation.py` *(neu)*
- `docs/KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_2026-07-22.md` *(neu)*
- `docs/audits/KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_2026-07-22.md` *(neu)*

## 6. Processing-core changed?

**Nein** — keine Änderung an:

- `invoice_tool/run.py`
- `invoice_tool/processing.py`
- `invoice_tool/routing.py`
- `invoice_tool/routing_guards.py`
- `invoice_tool/classification.py`
- `invoice_tool/target_routing.py`

Nur additives neues Modul `invoice_tool/core_dry_run.py`.

## 7. Dry-run API name / signature

```text
run_core_dry_run_sandbox(request: CoreDryRunRequest) -> CoreDryRunResult
```

## 8. Safety guards implemented

- Contract-Validation vor jeder Verarbeitung
- Original-looking / same input-output / sandbox_root Rejects
- Productive hooks fail-closed (`_PRODUCTIVE_RUN_ONCE`, `_DATEV_CLOUD_EXPORT_HOOK`)
- Source-Snapshot before/after (Name/Size/mtime/hash)
- Kein Archive-Create im Input
- Keine Default-Dateischreibvorgänge
- Filename-as-Truth disabled

## 9. Mutation prevention proof

- Tests vergleichen Source-Listing vor/nach
- `CoreDryRunSafetyProof` mit `no_source_*` Flags
- `evidence_notes` enthalten `source_snapshot_identical=True`
- Monkeypatch: `run_once` wird nicht aufgerufen
- AST: keine `run_once`-/DATEV-Call-Sites in `core_dry_run.py`

## 10. Result model behavior

- PDF ohne Extraktion → `review`
- Text mit ≥2 Invoice-Markern → begrenzt `recognized`
- Unsupported/unreadable → `errors`
- `planned_destinations[*].applied is False`
- Status: `completed` / `completed_with_review` / `failed`

## 11. Track A preservation proof

- Protection-Test: Processing-Core vs HEAD clean
- Keine Track-A-UI-Dateien geändert
- Legacy dirty bleiben unstaged: `ui_profile_dialog.py`, `ui_document_rules.py`

## 12. Tests run / results

Focused (erwartet):

```bash
.venv/bin/python -m pytest \
  tests/test_core_dry_run_no_mutation.py \
  tests/test_ui_v2_core_dry_run_contract.py \
  tests/test_track_a_internal_app_protection.py
```

UI-v2 full suite + `git diff --check` — Ergebnisse im Final Report.

## 13. No productive processing

Kein Produktivmodus, kein `run_once`-Aufruf, kein DATEV/Cloud-Export.

## 14. No real invoice folders touched

Nur `pytest` `tmp_path` / synthetische Dateien.

## 15. No release tag changes

Keine Tag-Erzeugung/-Änderung.

## 16. Remaining prompts

**32** (Prompt 3–34)

## 17. Exact next task

`KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01`
