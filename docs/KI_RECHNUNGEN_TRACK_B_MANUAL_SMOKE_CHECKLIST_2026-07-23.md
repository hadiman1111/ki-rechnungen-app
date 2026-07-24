# Track-B Manual Smoke Checklist (Prompt 34/34)

**Task ID:** `KI_RECHNUNGEN_TRACK_B_SAAS_READINESS_FINAL_AUDIT_AND_MANUAL_SMOKE_01`  
**Date:** 2026-07-23  
**manual_smoke_status:** `NOT_RUN`  
**Purpose:** Konkrete, wiederholbare manuelle End-to-End-Prüfung der Track-B-Kette bis zum kontrollierten Sandbox-Finalschreiben — ohne produktive Verarbeitung, ohne reale Rechnungsordner.

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**, **nicht production final-write-ready**.

---

## Preconditions (Pflicht)

| Check | Expected |
|---|---|
| Worktree | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Controlled input | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` (5 PDFs) |
| Controlled output | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` |
| UI start | `.venv-flet085/bin/python app_ui_v2.py` |
| Kein `run_once` / kein Produktivpfad | bestätigt |
| Keine realen Rechnungsordner als Input/Output | bestätigt |
| Production final-write | bleibt deaktiviert (`final_write_allowed_for_production=false`) |

Stop immediately if originals are mutated, real invoice folders are selected, or production final-write appears enabled.

---

## Exact steps

Record each step as `PASS` / `PARTIAL` / `FAIL` / `SKIP`.

| # | Step | Expected result | Result | Notes |
|---|---|---|---|---|
| 1 | Start UI: `.venv-flet085/bin/python app_ui_v2.py` | UI-v2 öffnet ohne Crash | | |
| 2 | Select controlled input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` | Input gesetzt; kein realer Rechnungsordner | | |
| 3 | Select controlled output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` | Output gesetzt; getrennt vom Input | | |
| 4 | Run Sandbox-Lauf | Sandbox-Lauf startet/endet ohne Original-Mutation | | |
| 5 | Verify five review items appear | Genau 5 Prüffälle sichtbar | | |
| 6 | Verify LUMITOP amount 476,00 and PayPal | LUMITOP zeigt `476,00`, Zahlungsweg PayPal (oder Guidance dazu) | | |
| 7 | Verify 1A-Bootshop amount 105,75 and PayPal | 1A-Bootshop zeigt `105,75`, PayPal | | |
| 8 | Verify Böttcher 84,39 generic card, not AMEX | Böttcher `84,39` als generic card; **nicht** AMEX | | |
| 9 | Verify Luxvenum 154,95 missing payment_field | Luxvenum `154,95`, `payment_field` missing/unklar | | |
| 10 | Verify Böttcher Storno 68,94 and art=storno | Storno `68,94`, `art=storno` | | |
| 11 | Create/save PayPal rule | PayPal-Regel speicherbar (explizit, nicht auto) | | |
| 12 | Rerun preview | Preview-Rerun ohne Original-Mutation | | |
| 13 | Verify LUMITOP and 1A-Bootshop move from Unklar to PayPal | Beide von Unklar → PayPal | | |
| 14 | Verify generic card remains not AMEX | Generic card bleibt nicht AMEX | | |
| 15 | Accept one safe suggestion | Eine sichere Suggestion akzeptiert; Review-Decision gesetzt | | |
| 16 | Edit one suggestion with invalid slash and verify validation blocks it | Slash/ungültiger Name wird blockiert | | |
| 17 | Build Finalisierungs-Vorschau | Finalization Preview Batch erstellt; Konflikte sichtbar falls vorhanden | | |
| 18 | Create Finalisierungs-Trockenlauf | Dry-Run-Paket unter controlled output (`finalization-dry-run-*`) | | |
| 19 | Trigger Sandbox-Finalschreiben testen | CTA „Sandbox-Finalschreiben testen“; Bestätigung „Nur kontrollierter Test-Output“ / „Originale bleiben unverändert“ | | |
| 20 | Verify sandbox-final-write-* folder exists only under controlled output | Ordner nur unter `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` | | |
| 21 | Verify copied files exist only in sandbox-final-write-* | Kopien nur dort; kein Produktions-Output-Ordner | | |
| 22 | Verify original input PDFs remain unchanged | Input-PDFs unverändert (Pfad, Name, Inhalt/Hash) | | |
| 23 | Verify no files are written to real invoice folders | Keine Schreibzugriffe auf reale Rechnungsordner | | |
| 24 | Verify manifest/audit contain `final_write_allowed_for_production=false` | Manifest/Audit zeigen Production-Final-Write deaktiviert | | |
| 25 | Record overall PASS/PARTIAL/FAIL | Gesamtstatus setzen | | |

---

## Evidence to capture

- Screenshot Review mit 5 Items (LUMITOP 476,00; 1A-Bootshop 105,75; Böttcher generic card not AMEX; Luxvenum missing payment_field; Böttcher Storno art=storno)
- Screenshot nach PayPal rule rerun (LUMITOP + 1A-Bootshop → PayPal)
- Pfad `finalization-dry-run-*` unter controlled output
- Pfad `sandbox-final-write-*` unter controlled output
- Manifest-/Audit-Ausschnitt mit `final_write_allowed_for_production=false`
- Bestätigung: originals unchanged / no real invoice folders / no productive processing

---

## Result recording

| Field | Value |
|---|---|
| Operator | |
| Date/time | |
| HEAD / app version | |
| Overall result | `PASS` / `PARTIAL` / `FAIL` / `NOT_RUN` |
| Unsafe incident? | `no` / describe |
| Production final-write observed enabled? | must be `no` |
| Real invoice folders touched? | must be `no` |

Current audit baseline for Prompt 34: **manual_smoke_status=`NOT_RUN`** (not executed by Product Owner / visible automation in this task). Do not fake PASS.
