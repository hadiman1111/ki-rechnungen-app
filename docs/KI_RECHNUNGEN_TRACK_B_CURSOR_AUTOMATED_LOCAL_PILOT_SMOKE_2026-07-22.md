# Track-B Cursor Automated Local Pilot Smoke

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_01`  
**Masterplan:** Prompt 8/34  
**Product status (before):** `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_MANUAL_SMOKE_SCRIPT_READY`  
**Product status (after):** `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_CURSOR_SMOKE_READY`  
**Automated smoke classification:** `CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT`  
**Date:** 2026-07-22

Dieses Dokument beschreibt den **technischen**, durch Cursor ausführbaren Sandbox-Smoke für Track B.  
Es ersetzt **keinen** visuellen manuellen GUI-Smoke durch Hadi.

Explizit: **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Automatisch verifizieren, dass die Track-B-Sandbox-Kette ohne GUI-Klicks sicher lauffähig ist:

- kopierter/synthetischer Sandbox-Input
- separater Sandbox-Output
- sicherer Core-Dry-Run-Pfad
- erzwungene Flags (`dry_run=true`, `no_mutation=true`, `productive_mode_requested=false`)
- echte UI-v2-State-/Bucket-/Export-Vorschau-Logik
- Mutationsnachweis
- kein `run_once`, keine produktive Verarbeitung, keine realen Rechnungsordner

---

## Automated smoke scope

| In scope | Out of scope |
|---|---|
| pytest `tmp_path` Sandbox | Desktop-GUI / manuelle Klicks |
| Track-B Bridge + LocalProcessingAdapter | Track-A UI |
| Fake/deterministisches `CoreDryRunResult` | OCR/AI auf realen Dateien |
| Export-Vorschau aus echtem Run-State | finales Write/Move/Archive/Rename |
| Hash-Vergleich Input before/after | `/Users/hadi_neu/Desktop/RECHNUNGEN/**` |
| Docs + Test | Code-/Runtime-Änderung an Processing-Core |

---

## Why Cursor execution is safe

1. Nur `pytest tmp_path` — keine Originalordner, kein Desktop-`RECHNUNGEN`.
2. `run_once` ist monkeypatched und lässt den Test fehlschlagen, falls aufgerufen.
3. OCR/AI/Network-Pfade sind best-effort monkeypatched und dürfen nicht laufen.
4. Der Dry-Run liefert ein **synthetisches**, aber ehrlich gemapptes Resultat (keine Fake-Produktiv-Claims).
5. Kein Build, kein GUI-Start, kein Produktivmodus.
6. Nur Test- und Dokumentationsdateien sind erlaubt geändert zu werden.

---

## Sandbox input/output

Unter `tmp_path`:

```text
<tmp>/cursor-auto-sandbox/input_copy/     # synthetische PDF-/Text-Platzhalter
<tmp>/cursor-auto-sandbox/output_preview/ # separater Preview-Output (muss leer bleiben)
```

- Input und Output sind **nicht** identisch.
- Kein Desktop-Sandbox-Ordner nötig (pytest `tmp_path` bevorzugt).
- Reale Rechnungsordner sind verboten.

---

## What was tested

1. Sandbox-Root + `input_copy` + `output_preview` werden erzeugt.
2. Mindestens zwei synthetische Dokumente liegen im Input.
3. Track-B-Startpfad (`apply_start_processing` / LocalProcessingAdapter / Core Bridge) erreicht `run_core_dry_run_sandbox`.
4. Request-Flags: `dry_run=true`, `no_mutation=true`, `productive_mode_requested=false`.
5. `run_once` wird nicht aufgerufen.
6. Result-State existiert; Buckets recognized/review/error/planned/warnings/safety-proof sind vorhanden.
7. Export-Vorschau enthält u. a.:
   - Export-Vorschau
   - keine final geschriebenen Dateien
   - Originale unverändert
   - Produktive Verarbeitung gesperrt
   - nicht SaaS-ready / SaaS-Ready ist nicht erreicht
8. Kein Fake-Success ohne Counts/State; keine „final processed“-Sprache.
9. Input-Hashes/Listing after == before.
10. Output enthält keine final umbenannten Rechnungs-PDFs.
11. Realer Rechnungsordner unverändert (falls vorhanden).
12. Track-A-Protection-Test bleibt Teil der Focused-Suite.

---

## What was not visually/manual tested

- Pixel-/Layout-Check der UI-v2 in einem echten Fenster
- Menschliche Lesbarkeit von Statusfarben/Buttons
- Manuelle Ordnerwahl per Folder-Picker
- End-to-end OCR/AI auf echten Scans
- Produktivmodus (bewusst gesperrt)
- SaaS-/Cloud-/Multi-Tenant-Verhalten

Für visuelle Evidenz bleibt das manuelle Runbook (Prompt 7) bzw. der nächste Evidence-Review-Gate (Prompt 9) relevant.

---

## Evidence

| Evidence | Source |
|---|---|
| Automated smoke classification | `CURSOR_AUTOMATED_SMOKE_PASS_WITH_SYNTHETIC_RESULT` |
| Test path | `tests/test_track_b_cursor_automated_local_pilot_smoke.py` |
| Sandbox method | pytest `tmp_path` |
| Core path reached | monkeypatched `run_core_dry_run_sandbox` call recorded |
| Buckets | recognized/review/error/planned/warnings/safety-proof |
| Export preview | `build_export_preview_report` + `render_export_preview_text` |
| Mutation proof | SHA-256 tree digest of `input_copy` |
| Output empty | no files under `output_preview` |
| Real folders | `/Users/hadi_neu/Desktop/RECHNUNGEN` not used; digest unchanged if present |

---

## Mutation proof

Vor dem Sandbox-Lauf wird ein SHA-256-Digest aller Dateien unter `input_copy` gebildet. Nach dem Lauf muss der Digest (und das Listing) identisch sein. `output_preview` darf keine final geschriebenen/umbenannten Rechnungs-PDFs enthalten.

---

## Export preview proof

Die Export-Vorschau wird aus dem **echten** `ProcessingRunState` nach dem Bridge-Lauf erzeugt (nicht aus Hardcoded-Dummy-UI-Text). Sie muss u. a. enthalten:

- `Export-Vorschau`
- `Keine Dateien wurden final geschrieben.`
- `Originale unverändert.`
- `Produktive Verarbeitung gesperrt.`
- `SaaS-Ready ist nicht erreicht.` / Local-Pilot nur Sandbox

Positive Claims (`SaaS-ready`, `production-ready`, `Local-Pilot-Ready`, final processed) sind verboten.

---

## No productive processing

- `productive_mode_requested=false`
- `productive_execution_allowed=false`
- `run_once` geblockt/monitored
- keine finalen Write/Move/Archive/Rename-Aktionen

---

## No real invoice folders

- Kein Zugriff auf `/Users/hadi_neu/Desktop/RECHNUNGEN/**`
- Keine Original-Produktionspfade als Input/Output
- Nur synthetische Platzhalter unter `tmp_path`

---

## Not SaaS-ready

Dieser Smoke prüft nur die lokale Track-B-Sandbox-Kette. Es gibt keine Cloud-, Multi-Tenant-, Billing- oder SaaS-Runtime. Status bleibt: **nicht SaaS-ready**.

---

## Not production-ready

Kein Produktivmodus, keine Originalverarbeitung, keine finalen Schreibpfade, kein Release-Tag-Wechsel. Status bleibt: **nicht production-ready**.

---

## Next manual/user evidence step if still needed

1. Optional: manuellen GUI-Smoke laut Prompt-7-Runbook mit kopiertem Desktop-Sandbox-Ordner ausführen (visuelle Evidenz).
2. Pflicht nächster Masterplan-Schritt:  
   `KI_RECHNUNGEN_TRACK_B_CURSOR_SMOKE_EVIDENCE_REVIEW_AND_NEXT_GATE_01`  
   (Evidence Review + Next Gate; verbleibend: **26** Prompts).

---

## Files in this task

- `tests/test_track_b_cursor_automated_local_pilot_smoke.py`
- `docs/KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_CURSOR_AUTOMATED_LOCAL_PILOT_SMOKE_2026-07-22.md`

Keine Code-/Runtime-Änderung an UI-v2, Track A, Processing-Core, Scripts oder Resources.
