# Audit — Track-B Real-PDF GUI Visual Smoke Guided

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_01`

## 2. Masterplan position: Prompt 12/34

Prompt 12 von 34 bis echter SaaS-Reife.

## 3. HEAD before/after

- **HEAD before:** `23161618efa3dfe2fd7d0026eed7f07153db0715`
- **HEAD after:** siehe Commit dieses Tasks / `git rev-parse HEAD` im Final Report

## 4. Purpose

Geführten GUI-Visual-Smoke für Track-B mit kopierten Real-PDFs dokumentieren: sicherer App-Start, kontrollierte Ordner, erwartete Counts, Safety-Proof, Export-Vorschau, leerer Output als Preview-Only, Return-Format für Hadi. Keine Code-/Runtime-Änderung, keine produktive Verarbeitung, keine realen Rechnungsordner.

## 5. Technical baseline from Prompt 11

- Path-Policy-Repair: kontrollierte kopierte Sandbox-/Testpfade erlaubt; Produktiv-/Originalpfade blockiert
- Real-PDF Dry-Run: 5 Review / 0 Recognized / 5 Planned; Export-Vorschau data-only
- Output: `OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY`
- Input hashes unverändert; `run_once` 0; OCR/AI/network nicht produktiv ausgeführt
- Product status before this task: `TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBLE_PREVIEW_ONLY`
- Scope-Sync-Audit (read-only): `POST_REAL_PDF_SANDBOX_REPAIR_SCOPE_SYNC_AUDIT_WARN_ALLOWED_BUT_UNLISTED_UIV2_CONTRACT_CHANGE` — Prompt 12 mit dokumentierter Vorsicht erlaubt (`core_dry_run_contract.py` UI-v2-Contract/Boundary, behavior-preserving für productive core)

## 6. GUI visual smoke scope

- Docs + Doc-Test only
- Guided Start / Monitor / UI-Schritte / Expected observations / Return-Format
- Kontrollierter Ordner `KI-Rechnungen-Test` only
- Kein GUI-Produktivlauf in diesem Task erzwungen; kein finales Write/Move/Archive/Rename
- Keine Änderung an Track A, Processing-Core, Release-Tags

## 7. App start evidence

| Kandidat | Evidenz |
|---|---|
| `invoice_tool/ui_v2/app.py` | vorhanden; exportiert `build_ui_v2`; **kein** `-m`-Runnable |
| `python -m invoice_tool.ui_v2.app` | nicht unterstützt (kein `__main__` / kein `main`) — Guide erfindet keinen falschen Entrypoint |
| `app_ui_v2.py` | belegter Track-B UI-v2-Start |
| Empfohlener Befehl | `.venv/bin/python app_ui_v2.py` |
| Fallback Flet 0.85 | `.venv-flet085/bin/python app_ui_v2.py` / `scripts/run_ui_v2_flet085.sh` |

## 8. Monitor command

Dokumentiert in Guide Abschnitt A: Parallel-`while true`-Sichtkontrolle für  
`$HOME/Desktop/KI-Rechnungen-Test/{input,output}` mit Hinweis, dass leerer Output im Dry-Run erlaubt ist, wenn Result-State + Export-Vorschau sichtbar sind.

## 9. Expected visual evidence

- Workspace akzeptiert kontrollierte Pfade
- „Sandbox-Lauf starten“ verfügbar
- Running- und Completed/Review-State
- Counts ≈ Review 5 / Recognized 0 / Planned 5
- Safety-Proof sichtbar
- Export-Vorschau sichtbar
- Review-Seite sichtbar
- Keine finalen Invoice-PDFs; Input unverändert

## 10. Empty output interpretation

Leerer Output = `OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY` **nur** mit sichtbarem nützlichem Result-State + Export-Vorschau.  
Ohne Result-State = Blocker. Finale umbenannte PDFs = UNSAFE.

## 11. Safety/stop rules

Stop bei Original-/Produktivordnern, Input==Output, produktiver Verarbeitung, finalen Writes/Moves/Archives/Renames, Input-Mutation, Fake-Success, Unsicherheit. Keine realen Rechnungsordner. Keine produktive Verarbeitung.

## 12. No productive processing

Bestätigt — Guide verbietet Produktivlauf; dieser Task führt keinen Produktivlauf aus. Keine Code-/Runtime-Änderung.

## 13. No real invoice folders

Bestätigt — nur dokumentierter kontrollierter Testordner `KI-Rechnungen-Test`. Keine realen Rechnungsordner verarbeitet.

## 14. No release tag changes

Release-Tags unverändert:

- `product-v1-local-pilot-2026-07-22` → `06dbfbcdbc753a781538039967a24237148c167e`
- `internal-working-version-2026-07-21` → `77ed11f98d1a2eef0bb3294fc3d2784623042ca7`

Keine Tags erstellt/geändert.

## 15. Product status after task

`TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDE_READY`

## 16. Remaining prompts: 22

## 17. Exact next task:

`KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_01`

---

## Files created

- `docs/KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_2026-07-22.md`
- `tests/test_track_b_real_pdf_gui_visual_smoke_guided_docs.py`

## No code/runtime change

Bestätigt — nur Docs + Doc-Test. Keine Änderung an UI-v2 Runtime, Track A, Processing-Core.
