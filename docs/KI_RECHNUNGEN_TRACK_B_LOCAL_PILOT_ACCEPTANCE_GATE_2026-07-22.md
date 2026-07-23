# Track-B Local Pilot Acceptance Gate

**Task ID:** `KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_ACCEPTANCE_GATE_01`  
**Masterplan:** Prompt 6/34  
**Date:** 2026-07-22

## Purpose

Bounded Local-Pilot-Abnahme für den Track-B UI-v2 Sandbox-Flow: Start → sicherer Core-Dry-Run → echte Ergebnisbuckets → Prüffluss → Export-Vorschau. Keine produktive Verarbeitung, keine Originalmutation, kein SaaS-/Production-Claim.

## Acceptance gate result

**PASSED** — Product status:

`TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY`

## Functional acceptance

| # | Kriterium | Ergebnis |
|---|-----------|----------|
| 1 | Track-B kann sicheren Sandbox-Dry-Run starten | PASS |
| 2 | Start erfordert kopierten/Sandbox-Eingang | PASS |
| 3 | Start erfordert expliziten Sandbox-Ausgang | PASS |
| 4 | Start erfordert aktives Profil/Konfiguration | PASS |
| 5 | Ungültige Eingaben erzeugen Blocker, keine Fake-Results | PASS |
| 6 | Identischer Ein-/Ausgang wird abgelehnt | PASS |
| 7 | Originalähnliche Ordner werden abgelehnt | PASS |
| 8 | Produktivmodus wird abgelehnt | PASS |
| 9 | `run_core_dry_run_sandbox` wird im gültigen Fall aufgerufen | PASS |
| 10 | `run_once` wird nicht aufgerufen | PASS |

## Safety acceptance

| # | Kriterium | Ergebnis |
|---|-----------|----------|
| 1 | `dry_run=true` | PASS |
| 2 | `no_mutation=true` | PASS |
| 3 | `productive_mode_requested=false` | PASS |
| 4 | Copied-data-Confirmation nur bei Sandbox-Policy | PASS |
| 5 | Original-folder-exclusion nur bei Boundary-Pass | PASS |
| 6 | Originaldateien in Tests unverändert | PASS |
| 7 | Keine produktive Verarbeitung | PASS |
| 8 | Keine realen Rechnungsordner berührt | PASS |
| 9 | Keine final umbenannten Rechnungen geschrieben | PASS |
| 10 | Export/Reporting bleibt Preview-only | PASS |

## UI acceptance

| # | Kriterium | Ergebnis |
|---|-----------|----------|
| 1 | Workspace zeigt „Prüfung läuft …“ | PASS |
| 2 | Completed/Review/Error/Blocked ehrlich | PASS |
| 3 | Counts sind real | PASS |
| 4 | Review-needed sichtbar als review-needed | PASS |
| 5 | Errors getrennt von Review | PASS |
| 6 | Erkannte nicht fälschlich als Review | PASS |
| 7 | Geplante Ziele nur Vorschau | PASS |
| 8 | Safety-Proof sichtbar | PASS |
| 9 | Export-Vorschau sichtbar | PASS |
| 10 | Finale Produktivaktionen disabled/blocked | PASS |

## Product-status acceptance

- Status: `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY`
- Explizit **nicht** SaaS-ready
- Explizit **nicht** production-ready
- Produktive Verarbeitung **nicht** aktiviert
- Finales Write/Move/Archive/Rename **nicht** aktiviert
- Local Pilot ist **sandbox-only**
- Export-Copy: „Local-Pilot akzeptiert nur Sandbox — nicht produktiv freigegeben.“ / „SaaS-Ready ist nicht erreicht.“

## Protection acceptance

| # | Kriterium | Ergebnis |
|---|-----------|----------|
| 1 | Track-A-geschützte UI unverändert | PASS |
| 2 | Processing-Core unverändert | PASS |
| 3 | `profile_config.local.json` unverändert | PASS |
| 4 | Release-Tags unverändert | PASS |
| 5 | Keine scripts/resources/venv/PDF/real-invoice Files staged | PASS |

## What local pilot sandbox-only means

- UI-v2 kann lokal mit kopierten Sandbox-Ordnern einen sicheren Core-Dry-Run starten.
- Ergebnisse (erkannt / Prüfung / Fehler / Warnungen / geplante Ziele) kommen aus echtem Dry-Run-State.
- Review und Export-Vorschau nutzen denselben State.
- Originale bleiben unverändert; Produktivmodus bleibt gesperrt.

## What local pilot sandbox-only does NOT mean

- Nicht SaaS-ready, nicht multi-tenant, nicht cloud-/billing-ready
- Nicht production-ready, nicht customer-data-ready
- Keine OCR/AI-Produktionspipeline
- Keine finale Verarbeitung / kein finales Umbenennen/Verschieben/Archivieren
- Keine DATEV-/Cloud-Produktivexporte

## Why SaaS readiness is still far away

Nach Prompt 6/34 fehlen u. a. kontrollierter lokaler Produktivmodus mit Schutz/Backup/Journal, echte Multi-Tenant-/Auth-/Billing-Fähigkeit, Cloud-Betrieb, produktive OCR/AI-Pipeline und rechtlich/steuerlich freigegebene Exporte. Der Masterplan führt noch 28 Prompts.

## What remains after Prompt 6/34

Nächster Task: `KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_01` — manuelles Smoke-Skript für den lokalen Sandbox-Pilot, ohne Produktivfreigabe.

## Tests

- `tests/test_ui_v2_local_pilot_acceptance_gate.py` (neu)
- Prompt-3–5-Regressionen + Core-Dry-Run + Track-A-Schutz
- Vollständige `tests/test_ui_v2_*.py` / `tests/test_saas_ui_v2_*.py`
