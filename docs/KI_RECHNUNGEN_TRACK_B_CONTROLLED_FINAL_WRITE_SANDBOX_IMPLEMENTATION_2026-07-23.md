# Track-B Controlled Final Write Sandbox Implementation

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONTROLLED_FINAL_WRITE_SANDBOX_IMPLEMENTATION_01`  
**Masterplan:** Prompt 33/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CONTROLLED_FINAL_WRITE_SANDBOX_IMPLEMENTATION_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.  
Sandbox-Kopien nur unter kontrolliertem Output mit Prefix `sandbox-final-write-`.  
`final_write_allowed_for_production=false` bleibt hart.

---

## Purpose

Implementiert einen kontrollierten Track-B-Sandbox-Final-Write-Pfad: nach Dry-Run-Paket, Gate, Autorisierung und Hash-/Target-/Konflikt-Recheck dürfen freigegebene Quell-PDFs **nur als Kopien** in einen klar gekennzeichneten Sandbox-Ordner geschrieben werden.

Dies ist **kein** produktives Finalschreiben.

---

## Baseline from Prompt 32

- `FinalWriteGate` / `FinalWriteAuthorization` / `FinalWritePlan` Design spezifiziert
- 16 Pflicht-Preconditions und Hard Blockers definiert
- UI-Confirmation-Design und Audit-Felder spezifiziert
- `final_write_execution_available=false` in Prompt 32
- Dry-Run-Package und Finalization Preview Batch vorhanden
- Product status vorher: `TRACK_B_CONTROLLED_FINAL_WRITE_GATE_DESIGN_READY`
- Design commit: `272b8640a763006c2876f71f2eb6c3e4a7316b21`
- HEAD Baseline vor diesem Task: `e995058a9b6ede1d09ed017168db1ec02dd83492`

---

## ControlledFinalWriteSandboxResult model

Modul: `invoice_tool/ui_v2/controlled_final_write_sandbox.py`

Wichtige Felder:

- `sandbox_final_write=true`
- `productive_mode_requested=false`
- `final_write_allowed_for_sandbox` (nur nach Gate)
- `final_write_allowed_for_production=false`
- `final_files_written` / `final_files_written_count`
- `skipped_items` / `blocked_items` / `failures`
- `originals_moved/renamed/archived/deleted=false`
- `source_mutation=false`
- `run_once_called=false`
- `safety_summary`

---

## FinalWriteGateRuntimeCheck model

Modul: `invoice_tool/ui_v2/final_write_gate.py`

Enthält u. a.:

- `gate_status`
- `all_preconditions_passed`
- `blockers` / `warnings`
- `source_hash_recheck_result`
- `target_path_recheck_result`
- `conflict_recheck_result`
- `dry_run_package_link_result`
- `authorization_result`
- `final_write_execution_allowed_for_sandbox`
- `final_write_execution_allowed_for_production=false`
- verknüpfte `FinalWritePlan`-Einträge, Gate und Authorization

---

## Authorization behavior

`build_sandbox_final_write_authorization(...)` verlangt:

- `authorized_by_user=true`
- Scope `selected_items` oder `whole_ready_batch`
- selected item ids
- Acknowledgements inkl. Sandbox-Write, Originale unverändert, nicht Produktion
- Confirmation Phrase, falls konfiguriert

Ohne gültige Autorisierung kein Sandbox-Write.

---

## Sandbox writer behavior

`execute_controlled_final_write_sandbox(...)`:

1. erfordert `sandbox_final_write=true`
2. erfordert kontrollierten Output-Root (Sandbox/Test-Policy)
3. erzeugt Ordner mit Prefix `sandbox-final-write-`
4. lehnt Roots/Ziele außerhalb des controlled output root ab
5. lehnt reale Rechnungsordner-Pfade ab
6. recheckt Source-Hash vor Copy
7. lehnt geänderte Source-Hashes ab
8. lehnt unresolved Duplicate/Conflicts ab
9. lehnt fehlende Dry-Run-Package-/Auth-/Ready-Items ab
10. kopiert Dateien (`shutil.copy2`) — kein Move/Rename/Archive/Delete von Originalen
11. überschreibt bestehende Targets nur bei expliziter Sandbox-Overwrite-Policy
12. schreibt Pre-Write-Audit vor Copies, Post-Write-Audit danach
13. schreibt Manifest JSON/CSV und Begleitartefakte
14. ruft kein `run_once` auf
15. setzt nie `final_write_allowed_for_production=true`

---

## Artifact list

Unter `sandbox-final-write-*`:

- `SANDBOX_FINAL_WRITE_README.md`
- `sandbox-final-write-manifest.json`
- `sandbox-final-write-manifest.csv`
- `pre-write-audit.md`
- `post-write-audit.md`
- `copied-files.md`
- `skipped-items.md`
- `blocked-items.md`
- `failures.md`

README stellt klar: Sandbox Final Write Test, not production output, originals unchanged, copies only, production final write remains disabled.

---

## UI action

Review UI (Track B / UI-v2):

- „Sandbox-Finalschreiben testen“
- „Nur kontrollierter Test-Output“
- „Originale bleiben unverändert“
- zeigt Sandbox-Pfad und Counts (written/skipped/blocked/failures)

Kein CTA „Finales Schreiben ausführen“ ohne Sandbox-/Test-Label.

---

## Preview export integration

Preview-Export-Manifest enthält bei vorhandenem Sandbox-Ergebnis:

- `sandbox_final_write_available`
- `sandbox_final_write_result_id`
- `sandbox_final_write_root`
- `final_write_allowed_for_production=false`
- `originals_moved/renamed/archived/deleted=false`
- `source_mutation=false`

---

## Safety guarantees

- `run_once` nicht aufgerufen
- Input-/Source-Hashes unverändert (Copy only)
- Originale bleiben am Originalpfad
- Output nur unter controlled sandbox output
- kein finales Produktions-Output
- keine realen Rechnungsordner
- Track A / Processing-Core unverändert
- Release-Tags unverändert

---

## What is now proven

- ControlledFinalWriteSandbox executor existiert
- Gate-/Authorization-/Plan-Runtime-Checks greifen
- Sandbox-Copy unter `sandbox-final-write-*` funktioniert
- Pre-/Post-Write-Audit und Manifeste werden geschrieben
- UI exponiert Sandbox-CTA klar getrennt von Produktion
- Preview Export enthält Sandbox-Metadaten
- Production final write bleibt deaktiviert

---

## What is still not proven

- produktives Final Write außerhalb Sandbox
- End-to-End manueller SaaS-Readiness-/Smoke-Abschluss (Prompt 34)
- Archive/Rename von Originalen (bewusst out of scope / verboten)

---

## Test result

Focused Prompt-33 Suite (inkl. Gate-Design, Dry-Run, Preview-Batch, Track-A-Schutz) und UI-v2/SaaS-Suite — siehe Audit.

---

## No productive processing

Ja — nur Sandbox-Kopien nach Gate; kein produktiver `run_once`.

## No real invoice folders

Ja — Path-Policy blockiert reale Rechnungsordner; nur Controlled Test Input/Output.

## Not SaaS-ready

Explizit nicht SaaS-ready.

## Not production-ready

Explizit nicht production-ready.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_SAAS_READINESS_FINAL_AUDIT_AND_MANUAL_SMOKE_01`
