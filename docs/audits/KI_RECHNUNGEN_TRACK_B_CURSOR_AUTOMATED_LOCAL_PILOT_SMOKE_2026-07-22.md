# Audit — Track-B Cursor Automated Local Pilot Smoke

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_01`

## 2. Masterplan position: Prompt 8/34

Prompt 8 von 34 bis echter SaaS-Reife.

## 3. HEAD before/after

- **HEAD before:** `929ca3600f6771edae6ec8a04731074a0095fce5`
- **HEAD after:** siehe Commit dieses Tasks / `git rev-parse HEAD` im Final Report

## 4. Automated smoke classification

`CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT`

Begründung: Der sichere Core-Dry-Run-Pfad wird über die echte Track-B-Bridge-/Adapter-Kette erreicht; das Dry-Run-Resultat selbst ist ein deterministisches Fake-`CoreDryRunResult` (kein OCR/AI/Network). State-/Bucket-/Export-Mapping bleibt real.

## 5. Sandbox method

pytest `tmp_path` only:

```text
<tmp>/cursor-auto-sandbox/input_copy/
<tmp>/cursor-auto-sandbox/output_preview/
```

Kein Desktop-Sandbox-Ordner nötig. Kein `/Users/hadi_neu/Desktop/RECHNUNGEN/**`.

## 6. Files created/changed

- `tests/test_track_b_cursor_automated_local_pilot_smoke.py` (neu)
- `docs/KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md` (neu)
- `docs/audits/KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md` (neu)

## 7. Test path used

`tests/test_track_b_cursor_automated_local_pilot_smoke.py`  
Einstieg: `apply_start_processing` → LocalProcessingAdapter → Core Bridge → `run_core_dry_run_sandbox` (monkeypatched).

## 8. run_once prevention

`invoice_tool.run.run_once` ist monkeypatched; Aufruf erhöht Counter und wirft `AssertionError`. Smoke verlangt Counter `== 0`. Extra-Test prüft, dass der Patch greift.

## 9. OCR/AI/network prevention

Best-effort Monkeypatches auf typische OCR/AI/HTTP-Einstiege (`invoice_tool.ocr.*`, `invoice_tool.ai.*`, `requests.*`, `httpx.*`, `urllib.request.urlopen`). Zusätzlich liefert der Fake-Dry-Run ohne echte OCR/AI. Classification bleibt synthetisch.

## 10. Mutation prevention proof

SHA-256-Digest + Listing von `input_copy` before/after identisch. `output_preview` enthält keine Dateien (keine final umbenannten Rechnungs-PDFs).

## 11. Export preview proof

`build_export_preview_report` + `render_export_preview_text` aus dem echten Run-State nach dem Smoke. Enthält u. a. Export-Vorschau, keine final geschriebenen Dateien, Originale unverändert, Produktive Verarbeitung gesperrt, SaaS-Ready nicht erreicht. Forbidden Claims negativ geprüft.

## 12. Real invoice folder protection

Smoke-Pfade liegen ausschließlich unter `tmp_path`. Falls `/Users/hadi_neu/Desktop/RECHNUNGEN` existiert, wird dessen Digest before/after verglichen. Kein Pfad dieses Roots wird als Input/Output gesetzt.

## 13. Track A preservation proof

Focused Suite enthält `tests/test_track_a_internal_app_protection.py`. Keine Stage/Commit von Track-A-UI-Dateien. Bekannte Legacy-Dirty-Dateien (`ui_profile_dialog.py`, `ui_document_rules.py`) bleiben unstaged.

## 14. Tests run/results

Siehe Final Report (Focused + UI-v2/SaaS + `git diff --check`).

## 15. No code/runtime change except test/doc

Bestätigt — nur Test + Docs/Audit. Keine Änderung an UI-v2 Runtime, Track A, Processing-Core, Scripts, Resources, pyproject, venv.

## 16. No productive processing

Bestätigt — `productive_mode_requested=false`, kein `run_once`, kein finales Write/Move/Archive/Rename.

## 17. No release tag changes

Release-Tags unverändert (read-only):

- `product-v1-local-pilot-2026-07-22` → `06dbfbcdbc753a781538039967a24237148c167e`
- `internal-working-version-2026-07-21` → `77ed11f98d1a2eef0bb3294fc3d2784623042ca7`

Keine Tags erstellt/geändert.

## 18. Product status after task

`TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_CURSOR_SMOKE_READY`

## 19. Remaining prompts: 26

## 20. Exact next task

`KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_01`

---

## Diagnosis

### 1. What can be tested fully through Cursor

- Sandbox-Ordneranlage (tmp_path)
- Bridge-/Adapter-Kette ohne GUI
- Flag-Enforcement (`dry_run` / `no_mutation` / `productive_mode_requested`)
- `run_once`-Verbot
- State-/Bucket-/Review-/Export-Mapping
- Mutationsnachweis Input/Output
- Track-A-Schutztests
- Doc-/Status-Gates

### 2. What cannot be visually verified without human/manual GUI smoke

- UI-Layout, Farben, Button-Feedback im echten Fenster
- Folder-Picker-Verhalten
- Menschliche Lesbarkeit der Workspace-/Review-Seiten
- Visuelle Export-Vorschau im GUI

### 3. Which automated path is equivalent to the Track-B sandbox chain

`mark_start_checking` → `apply_start_processing` → `LocalProcessingAdapter` → `run_core_bridge_sandbox_dry_run` → `run_core_dry_run_sandbox` (hier: synthetisches Resultat) → Result-Mapping → Review-VM → Export-Preview.

### 4. Which sandbox folders are used

Nur pytest `tmp_path` Unterordner `cursor-auto-sandbox/input_copy` und `…/output_preview`.

### 5. How mutation prevention is measured

SHA-256 Tree-Digest + Listing von `input_copy`; leerer `output_preview`; optional Digest von `RECHNUNGEN` falls vorhanden.

### 6. How run_once is blocked/monitored

Monkeypatch mit Counter + AssertionError; Smoke verlangt Counter 0.

### 7. How export preview is verified

Realer `ProcessingRunState` → `build_export_preview_report` / `render_export_preview_text` / Payload; Pflichtstrings und Forbidden Claims.

### 8. Why this is still not SaaS-ready and not production-ready

Nur lokaler Sandbox-Dry-Run-Smoke mit synthetischem Resultat. Kein Produktivmodus, keine Cloud/Multi-Tenant/Billing, keine Originalverarbeitung, keine finalen Schreibpfade, keine Reife-Claims. Explizit: **nicht SaaS-ready**, **nicht production-ready**.
