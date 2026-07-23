# Audit — Track-B Real-PDF Sandbox Result Visibility Repair

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBILITY_REPAIR_01`

## 2. Masterplan position: Prompt 11/34

Prompt 11 von 34 bis echter SaaS-Reife.

## 3. HEAD before/after

- **HEAD before:** `8b27480278e189b700255b874044314a8dc21065`
- **HEAD after:** `0a44be2418e572c6881f1f0a1e3fbb0a90af59af`

## 4. Root cause

`_DESKTOP_ORIGINAL_RE` blockierte `Desktop/.../KI-Rechnungen-Test/...` wegen Desktop + „Rechnung“, ohne positiven Sandbox-/Test-Override. Dry-Run wurde nicht erreicht; leerer Output war kein Preview-Erfolg.

## 5. Files changed

- `invoice_tool/ui_v2/core_dry_run_contract.py`
- `invoice_tool/ui_v2/sandbox_processing_gate.py`
- `invoice_tool/ui_v2/core_bridge.py`
- `tests/test_track_b_real_pdf_sandbox_path_policy.py` (neu)
- `tests/test_track_b_controlled_copied_real_pdf_sandbox_smoke.py`
- `docs/KI_RECHNUNGEN_TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBILITY_REPAIR_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBILITY_REPAIR_2026-07-22.md`
- `docs/KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_2026-07-22.md` (Evidence-Update)
- `docs/audits/KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_2026-07-22.md` (Evidence-Update)

Nicht geändert: Track-A UI, processing-core (`run.py`/`processing.py`/…), Release-Tags.

## 6. Path policy before/after

| Aspekt | Before | After |
|---|---|---|
| Desktop+Rechnung | immer block | block, außer positives Sandbox-/Test-Signal |
| `KI-Rechnungen-Test` | block (`original_looking`) | allow (positives `test`-Token) |
| `/RECHNUNGEN/` | block | block |
| `/02_Rechnungseingang/` | block | block |
| `/Original/`, `/Produktiv/` | block | block |
| Positives Signal erforderlich | nein | ja |
| Blanket Desktop/Rechnung allow | nein | nein |

## 7. Paths allowed

- Explizite kopierte Sandbox-/Testpfade mit positivem Signal und getrennten Input/Output
- Kontrolliert: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` + `.../output`
- Optional env-scoped Roots via `KI_RECHNUNGEN_COPIED_SANDBOX_TEST_ROOTS`

## 8. Paths still blocked

- `/Users/hadi_neu/Desktop/RECHNUNGEN/**`
- `/Users/hadi_neu/Desktop/02_Rechnungseingang/**`
- beliebige `Rechnungseingang` / `Original` / `Produktiv` Segmente
- identische Input/Output
- fehlende/nicht-Directory-Pfade
- `productive_mode_requested=true`
- Pfade ohne positives Sandbox-/Test-Signal

## 9. Controlled copied real-PDF smoke result

`PASS_PREVIEW_ONLY` / Product status `TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_PASS_PREVIEW_ONLY`  
5 PDFs → 5 Review + 5 planned (OCR/AI nicht ausgeführt), Bridge ok, Input unverändert.

## 10. Output classification

`OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY`

## 11. Empty-output explanation

Leerer Output ist erwartetes Preview-Only-Verhalten nach erfolgreichem Dry-Run (data-only planned destinations, keine finalen Invoice-PDFs). Nicht identisch mit Prompt-10-Block vor Dry-Run.

## 12. Result state summary

Nützlicher Result-State: `completed`/`completed_with_review`, 5 Review-Items, 5 planned destinations, Warnings (`ocr_not_run` / `ai_not_run`), Safety-Proof vorhanden.

## 13. Export preview summary

Export-Vorschau aus echtem Run-State: keine final geschriebenen Dateien, produktive Verarbeitung gesperrt, nicht SaaS-/production-ready.

## 14. Mutation prevention proof

Input hashes/listing unverändert; Output ohne finale PDFs.

## 15. run_once prevention proof

Monkeypatch Counter `run_once == 0`.

## 16. OCR/AI/network status

OCR/AI im Core-Dry-Run absichtlich nicht ausgeführt (`ocr_not_run` / `ai_not_run`); Network-/OCR-Hooks Counter 0.

## 17. Tests run/results

- `tests/test_track_b_real_pdf_sandbox_path_policy.py` → 15 passed
- `tests/test_track_b_controlled_copied_real_pdf_sandbox_smoke.py` → 2 passed
- Focused regression (bridge wiring, local pilot, export polish, core dry-run, Track A) → 92 passed
- `tests/test_ui_v2_*.py` + `tests/test_saas_ui_v2_*.py` → 576 passed, 44 skipped
- `git diff --check` → clean

## 18. No productive processing

Bestätigt.

## 19. No real invoice folders

Bestätigt — nur kontrollierter `KI-Rechnungen-Test`.

## 20. No release tag changes

Unverändert:

- `product-v1-local-pilot-2026-07-22` → `06dbfbcdbc753a781538039967a24237148c167e`
- `internal-working-version-2026-07-21` → `77ed11f98d1a2eef0bb3294fc3d2784623042ca7`

## 21. Product status after task

`TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBLE_PREVIEW_ONLY`

## 22. Remaining prompts: 23

## 23. Exact next task

`KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_01`
