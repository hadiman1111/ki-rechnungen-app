# Track-B Real-PDF Sandbox Result Visibility Repair

**Task ID:** `KI_RECHNUNGEN_TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBILITY_REPAIR_01`  
**Masterplan:** Prompt 11/34  
**Product status (before):** `TRACK_B_COPIED_REAL_PDF_SANDBOX_SMOKE_BLOCKED_NO_REAL_PATH`  
**Product status (after):** `TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBLE_PREVIEW_ONLY`  
**Date:** 2026-07-22

Reparatur der Track-B-Sandbox-Pfadpolitik für kontrollierte kopierte Testordner.  
Explizit: **nicht SaaS-ready**, **nicht production-ready**, keine produktive Verarbeitung.

---

## Purpose

Kontrollierte kopierte Sandbox-/Testordner (z. B. `KI-Rechnungen-Test`) sollen die Track-B-Sandbox-Grenze passieren können, ohne den Schutz vor Original-/Produktivordnern zu schwächen — damit ein Real-PDF-Dry-Run einen nützlichen Result-State / Export-Vorschau erzeugen kann.

---

## Problem

Prompt 10/34 fand den kontrollierten Ordner:

- Input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`
- Output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`

Task-level war der Ordner als kopierter Sandbox-Testordner gültig, aber Bridge/Contract blockierten mit `blocked_original_looking` / `core_dry_run_original_looking_path`.

---

## Root cause

Heuristik `_DESKTOP_ORIGINAL_RE` matchte `Desktop/...` + Substring „Rechnung“ in `KI-Rechnungen-Test`.  
Es gab keinen positiven Sandbox-/Test-Override. Deshalb lief kein Dry-Run; leerer Output war **kein** Preview-Only-Erfolg.

---

## Path policy repair

Positive Sandbox-Override (ohne Original-Schutz abzuschalten):

1. Harte Produktiv-/Original-Marker bleiben immer blockiert  
   (`/RECHNUNGEN/`, `/02_Rechnungseingang/`, `/Rechnungseingang/`, `/Original/`, `/Produktiv/`).
2. Benannte Original-Muster bleiben blockiert (`somaa`, `test rechnungen`, …).
3. Erst danach: positiver Sandbox-/Test-Signal-Override  
   (Segment `sandbox` / `test` / `input_copy` / `output_preview`, oder Env-Root).
4. Desktop- oder Rechnung-Pfade allein werden **nicht** global erlaubt.
5. Keine Hadi-spezifischen Produkt-Defaults; optional  
   `KI_RECHNUNGEN_COPIED_SANDBOX_TEST_ROOTS` für test-/env-scoped Roots.

Geänderte Module:

- `invoice_tool/ui_v2/core_dry_run_contract.py` — gemeinsame Path-Policy
- `invoice_tool/ui_v2/sandbox_processing_gate.py` — Pair-Klassifikation + Safety-Proof-Texte
- `invoice_tool/ui_v2/core_bridge.py` — Delegation an Contract-Policy + klarere Blocker-Texte

---

## Safety rules

| Regel | Status |
|---|---|
| `dry_run=true` | erzwungen |
| `no_mutation=true` | erzwungen |
| `productive_mode_requested=false` | erzwungen |
| `run_once` | nicht aufgerufen |
| Produktiv-/Originalordner | blockiert |
| Desktop/Rechnung global | nicht erlaubt |
| Positives Sandbox-/Test-Signal | erforderlich |

Safety-Proof bei Freigabe:

- Kopierter Sandbox-/Testordner bestätigt
- Originalordner ausgeschlossen
- Produktivmodus gesperrt
- Dry-Run ohne Mutation

---

## Controlled copied real-PDF smoke result

| Feld | Wert |
|---|---|
| Classification | `PASS_PREVIEW_ONLY` |
| PDF count | 5 |
| Review rows | 5 |
| Recognized rows | 0 (OCR/AI absichtlich nicht ausgeführt) |
| Planned destinations | 5 (data-only) |
| Bridge ok | ja |
| Output files | 0 |
| Input hashes | unverändert |

---

## Output folder interpretation

`OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY`

Leerer Output ist hier **erwartet und erfolgreich**, weil Export/Pläne in-memory / data-only bleiben und keine finalen Invoice-PDFs geschrieben werden.  
Das ist nicht derselbe Zustand wie Prompt 10 (Block vor Dry-Run).

---

## Mutation proof

Input SHA-256/Listing before == after.  
Output ohne finale PDFs. Keine Rename/Move/Archive/Delete an Originalen.

---

## run_once proof

Monkeypatch-Counter `run_once == 0`. Produktivpfad nicht erreicht.

---

## No productive processing

Bestätigt. Kein produktiver Modus, keine finalen Writes, keine realen Rechnungsordner.

---

## No real invoice folders

Nur `KI-Rechnungen-Test`. Nicht berührt:

- `/Users/hadi_neu/Desktop/RECHNUNGEN/**`
- `/Users/hadi_neu/Desktop/02_Rechnungseingang/**`

---

## Not SaaS-ready / Not production-ready

Explizit bestätigt. Kein Local-Pilot-Ready-Claim über den Sandbox-Dry-Run hinaus.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_01`
