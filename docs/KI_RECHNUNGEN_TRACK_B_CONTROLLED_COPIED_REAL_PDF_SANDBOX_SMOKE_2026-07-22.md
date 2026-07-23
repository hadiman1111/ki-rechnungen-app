# Track-B Controlled Copied Real-PDF Sandbox Smoke

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_01`  
**Masterplan:** Prompt 10/34  
**Product status (before):** `TRACK_B_CURSOR_SMOKE_EVIDENCE_ACCEPTED_SYNTHETIC_LIMITATION_DISCLOSED`  
**Product status (after):** `TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_BLOCKED_NO_REAL_PATH`  
**Smoke classification:** `BLOCKED_NO_REAL_PATH`  
**Date:** 2026-07-22

Kontrollierter Sandbox-Smoke gegen kopierte echte PDFs.  
Explizit: **nicht SaaS-ready**, **nicht production-ready**, keine produktive Verarbeitung.

---

## Purpose

Prüfen, ob Track-B gegen den vorhandenen kopierten Real-PDF-Testordner laufen kann und ob ein leerer Output-Ordner erwartetes Preview-Only-Verhalten oder ein fehlender Real-PDF-Sandbox-Pfad ist.

---

## Controlled folder paths

| Rolle | Pfad |
|---|---|
| Input (kopierte Test-PDFs) | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` |
| Output (separat) | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` |
| Sandbox-Root | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test` |

Env-Overrides:

- `KI_RECHNUNGEN_REAL_PDF_SMOKE_INPUT`
- `KI_RECHNUNGEN_REAL_PDF_SMOKE_OUTPUT`

Nicht verwendet:

- `/Users/hadi_neu/Desktop/RECHNUNGEN/**`
- `/Users/hadi_neu/Desktop/02_Rechnungseingang/**`
- sonstige produktive/originale Rechnungsordner

---

## Safety validation

| Check | Result |
|---|---|
| Worktree | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Input existiert | ja |
| Output existiert | ja (leer vor Lauf) |
| Input ≠ Output | ja |
| Beide unter `KI-Rechnungen-Test` | ja |
| Forbidden markers (`/RECHNUNGEN/`, `/02_Rechnungseingang/`, …) | keine |
| Task-level: kopierter Sandbox-Testordner | akzeptiert |
| Track-B Bridge/Contract: `path_looks_like_original` | **abgelehnt** |

Ursache der Ablehnung: Heuristik `_DESKTOP_ORIGINAL_RE` trifft auf  
`Desktop/.../KI-Rechnungen-Test/...` (Desktop + Substring „Rechnung“).

---

## PDF count

**5** kopierte PDFs im Input:

- `320262919974.pdf`
- `420260091336.pdf`
- `FA011466.pdf`
- `Rechnung RE-202605-14594.pdf`
- `Rechnung-2026156019-102201.pdf`

---

## What was run

1. Preflight Git/Ordner-Checks.
2. Input-Listing + SHA-256 before.
3. Monkeypatch: `run_once` + best-effort OCR/AI/Network → fail if called.
4. `run_core_bridge_sandbox_dry_run` gegen die kontrollierten Ordner.
5. Direkter Contract/`run_core_dry_run_sandbox`-Versuch (gleicher Pfad).
6. Mapping des Bridge-Blockers auf `ProcessingRunState` + Export-Vorschau.
7. Input-Hashes after; Output-Listing after.
8. Kein synthetisches Fake-`CoreDryRunResult`.

---

## Real-PDF sandbox result

**BLOCKED_NO_REAL_PATH**

- Bridge: `blocked_original_looking` / `core_bridge_original_looking`
- Core Contract: `core_dry_run_original_looking_path`
- Kein erfolgreicher Dry-Run gegen die 5 Real-PDFs
- Kein erkannte/review/error/planned Bucket aus PDF-Auswertung
- Kein Fake-Success

---

## Workspace/result state classification

| Aspekt | Status |
|---|---|
| Meaningful recognized/review/error/planned | nein |
| Safety-proof / Blocker-State | ja (`blocked`) |
| Nur Blocker | ja |
| Empty/no PDFs (Input) | nein (5 PDFs) |
| Failed unsafe | nein |

---

## Output-folder classification

`OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY` im Sinne „keine finalen PDFs geschrieben“ — aber **nicht** als Erfolg eines Preview-Only-Dry-Runs.

Ehrliche Einordnung parallel: `OUTPUT_NO_USEFUL_RESULT` bezogen auf sichtbare Verarbeitungs-Evidenz aus Real-PDFs.

---

## Whether empty output is expected or problematic

**Leerer Output ist hier erwartet, aber problematisch für den Smoke-Zweck.**

- Erwartet: weil Track-B den Pfad vor dem Dry-Run ablehnt und deshalb nichts schreibt.
- Problematisch: weil damit **nicht** bewiesen ist, dass ein erfolgreicher Preview-Only-Dry-Run gegen kopierte echte PDFs leeren Output hinterlässt.
- Der leere Ordner ist **kein** Nachweis für „preview-only success“, sondern Folge von **path policy block**.

---

## Mutation proof

- Input SHA-256 before == after
- Input-Listing before == after
- Keine finalen Invoice-PDFs im Output
- Output-Dateianzahl unverändert (0)

---

## run_once proof

`invoice_tool.run.run_once` monkeypatched; Counter blieb 0. Bridge/Core importieren den Produktivpfad nicht für diesen Lauf.

---

## OCR/AI/network proof or blocker

- OCR/AI/Network best-effort monkeypatched; Counter 0
- Zusätzlich: Dry-Run wurde wegen Path-Policy gar nicht ausgeführt → keine Extraktion
- Hinweis aus Core-Design: echte PDFs würden im Dry-Run ohnehin als Review (`ocr_not_run` / `ai_not_run`) landen — dieser Pfad wurde hier nicht erreicht

---

## No productive processing

Bestätigt: `dry_run=true`, `no_mutation=true`, `productive_mode_requested=false` im Request; Produktivmodus nicht freigeschaltet; keine finalen Writes/Moves/Archives/Renames.

---

## No real invoice folders

Bestätigt: nur `KI-Rechnungen-Test/{input,output}`. Keine Original-/Produktivordner als Input/Output.

---

## Not SaaS-ready

Dieser Smoke beweist keine SaaS-Reife.

---

## Not production-ready

Dieser Smoke beweist keine Production-Reife.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBILITY_REPAIR_01`

Nötig: Track-B muss den explizit kontrollierten kopierten Testordner `KI-Rechnungen-Test` als erlaubten Sandbox-Pfad akzeptieren können (ohne Desktop-Produktivordner freizuschalten), damit Real-PDF-Review-/Export-Evidenz sichtbar wird.

---

## Follow-up (Prompt 11/34)

Pfadpolitik repariert in  
`KI_RECHNUNGEN_TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBILITY_REPAIR_01`.  
Re-Smoke gegen denselben kontrollierten Ordner: `PASS_PREVIEW_ONLY`  
(5 Review / 5 planned, Output leer erwartet, Input-Hashes unverändert).  
Siehe `docs/KI_RECHNUNGEN_TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBILITY_REPAIR_2026-07-22.md`.
