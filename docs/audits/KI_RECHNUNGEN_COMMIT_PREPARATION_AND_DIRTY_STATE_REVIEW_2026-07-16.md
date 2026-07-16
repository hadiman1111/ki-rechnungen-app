# KI_RECHNUNGEN_COMMIT_PREPARATION_AND_DIRTY_STATE_REVIEW_01

Datum: 2026-07-16  
Worktree: `KI-Rechnungen-App`  
Branch: `main`  
HEAD: `6399cb82c5e2dc062691128f232e90df6567146e`  
Upstream: `origin/main` (ahead 2 / behind 0)

## Initial classification

`READY_WITH_PREEXISTING_DIRTY_STATE`

## Final classification

`COMMIT_PREPARATION_REVIEW_PASS_WITH_EXCLUSIONS`

## Preflight (kurz)

| Check | Result |
|---|---|
| Active merge / rebase / cherry-pick | nein |
| Git locks | nein |
| Staged files | 0 |
| Tracked modified | 30 |
| Untracked (gesamt) | ~11382 (davon ~4922 `.venv-flet085`, ~6460 sonst) |
| `.git/AUTO_MERGE` | ja (stale) |
| `.git/MERGE_HEAD` | nein |
| Reale `RECHNUNGEN/**` im Index/Status | nein |
| Commit / Push / Reset / Stash / Clean | nicht ausgeführt |

## Ahead-2

Lokale Commits vor `origin/main` (behalten, nicht umschreiben):

1. `7783f237` — *UI: Add design tokens and refine launcher terminology* (2026-06-01)  
   Dateien: `invoice_tool/gui.py`, `invoice_tool/ui_tokens.py`
2. `6399cb82` — *Add UI v2 shell with streamlined navigation and configuration workflow.* (2026-07-13)  
   Dateien: UI-v2-Paket, `app_ui_v2.py`, Tests/Helper, Self-Check-Skript

Bewertung: erwartete UI-/Launcher-Historie; kein Rewrite; Push erst nach getrennten Dirty-Commits und PO-Freigabe.

## Stale AUTO_MERGE

- Inhalt: Tree-OID `3373496a194c90ac375c9bd3053c82b6af6b791d` (kein Commit)
- Datum Datei: 2026-07-14
- Git meldet keinen aktiven Merge
- Bewertung: **stale**
- Entfernung **nicht** in diesem Task; später nur bei PO-Freigabe:
  - `rm .git/AUTO_MERGE`
- Vor Commit empfohlen (Hygiene), aber kein Blocker für Staging von Arbeitsbaumdateien

## Dirty-State-Gruppen

### A. Core functional (neu + tracked)

Neu u. a.: `recipient_guard.py`, `supplier_routing.py`, `file_lifecycle.py`, `folder_destination.py`, `target_routing.py`, `source_inventory.py`, `app_paths.py`  
Tracked u. a.: `processing.py`, `profile_compiler.py`, `run.py`, `models.py`, `config.py`, `logging_utils.py`, `filename_schema.py`, `extraction.py`, `profile_editor.py`, `profile_config.schema.json`

### B. Tests

Neu: Amazon / Recipient-Duplicate-Anthropic / Lifecycle / Target-Routing / Folder-Destination u. a.  
Tracked-Anpassungen: Schema-/Runtime-/Document-Profile-/Run-Tests

### C. Audit/Docs

Viele `docs/audits/*.md` + `docs/audits/evidence/**`  
Evidence enthält absolute User-Pfade, Rechnungsdateinamen, Run-Logs, Profil-Snapshots → **Commit nur selektiv**

### D. Launcher / UI (vorbestehend / parallel)

Untracked Launcher (`app_main.py`, `app_internal_launcher.py`, `invoice_tool/internal_launcher/**`)  
Dirty UI: `gui.py`, Legacy-UI-Module, `ui_v2/**`, Tokens, `pyproject.toml`, `scripts/build_macos_app.sh`  
→ **nicht** in den Routing-/Lifecycle-Commit mischen

### E. Ausschließen / lokal lassen

- `.venv-flet085/` (~207M)
- `diagnostics/backups_*` (~268M App-Bundle)
- `testing/**` Acceptance-/Tmp-Workspaces inkl. PDFs und lokalen Profilkopien
- Evidence-Rohlogs / Profil-Dumps / stdout mit Pfaden
- Externes Profil unter Application Support (außerhalb Repo)

## Sensitive-Data-Check (Zusammenfassung)

Gefunden in Evidence (nicht voll zitiert):

