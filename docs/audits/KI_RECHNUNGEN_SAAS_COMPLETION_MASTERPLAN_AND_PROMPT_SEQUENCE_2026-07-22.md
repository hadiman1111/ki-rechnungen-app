# Audit — SaaS Completion Masterplan and Prompt Sequence

Stand: 2026-07-22  
Task ID: `KI_RECHNUNGEN_SAAS_COMPLETION_MASTERPLAN_AND_PROMPT_SEQUENCE_01`

## 1. Task ID

`KI_RECHNUNGEN_SAAS_COMPLETION_MASTERPLAN_AND_PROMPT_SEQUENCE_01`

## 2. User objection

Der User verwirft die Interpretation „lokale Pilotversion freigegeben mit Limitationen“.

Korrekte Lesart:

- ein lokaler Pilot ist nicht akzeptabel, wenn kein echter Verarbeitungs­lauf möglich ist
- aktueller Stand: **noch nicht lokal pilotfähig**
- Ursache: fehlende sichere Core-Dry-Run-/No-Mutation-API
- SaaS-Reife ist deutlich mehr als lokaler Pilot und braucht einen längeren, gegateten Fertigstellungsplan

## 3. Evidence from current repo state

| Item | Ergebnis |
|------|----------|
| Worktree | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Branch | `main` |
| HEAD (vor diesem Task) | `65a735f3fd7df8d65f5623519e3897680d6cb276` |
| origin/main | identisch, ahead/behind `0/0` |
| Core-Bridge Audit | vorhanden: `docs/audits/KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_SANDBOX_DRY_RUN_PARITY_2026-07-22.md` |
| Core-Bridge Code | Path B: `requires_core_dry_run_contract`; kein Core-Import/-Call |
| `run_once` | schreibt Outputs, archiviert Quellen, App-Support-Artefakte; kein Dry-Run-Contract |
| Alter Release-Tag | `product-v1-local-pilot-2026-07-22` existiert (historisch; Lesart korrigiert) |
| Processing-core dirty | nein |
| Track-A protected dirty/staged | nein |
| Known legacy UI dirty (unstaged) | `invoice_tool/ui_profile_dialog.py`, `invoice_tool/ui_document_rules.py` |

## 4. Why current app is not local-pilot-ready

Track B kann Workspace, Config-Auflösung, Blocker, Originalschutz und Exportvorschau-Struktur zeigen, aber **keinen echten kopierten-PDF-Lauf** über eine sichere Core-Schnittstelle ausführen.

Die Bridge stoppt bewusst vor dem Core. Ohne reale Ergebnisse aus kopierten PDFs fehlt die Kernfähigkeit eines lokalen Piloten.

## 5. Why local pilot must include real copied-file processing

Ohne realen Sandbox-Lauf mit kopierten Dateien bleiben Review, Fehlerfälle, geplante Ziele und Exportvorschau entweder leer, strukturell oder adapter-simuliert — nicht aus echtem Laufzustand. Das ist für einen Pilot inakzeptabel.

## 6. Why SaaS readiness needs a longer plan

SaaS-Reife erfordert Architektur, Auth/RBAC/Tenant-Isolation, persistente Pipelines, Storage/Queue/Workers, Frontend, Ops/Security/Privacy, Billing-Prep und gestaffelte Acceptance-/Production-/Release-Gates. Das ist nicht in einem lokalen UI-v2-Pilot enthalten.

## 7. Chosen number of prompts: 34

Exakt **34** große Cursor-Prompts ab aktuellem Stand, wie spezifiziert. Repo-Evidence rechtfertigt keine kleinere Zahl (fehlende Core-Dry-Run-API + voller SaaS-Scope) und keine Vergrößerung ohne neue Evidenz.

## 8. Summary of phases

1. Functional local pilot (1–6)  
2. Controlled local productive behavior (7–11)  
3. SaaS architecture (12–16)  
4. SaaS backend and processing pipeline (17–22)  
5. SaaS frontend (23–26)  
6. Operations, security, billing, deployment (27–31)  
7. SaaS acceptance and release (32–34)

## 9. Docs created

- `docs/KI_RECHNUNGEN_CURRENT_STATUS_CORRECTION_NOT_LOCAL_PILOT_READY_2026-07-22.md`
- `docs/KI_RECHNUNGEN_SAAS_COMPLETION_MASTERPLAN_2026-07-22.md`
- `docs/KI_RECHNUNGEN_SAAS_COMPLETION_PROMPT_SEQUENCE_2026-07-22.md`
- `docs/audits/KI_RECHNUNGEN_SAAS_COMPLETION_MASTERPLAN_AND_PROMPT_SEQUENCE_2026-07-22.md`

## 10. Confirmations

| Confirmation | Status |
|--------------|--------|
| No code changed | ja (docs-only) |
| No Track A change | ja |
| No processing-core change | ja |
| No productive processing | ja |
| Release tags unchanged | ja (kein neuer Tag, kein Tag-Move) |
| Known legacy UI remain unstaged | ja |

## 11. Auto-run rule recorded

Cursor darf die 34 Prompts nicht blind ohne Stop-Gates ausführen. Jeder Prompt endet mit Tests/Audit/Commit/Push (wenn sicher), Final Classification und exact next task.

## 12. Exact next task recommendation

`KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`

## 13. Corrected current status

`NOT_LOCAL_PILOT_READY_CORE_DRY_RUN_API_REQUIRED`
