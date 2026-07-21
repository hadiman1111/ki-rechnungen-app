# KI_RECHNUNGEN_INTERNAL_WORKING_VERSION_FREEZE — 2026-07-21

**Freeze title:** Internal Working Version Freeze (Track A — interne lokale App)  
**Freeze task ID:** `KI_RECHNUNGEN_INTERNAL_WORKING_VERSION_FREEZE_01`  
**Freeze date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Internal Working Version / Freeze

## Freeze commit

**Validated freeze point (code/runtime baseline):**

`51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1`

This SHA is the frozen internal working version for Track A. The freeze *documentation* commit that records this decision may sit one commit ahead of this SHA; the freeze *point* for runtime/behavior remains `51fbf11…`.

## HEAD / origin/main / ahead-behind confirmation (preflight)

| Check | Result |
|---|---|
| Worktree | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Branch | `main` |
| HEAD (before freeze docs commit) | `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1` |
| origin/main (before freeze docs commit) | `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1` |
| `git ls-remote origin refs/heads/main` | `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1` |
| ahead / behind | `0 / 0` |
| Freeze candidate equals HEAD | yes |
| Freeze candidate equals origin/main | yes |
| Staged files | none |
| Active Git operation | none |
| Git locks | none |
| Processing/routing/classification dirty | no |
| `profile_config.local.json` in status | no |
| Real invoice folders in status | no |
| Initial classification | `READY_FOR_INTERNAL_WORKING_VERSION_FREEZE` |

## What is frozen

At commit `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1`:

- Validated processing / routing / classification behavior (including prior routing/payment/document fixes)
- `FULL_250_PDF_ISOLATED_RETEST_PASS`
- GUI Shell Foundation (`GUI_SHELL_FOUNDATION_COMMITTED_AND_PUSHED`)
- GUI Shell Page Modules (`GUI_SHELL_PAGE_MODULES_COMMITTED_AND_PUSHED`)
- GUI Shell Tokens / Wiring (`GUI_SHELL_TOKENS_WIRING_COMMITTED_AND_PUSHED`)
- Build / Foundation for internal standalone path (`BUILD_FOUNDATION_COMMITTED_AND_PUSHED`)
- Safe internal launcher tests (`INTERNAL_LAUNCHER_SAFE_TESTS_COMMITTED_AND_PUSHED`)
- Boundary readiness: `GUI_SHELL_RUNTIME_SMOKE_BUILD_BOUNDARY_READY`
- Legacy UI cleanup-or-freeze decision documented: `LEGACY_UI_CLEANUP_OR_FREEZE_READY` (see companion audit)

## What is explicitly not frozen

- Legacy `invoice_tool/ui_profile_dialog.py` (tracked, may remain dirty)
- Legacy `invoice_tool/ui_document_rules.py` (untracked)
- Untracked UI-v2 scripts / tools under `scripts/**` (local WIP)
- Untracked design / task / historical audit docs unless separately committed later
- `testing/**` and testing PDFs (local fixtures; not part of freeze payload)
- `.venv-flet085/` (and other local venvs)
- Local profiles (`profile_config.local.json` and equivalents)
- Real invoice folders (`/Users/hadi_neu/Desktop/RECHNUNGEN/**`, `/Users/hadi_neu/Desktop/TEST Rechnungen/**`)
- Untracked / mixed local tests that require Flet ≥ 0.85 GUI windows or productive processing

## Dirty-state allowed after freeze

- Local-only WIP may remain dirty or untracked after this freeze.
- The freeze point is the **Git commit** `51fbf11…` (validated baseline), **not** a clean working tree.
- Clean worktree is **not** required.
- Remaining dirty-state must be documented, not blindly cleaned.
- Companion inventory: `docs/audits/KI_RECHNUNGEN_LEGACY_UI_CLEANUP_OR_FREEZE_FOLLOWUP_2026-07-21.md` (buckets A–F).

### Remaining dirty-state summary (observed at freeze documentation time)

| Bucket | Examples |
|---|---|
| Legacy UI | `M invoice_tool/ui_profile_dialog.py`, `?? invoice_tool/ui_document_rules.py` |
| Local venv | `?? .venv-flet085/` |
| Docs / design / tasks | many untracked `docs/audits/*`, `docs/design/`, `docs/design-references/`, `docs/tasks/` |
| Scripts / tools | untracked UI-v2 / flet085 / e2e helpers under `scripts/` |
| Testing | `?? testing/` (~406 PDFs counted), assorted untracked tests |
| Local notes | `?? AGENTS.md` |

## Safety confirmations

- No productive processing
- No real invoice changes
- No PDF commit
- No venv commit
- No private local profile commit
- No processing / routing / classification dirty files at freeze time
- Freeze documentation commit stages **only** the two allowed audit docs under `docs/audits/`
- No code / test / script / resource / PDF / venv / testing files in freeze commit payload

## Operational recommendation

1. **macOS build after freeze** — separate post-freeze build task; not a freeze prerequisite.
2. **Manual GUI smoke after freeze** — validates the frozen artifact; prior boundary already `GUI_SHELL_RUNTIME_SMOKE_BUILD_BOUNDARY_READY`.
3. **No blind cleanup of `testing/**`** — never mass-delete testing PDFs.
4. Legacy UI cleanup only later with an **explicit file list** and PO approval.

## Next tasks

1. Manual GUI smoke (frozen internal app)
2. macOS build smoke (post-freeze)
3. Legacy UI cleanup only with explicit list (leave dirty until then)
4. Optional docs/design redaction before any later commit of historical/design WIP
5. Track B (generic SaaS / UI-v2) remains a separate future track

## Product-track note

- **Track A** — internal local app is frozen at commit `51fbf11e3cfcf79667eb54fb70b4f6cf8ec894a1`.
- **Track B** — generic SaaS / UI-v2 remains a separate future track and is not part of this freeze.

## Related audits

- `docs/audits/KI_RECHNUNGEN_LEGACY_UI_CLEANUP_OR_FREEZE_FOLLOWUP_2026-07-21.md`