- absolute lokale Pfade (`/Users/...`)
- echte Rechnungsdateinamen und Routing-Ergebnisse
- Profil-Snapshots mit Karten-/IBAN-Endungen
- Supplier-Strings mit USt-IdNr.-Fragmenten in Logs
- Run-Logs / `output_mapping` / `decision_trace`

Core-Code-Diffs: keine Steuer-IDs / keine API-Keys / keine vollen IBANs erkannt.  
Empfehlung: Evidence-Rohdaten und Profil-Dumps vom Commit ausschließen; nur redigierte Markdown-Berichte.

## External profile (read-only)

- Pfad: `~/Library/Application Support/KI-Rechnungen/profile_config.local.json`
- SHA-256: `9ff8e3bdbe7265bcbe798c275f37b20b7c6336a8456ec2b3220b7888399dff16`
- Compile: `compile_profile_to_rules` → OK (`folder_destinations` vorhanden)
- `recipient_policy`: vorhanden
- Anthropic- / Amazon-Vendor-Regeln: vorhanden (`match_scope=supplier`, Runtime via `supplier_routing`)
- Fallback / Unklar: `target_routing.fallback` + `review_policy.unclear_folder`
- Aktives Scan-Modell: `scan_model_id=rechnungen` (genau ein aktives Scan-Modell-ID-Feld)
- Profil bleibt außerhalb Repo; Backup/Commit-Strategie separat

## Hashes (Schutz / Launcher)

| Artefakt | SHA-256 |
|---|---|
| `invoice_tool/ui_v2/app.py` (WT) | `f97c464d60d61fc0488f795cb91414ed8a3957f5a691fb63f9a2b34c12cfab2a` |
| Externes Profil | `9ff8e3bdbe7265bcbe798c275f37b20b7c6336a8456ec2b3220b7888399dff16` |
| `app_main.py` | `38831cac2c533aaa2c1ecdf7a61976d971c3539da0c7de521c3f1f4e5cfbf6e1` |
| `app_internal_launcher.py` | `b67c5f6398d846aa388a34a008ab9ccea5fd6e81b07d36514f40932c03fd347b` |
| `scripts/run_internal_launcher_flet085.sh` | `25694b24613663efbbc191d0499bafa00f9c0f186b7ac0c1ea92c561980d5fac` |

## Focused tests

Befehl (`.venv`):

```bash
.venv/bin/python -m pytest -q \
  tests/test_amazon_supplier_rule.py \
  tests/test_recipient_duplicate_anthropic_fix.py \
  tests/test_file_lifecycle.py \
  tests/test_target_routing.py \
  tests/test_folder_destination.py \
  tests/test_profile_config_schema.py \
  tests/test_profile_folder_destinations.py \
  tests/test_runtime_rules.py
```

Ergebnis: **142 passed**

## Vorgeschlagene Commit-Gruppen (nicht ausgeführt)

### Commit 1 — Core routing & lifecycle

Stage nur Kernmodule + Schema (siehe Final Report Liste).  
Message-Vorschlag:

```
fix: Recipient-Guard, Supplier-Routing und Duplicate-Lifecycle absichern

Amazon/Anthropic-Regeln und Same-Run-Dubletten laufen über Profil- und Lifecycle-Pfade; Schema/Compiler unterstützen Zielordner und Fallback.
```

### Commit 2 — Tests

Zugehörige neuen/angepassten Tests.  
Message-Vorschlag:

```
test: Regressionen für Recipient-Guard, Amazon/Anthropic und Lifecycle
```

### Commit 3 — Audit Markdown (ohne Evidence-Rohdaten)

Nur ausgewählte `docs/audits/*.md` der relevanten Tasks; **ohne** `docs/audits/evidence/**` mit Logs/Profil-Dumps.  
Message-Vorschlag:

```
docs: Audit-Berichte für Routing-, Amazon- und Controlled-Copy-Runs
```

## Push readiness

- Push **nicht** jetzt
- Ahead-2 später mit neuen Commits möglich, nach Ausschluss sensibler Dateien
- Dirty-State muss vor Push stark reduziert / gruppiert sein
- Stale `AUTO_MERGE` vorher entfernen empfohlen
- Sensible Evidence blockiert einen „alles committen“-Push

## Next task

`KI_RECHNUNGEN_SAFE_COMMIT_EXECUTION_01` — nur nach PO-Freigabe; kein Push ohne separate Freigabe.

## Confirmations

- kein Commit
- kein Push
- kein Reset / Stash / Clean
- keine Änderung realer Rechnungsordner

STOPPED_AFTER_KI_RECHNUNGEN_COMMIT_PREPARATION_AND_DIRTY_STATE_REVIEW — AWAITING_PRODUCT_OWNER_REVIEW
