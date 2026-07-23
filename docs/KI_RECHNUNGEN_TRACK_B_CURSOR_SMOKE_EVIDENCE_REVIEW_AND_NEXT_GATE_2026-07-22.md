# Track-B Cursor Smoke Evidence Review and Next Gate

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_01`  
**Masterplan:** Prompt 9/34  
**Product status (before):** `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_CURSOR_SMOKE_READY`  
**Product status (after):** `TRACK_B_CURSOR_SMOKE_EVIDENCE_ACCEPTED_SYNTHETIC_LIMITATION_DISCLOSED`  
**Evidence classification:** `TECHNICAL_CURSOR_SMOKE_ACCEPTED_WITH_SYNTHETIC_LIMITATION`  
**Date:** 2026-07-22

Dieses Dokument bewertet die Evidenz aus Prompt 8 (Cursor Automated Local Pilot Smoke).  
Es ist ein **read-only/docs** Gate: keine produktive Verarbeitung, keine realen Rechnungsordner, kein GUI-Lauf, kein Build.

Explizit: **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

1. Prompt-8-Evidenz auf Existenz, Sync und ehrliche Limitation prüfen.
2. Sicherstellen, dass der automatisierte Cursor-Smoke nicht als voller visueller GUI-/Manual-Smoke oder Real-PDF-Qualitätsnachweis überclaimt wird.
3. Den nächsten sicheren Track-B-Validierungsschritt festlegen.

---

## Prompt 8 evidence reviewed

| Artefakt | Pfad | Status |
|---|---|---|
| Smoke-Doc | `docs/KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md` | vorhanden |
| Audit | `docs/audits/KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md` | vorhanden |
| Test | `tests/test_track_b_cursor_automated_local_pilot_smoke.py` | vorhanden |
| Commit | `54b33aed42a8b8862dc90e7104a42e78d238fb4a` | auf `origin/main`, Ancestor von HEAD |
| Classification (Prompt 8) | `CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT` | bestätigt |

Zusätzlicher Kontext gelesen:

- `docs/KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_2026-07-22.md`
- `docs/KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_ACCEPTANCE_GATE_2026-07-22.md`
- `docs/KI_RECHNUNGEN_TRACK_B_EXPORT_REPORTING_PREVIEW_POLISH_2026-07-22.md`

---

## Sync status

| Check | Result |
|---|---|
| Worktree | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Branch | `main` |
| HEAD | `54b33aed42a8b8862dc90e7104a42e78d238fb4a` |
| local `origin/main` | identisch zu HEAD |
| remote `origin/main` (`git ls-remote`) | identisch zu HEAD |
| ahead/behind | `0/0` |
| staged files | keine |
| active Git operation | nein |
| Git locks | keine |
| Prompt-8-Commit Ancestor von HEAD/`origin/main` | ja |
| Release-Tags geändert | nein |

Bekannter ungestaged Legacy-/Nebenstatus bleibt unberührt (u. a. `invoice_tool/ui_profile_dialog.py`). Keine Track-A-geschützten UI-Dateien staged/dirty im Sinne dieses Gates; kein `processing-core`-Dirty. `/Users/hadi_neu/Desktop/RECHNUNGEN` erscheint nicht in `git status`.

---

## Evidence classification

`TECHNICAL_CURSOR_SMOKE_ACCEPTED_WITH_SYNTHETIC_LIMITATION`

Begründung: Prompt 8 belegt die technische Track-B-Sandbox-State-/Bucket-/Export-/No-Mutation-Kette zuverlässig, nutzt aber ein deterministisches Fake-`CoreDryRunResult`. Deshalb technische Akzeptanz mit offener synthetischer Limitation — nicht „fully real sandbox“, nicht incomplete, nicht unsafe.

---

## What the Cursor smoke proves

- Technische Sandbox-Kette über pytest `tmp_path` (`cursor-auto-sandbox/input_copy` + `output_preview`)
- Erreichen von `run_core_dry_run_sandbox` über Track-B Bridge/Adapter
- Flags: `dry_run=true`, `no_mutation=true`, `productive_mode_requested=false`
- Result-State und Buckets: recognized / review / error / planned / warnings / safety-proof
- Export-Vorschau aus echtem Run-State (keine final geschriebenen Dateien, Originale unverändert, produktive Verarbeitung gesperrt)
- Mutation proof: Input-Digest before/after unverändert; `output_preview` leer
- `run_once` nicht aufgerufen (Monkeypatch/Counter)
- OCR/AI/Network best-effort geblockt / Fake-Dry-Run ohne echte Extraktion
- Keine realen Rechnungsordner als Input/Output
- Keine produktive Verarbeitung
- Track-A-Protection bleibt Teil der Focused Suite
- Explizite Nicht-Claims: nicht SaaS-ready, nicht production-ready

---

## What it does not prove

- Visuelle GUI-Usability durch einen Menschen (kein voller visueller manueller GUI-Smoke)
- Real-PDF-Parsing-Qualität auf kopierten echten Rechnungen
- OCR/AI-Extraktionsqualität
- Produktivverarbeitung / finale Write/Move/Archive/Rename
- SaaS-Reife / Production-Reife
- Cloud-/Multi-Tenant-/Billing-Verhalten

---

## Synthetic limitation

Prompt 8 verwendet ein **deterministisches Fake-`CoreDryRunResult`** sowie synthetische Platzhalter-Dokumente unter `tmp_path`.

Damit ist bewiesen: technische State-/Mapping-/Export-/Safety-Kette.  
Damit ist **nicht** bewiesen: echte Dokumentqualität, visuelle GUI, oder produktive Verarbeitungsreife.

Die Limitation ist in Doc, Audit und Test von Prompt 8 ehrlich ausgewiesen (`CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT`).

---

## Safety conclusion

- Automated Cursor smoke als **technische Sandbox-Evidenz** akzeptiert.
- Synthetic-result Limitation ausdrücklich disclosed.
- Keine produktive Verarbeitung im Review.
- Keine realen Rechnungsordner verwendet oder verarbeitet.
- Keine Overclaims zu visuellem GUI-Smoke, SaaS-ready oder production-ready.
- Release-Tags unverändert.
- Nächste Validierungsschicht erforderlich (kopierte Real-PDFs in kontrollierter Sandbox).

---

## Next gate decision

Gewählt (genau eine):

`KI_RECHNUNGEN_TRACK_B_CONTROLLED_COPIED_REAL_PDF_SANDBOX_SMOKE_01`

Begründung: Prompt 8 beweist die technische Kette mit synthetischem Resultat; der sinnvolle nächste sichere Schritt ist ein kontrollierter Sandbox-Smoke mit **kopierten** realen PDFs — weiterhin ohne Originalordner, ohne produktive Verarbeitung, ohne finale Schreibpfade.

Nicht gewählt in diesem Gate:

- `KI_RECHNUNGEN_TRACK_B_MANUAL_VISUAL_SMOKE_EVIDENCE_INTAKE_01` (optional später für menschliche GUI-Evidenz)
- `KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_REPAIR_OR_RERUN_PLAN_01` (nicht nötig; Evidenz ist akzeptiert)

---

## Not SaaS-ready / not production-ready

Dieser Evidence Review ändert die Reife nicht. Status bleibt:

- **nicht SaaS-ready**
- **nicht production-ready**

Local Pilot bleibt Sandbox-only; nächster Schritt ist kontrollierte Real-PDF-Sandbox-Validierung, nicht Produktivfreigabe.

---

## Files in this task

- `docs/KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_2026-07-22.md`
- `tests/test_track_b_cursor_smoke_evidence_review_docs.py`

Keine Code-/Runtime-Änderung an UI-v2, Track A, Processing-Core, Scripts oder Resources.
