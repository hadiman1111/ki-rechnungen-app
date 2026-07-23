# Audit — Track-B Local Pilot Manual Smoke Script

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_01`

## 2. Masterplan position: Prompt 7/34

Prompt 7 von 34 bis echter SaaS-Reife.

## 3. HEAD before/after

- **HEAD before:** `1012f107476a500ee3e5a54d8400b58470742872`
- **HEAD after:** siehe Commit dieses Tasks / `git rev-parse HEAD` im Final Report

## 4. Purpose

Erstellt ein manuelles Smoke-Runbook für den akzeptierten Track-B Local Sandbox Pilot: kopierter Input, separater Output, Dry-Run only, Evidenzcheckliste, Stopregeln. Keine Code-/Runtime-Änderung, keine produktive Verarbeitung, keine realen Rechnungsordner.

## 5. Docs created

- `docs/KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_2026-07-22.md`
- `tests/test_track_b_local_pilot_manual_smoke_script_docs.py`

## 6. Product status before

`TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY`

## 7. Manual smoke scope

- UI-v2 lokal (`app_ui_v2.py`)
- kopierter Sandbox-Eingang
- expliziter separater Sandbox-Ausgang
- sicherer Core-Dry-Run
- Workspace-/Review-/Export-Vorschau beobachten
- Evidenz für Prompt 8 Evidence Intake sammeln
- kein Produktivlauf, kein Originalordner, kein finales Write/Move/Archive/Rename

## 8. Folder safety rules

- Input muss kopierter Sandbox-Ordner sein (empfohlen: `/Users/hadi_neu/Desktop/KI-Rechnungen-Sandbox/input_copy`)
- Output muss expliziter separater Sandbox-Ordner sein (empfohlen: `/Users/hadi_neu/Desktop/KI-Rechnungen-Sandbox/output_preview`)
- Input ≠ Output
- Original-/Produktions-Rechnungsordner verboten
- keine finale Verarbeitung / keine Originalmutation erwartet

## 9. Evidence checklist

Gefordert u. a.: date/time, Startmethode, Input-/Output-Pfad, Dateizahlen before/after, Original-touched, Workspace-Status, recognized/review/error/planned-destination counts, Export-Preview sichtbar, Safety-Proof sichtbar, optional Screenshot, Blocker-Text, Klassifikation
`MANUAL_SMOKE_PASS` | `MANUAL_SMOKE_PASS_WITH_NOTES` | `MANUAL_SMOKE_BLOCKED` | `MANUAL_SMOKE_FAIL_UNSAFE`.

## 10. Stop conditions

Sofortstopp u. a. bei: Original-/Produktivordner-Anforderung, finaler Write/Move/Archive/Rename-Aktion, Schreiben in Originalordner, unerwarteter Mutation von `input_copy`, final umbenannten Rechnungen in `output_preview`, Fake-Success ohne Counts, fehlender Review/Export-Vorschau, Start produktiver Verarbeitung, Änderung realer Rechnungsordner, Unsicherheit bei Ordnerwahl.

## 11. No code/runtime change

Bestätigt — nur Docs + Doc-Test. Keine Änderung an UI-v2 Runtime, Track A, Processing-Core, Scripts, Resources.

## 12. No productive processing

Bestätigt — Runbook verbietet produktive Verarbeitung; dieser Task führt keinen Produktivlauf aus.

## 13. No real invoice folders touched

Bestätigt — keine realen Rechnungsordner verarbeitet oder berührt; nur dokumentierte Sandbox-Pfad-Empfehlungen.

## 14. No release tag changes

Release-Tags unverändert (`product-v1-local-pilot-2026-07-22`, `internal-working-version-2026-07-21`). Keine Tags erstellt/geändert.

## 15. Product status after task

`TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_MANUAL_SMOKE_SCRIPT_READY`

## 16. Remaining prompts: 27

## 17. Exact next task:

`KI_RECHNUNGEN_TRACK_B_MANUAL_SMOKE_EVIDENCE_INTAKE_01`

---

## Diagnosis

### 1. What local sandbox pilot currently supports

- lokaler UI-v2 Sandbox-Pilot nutzbar
- sicherer Core-Dry-Run verdrahtet
- echte Ergebnisbuckets (erkannt / Prüfung / Fehler)
- Review-Flow vorhanden
- Export/Reporting Preview vorhanden
- Originale unverändert; Produktivmodus gesperrt
- Acceptance: `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY`

### 2. What the manual smoke script must verify

- Ordner-Setup (kopierter Input, separater Output)
- UI-Start Track B
- Auswahl Input/Output/Profil/Konfiguration
- Start Sandbox-Dry-Run
- Workspace-/Review-/Export-Beobachtungen
- Mutation Check
- Evidenz + Klassifikation
- Stop bei Unsicherheit/Unsicherheitspfaden

### 3. Which folders are allowed for manual smoke

- kopierte Sandbox-Input-Ordner (z. B. `…/KI-Rechnungen-Sandbox/input_copy`)
- explizite Sandbox-Output-Ordner (z. B. `…/KI-Rechnungen-Sandbox/output_preview`)

### 4. Which folders are forbidden

- reale Produktions-Rechnungsordner
- Originalordner
- identischer Input=Output
- jeder unsichere Pfad

### 5. Which evidence Hadi should capture

Siehe §9 Evidence checklist und Return-Format im Smoke-Script §20.

### 6. Which stop conditions Hadi should use

Siehe §10 Stop conditions / Smoke-Script §16.

### 7. What still remains after manual smoke

- Prompt 8: kontrollierte Evidence Intake nach Hadis Lauf
- danach weitere Masterplan-Prompts (kontrollierter Produktivmodus, Schutz/Backup/Journal, SaaS-Fähigkeiten u. a.)
- verbleibend: **27** Prompts

### 8. Why this is not SaaS-ready and not production-ready

Das Runbook dokumentiert nur einen lokalen Sandbox-Dry-Run-Smoke. Es aktiviert keinen Produktivmodus, keine Cloud/Multi-Tenant/Billing-Fähigkeit, keine Originalverarbeitung und keine finalen Schreibpfade. Explizit: **nicht SaaS-ready**, **nicht production-ready**.
