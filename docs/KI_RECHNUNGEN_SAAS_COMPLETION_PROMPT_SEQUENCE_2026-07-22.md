# SaaS-Fertigstellung — Prompt-Sequenz (34)

Stand: 2026-07-22  
Masterplan: `docs/KI_RECHNUNGEN_SAAS_COMPLETION_MASTERPLAN_2026-07-22.md`  
Aktueller Status: `NOT_LOCAL_PILOT_READY_CORE_DRY_RUN_API_REQUIRED`

## Operating Rule (gilt für alle Prompts)

- Cursor läuft nicht endlos ohne Stop-Gates.
- Jeder Prompt: Implementierung (soweit Scope), Tests, Audit, Commit, Push (wenn sicher), dann Stop.
- Jeder Prompt endet mit Final Classification + exact next task.
- Kein „fertig/release/SaaS-ready“-Claim ohne erfüllte Kriterien.
- Track A und reale Originalordner bleiben geschützt, bis ein Prompt sie explizit und sicher adressiert.
- Processing-core nur in Prompts, die das explizit erlauben (ab Prompt 1/2 im Core-Dry-Run-Kontext).

---

## Phase 1 — Functional local pilot

### Prompt 1/34 — `KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Verbindlichen Core-Dry-Run-/Sandbox-API-Contract definieren (Signaturen, No-Mutation-Garantien, Result-Shape, Artefaktgrenzen). |
| Allowed scope | Contract-Docs + ggf. reine Contract-/Typ-Stubs ohne Live-Mutation; kein Track-A-Behavior-Change; kein Produktivlauf. |
| Hard stop | Wenn Contract Mutationen, Archive-Moves oder App-Support-Nebenwirkungen als „dry-run“ zulässt. |
| Expected output | Contract-Dokument + Audit; klare API-Namen/Statuscodes für Track-B-Bridge. |
| Tests/gate | Contract-Konsistenzchecks / gezielte Unit-Stubs falls nötig; `git diff --check`. |
| Next task | `KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01` |

### Prompt 2/34 — `KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Sichere Dry-Run-/No-Mutation-Implementierung gemäß Contract. |
| Allowed scope | Processing-core nur im Dry-Run-Pfad laut Contract; Track A unverändert im Produktivverhalten; keine Originalordner. |
| Hard stop | Jede Mutation von Source/Archive/Output außerhalb Dry-Run-Garantien. |
| Expected output | Implementierte Dry-Run-API + Tests + Audit. |
| Tests/gate | No-mutation tests (tmp sandbox copies); Track-A-Schutzregression. |
| Next task | `KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01` |

### Prompt 3/34 — `KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Track-B Core-Bridge von Path B auf echten Sandbox-Dry-Run verdrahten. |
| Allowed scope | `ui_v2/core_bridge*` und angrenzende Track-B-Wiring-Dateien; kein Track A. |
| Hard stop | Direkter `run_once`-Produktivaufruf; Originalpfade; Fake-Results. |
| Expected output | Bridge ruft Dry-Run-API; UI zeigt echten Laufstatus. |
| Tests/gate | Bridge-/Workspace-Tests; Produktiv weiterhin blockiert. |
| Next task | `KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_01` |

### Prompt 4/34 — `KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Echte Run-Ergebnisse auf erkannt / review / failed / planned destinations mappen. |
| Allowed scope | Track-B Result-/Review-Mapping und UI-Anbindung. |
| Hard stop | Erfundene Dokumentzeilen ohne Core-Ergebnis. |
| Expected output | Review-Flow aus realem Laufzustand. |
| Tests/gate | Mapping-/Review-Tests mit Sandbox-Kopien oder synthetischen Core-Results. |
| Next task | `KI_RECHNUNGEN_TRACK_B_REAL_RUN_EXPORT_REPORTING_PARITY_01` |

### Prompt 5/34 — `KI_RECHNUNGEN_TRACK_B_REAL_RUN_EXPORT_REPORTING_PARITY_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Export-/Reporting-Vorschau an realen Laufzustand anbinden (Parity). |
| Allowed scope | Track-B Export/Reporting; kein DATEV-/Cloud-Produktivexport. |
| Hard stop | Produktivexport-Claim; Daten ohne Run-State. |
| Expected output | Preview aus realem State. |
| Tests/gate | Export/Reporting-Parity-Tests. |
| Next task | `KI_RECHNUNGEN_LOCAL_PILOT_REAL_COPIED_DATA_ACCEPTANCE_GATE_01` |

### Prompt 6/34 — `KI_RECHNUNGEN_LOCAL_PILOT_REAL_COPIED_DATA_ACCEPTANCE_GATE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Abnahme lokaler Pilot mit echten kopierten Daten (10 Mindestkriterien). |
| Allowed scope | Gate-Helfer/Docs/Tests; keine Scope-Erweiterung. |
| Hard stop | Kriterien unvollständig → kein Pilot-Claim. |
| Expected output | Gate-Klassifikation nur bei erfüllten Kriterien. |
| Tests/gate | Acceptance-Suite inkl. real copied sandbox run. |
| Next task | `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_MODE_SAFETY_DESIGN_01` |

---

## Phase 2 — Controlled local productive behavior

### Prompt 7/34 — `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_MODE_SAFETY_DESIGN_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Safety-Design für kontrollierten lokalen Produktivmodus. |
| Allowed scope | Design-/Policy-Docs (+ ggf. reine Typen); keine Live-Produktivfreigabe. |
| Hard stop | Stille Produktivfreigabe. |
| Expected output | Safety-Design mit expliziten Freigabeschritten. |
| Tests/gate | Design-Konsistenz / Doc-Checks. |
| Next task | `KI_RECHNUNGEN_LOCAL_ORIGINAL_PROTECTION_BACKUP_UNDO_RUN_JOURNAL_01` |

### Prompt 8/34 — `KI_RECHNUNGEN_LOCAL_ORIGINAL_PROTECTION_BACKUP_UNDO_RUN_JOURNAL_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Originalschutz, Backup, Undo, Run-Journal. |
| Allowed scope | Lokale Schutz-/Journal-Mechanismen laut Design. |
| Hard stop | Unprotokollierte Originalmutation. |
| Expected output | Schutzpfad + Journal + Undo-Konzept/Implementierung. |
| Tests/gate | Protection/Backup/Undo-Tests. |
| Next task | `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_PROCESSING_CONTROLLED_WIRING_01` |

### Prompt 9/34 — `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_PROCESSING_CONTROLLED_WIRING_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Kontrollierte Verdrahtung lokaler Produktivverarbeitung. |
| Allowed scope | Expliziter Produktivpfad hinter Safety-Gates. |
| Hard stop | Produktiv ohne Backup/Journal/Explicit-Allow. |
| Expected output | Controlled wiring + Audit. |
| Tests/gate | Controlled productive wiring tests. |
| Next task | `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_REVIEW_ERROR_ROLLBACK_TESTS_01` |

### Prompt 10/34 — `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_REVIEW_ERROR_ROLLBACK_TESTS_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Review-/Error-/Rollback-Tests für lokalen Produktivpfad. |
| Allowed scope | Tests + notwendige Fixups im lokalen Produktivpfad. |
| Hard stop | Fehlender Rollback bei Fehlerfällen. |
| Expected output | Harte Testabdeckung. |
| Tests/gate | Review/Error/Rollback-Suite. |
| Next task | `KI_RECHNUNGEN_LOCAL_PRODUCT_VERSION_ACCEPTANCE_GATE_01` |

### Prompt 11/34 — `KI_RECHNUNGEN_LOCAL_PRODUCT_VERSION_ACCEPTANCE_GATE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Abnahme lokale Produktversion (nicht SaaS). |
| Allowed scope | Gate/Docs/Tests. |
| Hard stop | SaaS-/Produktions-Claim. |
| Expected output | Gate-Klassifikation lokale Produktversion. |
| Tests/gate | Local product acceptance suite. |
| Next task | `KI_RECHNUNGEN_SAAS_TARGET_ARCHITECTURE_01` |

---

## Phase 3 — SaaS architecture

### Prompt 12/34 — `KI_RECHNUNGEN_SAAS_TARGET_ARCHITECTURE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | SaaS-Zielarchitektur festlegen (Web/Cloud, Services, Boundaries). |
| Allowed scope | Architecture docs; kein Deploy. |
| Hard stop | Implementierungs- oder Ready-Claim ohne Architektur. |
| Expected output | Target-Architecture-Dokument. |
| Tests/gate | Architektur-Review-Checkliste. |
| Next task | `KI_RECHNUNGEN_SAAS_TENANT_ROLE_PERMISSION_MODEL_01` |

### Prompt 13/34 — `KI_RECHNUNGEN_SAAS_TENANT_ROLE_PERMISSION_MODEL_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Tenant-/Rollen-/Permission-Modell. |
| Allowed scope | AuthZ-Modell-Docs (+ ggf. Schema-Skizzen). |
| Hard stop | Geteilte Mandantendaten ohne Isolationmodell. |
| Expected output | RBAC/Tenant-Modell. |
| Tests/gate | Modell-Konsistenzchecks. |
| Next task | `KI_RECHNUNGEN_SAAS_DOCUMENT_RUN_RESULT_EXPORT_DATA_MODEL_01` |

### Prompt 14/34 — `KI_RECHNUNGEN_SAAS_DOCUMENT_RUN_RESULT_EXPORT_DATA_MODEL_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Persistentes Datenmodell für Document/Run/Result/Export. |
| Allowed scope | Data-model docs / schema drafts. |
| Hard stop | Modell ohne Tenant-Fremdschlüssel/Isolation. |
| Expected output | Data-model Spezifikation. |
| Tests/gate | Schema-/Referenzintegritätschecks (docs/tests). |
| Next task | `KI_RECHNUNGEN_SAAS_SECURITY_ISOLATION_DELETION_AUDIT_MODEL_01` |

### Prompt 15/34 — `KI_RECHNUNGEN_SAAS_SECURITY_ISOLATION_DELETION_AUDIT_MODEL_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Security-, Isolation-, Deletion-, Audit-Modell. |
| Allowed scope | Security/Privacy-Architektur-Docs. |
| Hard stop | Fehlende Lösch-/Export-/Audit-Anforderungen. |
| Expected output | Security/Deletion/Audit-Modell. |
| Tests/gate | Threat-/Privacy-Checkliste. |
| Next task | `KI_RECHNUNGEN_LOCAL_TO_SAAS_MIGRATION_PLAN_01` |

### Prompt 16/34 — `KI_RECHNUNGEN_LOCAL_TO_SAAS_MIGRATION_PLAN_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Migrationsplan Local → SaaS. |
| Allowed scope | Migration docs. |
| Hard stop | Big-Bang ohne Rollback-/Paritätsstrategie. |
| Expected output | Migrationsplan mit Cutover-Gates. |
| Tests/gate | Plan-Vollständigkeitscheck. |
| Next task | `KI_RECHNUNGEN_SAAS_BACKEND_API_CONTRACTS_FOUNDATION_01` |

---

## Phase 4 — SaaS backend and processing pipeline

### Prompt 17/34 — `KI_RECHNUNGEN_SAAS_BACKEND_API_CONTRACTS_FOUNDATION_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Backend-API-Contracts Foundation. |
| Allowed scope | API contracts / skeleton laut Architektur. |
| Hard stop | Endpoints ohne AuthZ/Tenant-Kontext. |
| Expected output | Contract foundation + Audit. |
| Tests/gate | Contract-/OpenAPI-/Schema-Tests. |
| Next task | `KI_RECHNUNGEN_SAAS_UPLOAD_STORAGE_PIPELINE_01` |

### Prompt 18/34 — `KI_RECHNUNGEN_SAAS_UPLOAD_STORAGE_PIPELINE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Upload- und Storage-Pipeline. |
| Allowed scope | Upload/storage services laut Modell. |
| Hard stop | Cross-tenant storage access. |
| Expected output | Upload/storage pipeline. |
| Tests/gate | Upload/isolation tests. |
| Next task | `KI_RECHNUNGEN_SAAS_WORKER_QUEUE_JOB_STATUS_PIPELINE_01` |

### Prompt 19/34 — `KI_RECHNUNGEN_SAAS_WORKER_QUEUE_JOB_STATUS_PIPELINE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Worker/Queue/Job-Status-Pipeline. |
| Allowed scope | Queue/worker/job status. |
| Hard stop | Synchrone Endlosverarbeitung ohne Job-Tracking. |
| Expected output | Job pipeline + status API. |
| Tests/gate | Queue/job lifecycle tests. |
| Next task | `KI_RECHNUNGEN_SAAS_RESULT_REVIEW_ERROR_PERSISTENCE_01` |

### Prompt 20/34 — `KI_RECHNUNGEN_SAAS_RESULT_REVIEW_ERROR_PERSISTENCE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Persistenz für Results, Review, Errors. |
| Allowed scope | Persistence layer für Run-Outcomes. |
| Hard stop | Review nur im Memory ohne Persistenz. |
| Expected output | Persistente Review-/Error-States. |
| Tests/gate | Persistence/review tests. |
| Next task | `KI_RECHNUNGEN_SAAS_EXPORT_REPORTING_API_01` |

### Prompt 21/34 — `KI_RECHNUNGEN_SAAS_EXPORT_REPORTING_API_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Export-/Reporting-API (SaaS). |
| Allowed scope | Export/reporting APIs; Legal-Limits klar. |
| Hard stop | Steuer-/DATEV-Produktivclaim ohne Freigabe. |
| Expected output | Export/reporting API + Limits. |
| Tests/gate | Export API tests. |
| Next task | `KI_RECHNUNGEN_SAAS_BACKEND_E2E_SYNTHETIC_AND_COPIED_DATA_TESTS_01` |

### Prompt 22/34 — `KI_RECHNUNGEN_SAAS_BACKEND_E2E_SYNTHETIC_AND_COPIED_DATA_TESTS_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Backend-E2E mit synthetic + copied data. |
| Allowed scope | E2E tests / harness; keine Real-Originalordner. |
| Hard stop | Echte Originalkundenordner im Testpfad. |
| Expected output | Bestehende Backend-E2E-Suite. |
| Tests/gate | Backend E2E green. |
| Next task | `KI_RECHNUNGEN_SAAS_FRONTEND_AUTH_WORKSPACE_TENANT_UI_01` |

---

## Phase 5 — SaaS frontend

### Prompt 23/34 — `KI_RECHNUNGEN_SAAS_FRONTEND_AUTH_WORKSPACE_TENANT_UI_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Auth-, Workspace-, Tenant-UI. |
| Allowed scope | SaaS frontend auth/workspace/tenant. |
| Hard stop | UI ohne Tenant-Kontext. |
| Expected output | Auth/workspace/tenant UI. |
| Tests/gate | Frontend auth/tenant tests. |
| Next task | `KI_RECHNUNGEN_SAAS_FRONTEND_UPLOAD_AND_RUN_CONTROL_UI_01` |

### Prompt 24/34 — `KI_RECHNUNGEN_SAAS_FRONTEND_UPLOAD_AND_RUN_CONTROL_UI_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Upload- und Run-Control-UI. |
| Allowed scope | Upload/run control UI. |
| Hard stop | Run starten ohne Job-Status-Feedback. |
| Expected output | Upload/run UI verdrahtet. |
| Tests/gate | Upload/run UI tests. |
| Next task | `KI_RECHNUNGEN_SAAS_FRONTEND_REVIEW_CORRECTION_EXPORT_UI_01` |

### Prompt 25/34 — `KI_RECHNUNGEN_SAAS_FRONTEND_REVIEW_CORRECTION_EXPORT_UI_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Review-, Korrektur-, Export-UI. |
| Allowed scope | Review/correction/export UI. |
| Hard stop | Korrekturen ohne Persistenz. |
| Expected output | Review/export UI. |
| Tests/gate | Review/export UI tests. |
| Next task | `KI_RECHNUNGEN_SAAS_FRONTEND_ADMIN_SETTINGS_PROFILE_UI_01` |

### Prompt 26/34 — `KI_RECHNUNGEN_SAAS_FRONTEND_ADMIN_SETTINGS_PROFILE_UI_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Admin-/Settings-/Profile-UI. |
| Allowed scope | Admin/settings/profile UI unter RBAC. |
| Hard stop | Admin-Funktionen ohne Permission-Checks. |
| Expected output | Admin/settings/profile UI. |
| Tests/gate | Admin RBAC UI tests. |
| Next task | `KI_RECHNUNGEN_SAAS_AUTH_RBAC_TENANT_ISOLATION_TEST_GATE_01` |

---

## Phase 6 — Operations, security, billing, deployment

### Prompt 27/34 — `KI_RECHNUNGEN_SAAS_AUTH_RBAC_TENANT_ISOLATION_TEST_GATE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Auth/RBAC/Tenant-Isolation Test-Gate. |
| Allowed scope | Isolation/security tests + Fixes. |
| Hard stop | Cross-tenant Leak. |
| Expected output | Isolation gate passed/failed classification. |
| Tests/gate | Hard isolation suite. |
| Next task | `KI_RECHNUNGEN_SAAS_LOGGING_MONITORING_ERROR_DIAGNOSTICS_01` |

### Prompt 28/34 — `KI_RECHNUNGEN_SAAS_LOGGING_MONITORING_ERROR_DIAGNOSTICS_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Logging, Monitoring, Error Diagnostics. |
| Allowed scope | Observability stack/docs/config. |
| Hard stop | Secrets in Logs. |
| Expected output | Monitoring/diagnostics baseline. |
| Tests/gate | Log redaction / smoke checks. |
| Next task | `KI_RECHNUNGEN_SAAS_BILLING_PLAN_MODEL_PREPARATION_01` |

### Prompt 29/34 — `KI_RECHNUNGEN_SAAS_BILLING_PLAN_MODEL_PREPARATION_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Billing-/Plan-Modell vorbereiten oder klar deferred dokumentieren. |
| Allowed scope | Billing prep docs / hooks; kein Fake-Billing-Claim. |
| Hard stop | „Billing fertig“ ohne echte Integration. |
| Expected output | Plan-Modell oder deferred architecture. |
| Tests/gate | Billing-prep consistency checks. |
| Next task | `KI_RECHNUNGEN_SAAS_PRIVACY_DELETION_DATA_EXPORT_FUNCTIONS_01` |

### Prompt 30/34 — `KI_RECHNUNGEN_SAAS_PRIVACY_DELETION_DATA_EXPORT_FUNCTIONS_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Privacy: Löschung und Datenexport. |
| Allowed scope | Deletion/export functions + docs. |
| Hard stop | Unlöschbare Mandantendaten ohne Ausnahmeprozess. |
| Expected output | Deletion/export capabilities. |
| Tests/gate | Deletion/export tests. |
| Next task | `KI_RECHNUNGEN_SAAS_STAGING_DEPLOYMENT_SMOKE_TESTS_01` |

### Prompt 31/34 — `KI_RECHNUNGEN_SAAS_STAGING_DEPLOYMENT_SMOKE_TESTS_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Staging-Deployment + Smoke Tests. |
| Allowed scope | Staging deploy/smoke; kein Production-Release. |
| Hard stop | Production-Deploy in diesem Prompt. |
| Expected output | Staging smoke report. |
| Tests/gate | Staging smoke suite. |
| Next task | `KI_RECHNUNGEN_SAAS_PILOT_ACCEPTANCE_GATE_01` |

---

## Phase 7 — SaaS acceptance and release

### Prompt 32/34 — `KI_RECHNUNGEN_SAAS_PILOT_ACCEPTANCE_GATE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | SaaS-Pilot-Acceptance-Gate. |
| Allowed scope | Gate/docs/tests. |
| Hard stop | Kriterien offen → kein Pilot-Claim. |
| Expected output | SaaS pilot gate classification. |
| Tests/gate | SaaS pilot acceptance suite. |
| Next task | `KI_RECHNUNGEN_SAAS_PRODUCTION_READINESS_GATE_01` |

### Prompt 33/34 — `KI_RECHNUNGEN_SAAS_PRODUCTION_READINESS_GATE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Production-Readiness-Gate. |
| Allowed scope | Readiness matrix/docs/tests. |
| Hard stop | Security/Privacy/Monitoring offen. |
| Expected output | Production readiness classification. |
| Tests/gate | Production readiness checklist + tests. |
| Next task | `KI_RECHNUNGEN_SAAS_V1_RELEASE_GATE_01` |

### Prompt 34/34 — `KI_RECHNUNGEN_SAAS_V1_RELEASE_GATE_01`

| Feld | Inhalt |
|------|--------|
| Purpose | Finales SaaS-V1-Release-Gate. |
| Allowed scope | Release gate/docs/tests/tag-only if criteria met. |
| Hard stop | Jedes offene Pflichtkriterium → kein Release. |
| Expected output | Release classification nur bei voller Gate-Erfüllung. |
| Tests/gate | Final release suite + audit. |
| Next task | `STOPPED_AFTER_KI_RECHNUNGEN_SAAS_V1_RELEASE_GATE — AWAITING_PRODUCT_OWNER_REVIEW` |

---

## Prompt index (compact)

| # | Task ID |
|--:|---------|
| 1 | `KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01` |
| 2 | `KI_RECHNUNGEN_CORE_DRY_RUN_NO_MUTATION_IMPLEMENTATION_01` |
| 3 | `KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_REAL_SANDBOX_RUN_WIRING_01` |
| 4 | `KI_RECHNUNGEN_TRACK_B_REAL_RUN_RESULT_MAPPING_AND_REVIEW_FLOW_01` |
| 5 | `KI_RECHNUNGEN_TRACK_B_REAL_RUN_EXPORT_REPORTING_PARITY_01` |
| 6 | `KI_RECHNUNGEN_LOCAL_PILOT_REAL_COPIED_DATA_ACCEPTANCE_GATE_01` |
| 7 | `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_MODE_SAFETY_DESIGN_01` |
| 8 | `KI_RECHNUNGEN_LOCAL_ORIGINAL_PROTECTION_BACKUP_UNDO_RUN_JOURNAL_01` |
| 9 | `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_PROCESSING_CONTROLLED_WIRING_01` |
| 10 | `KI_RECHNUNGEN_LOCAL_PRODUCTIVE_REVIEW_ERROR_ROLLBACK_TESTS_01` |
| 11 | `KI_RECHNUNGEN_LOCAL_PRODUCT_VERSION_ACCEPTANCE_GATE_01` |
| 12 | `KI_RECHNUNGEN_SAAS_TARGET_ARCHITECTURE_01` |
| 13 | `KI_RECHNUNGEN_SAAS_TENANT_ROLE_PERMISSION_MODEL_01` |
| 14 | `KI_RECHNUNGEN_SAAS_DOCUMENT_RUN_RESULT_EXPORT_DATA_MODEL_01` |
| 15 | `KI_RECHNUNGEN_SAAS_SECURITY_ISOLATION_DELETION_AUDIT_MODEL_01` |
| 16 | `KI_RECHNUNGEN_LOCAL_TO_SAAS_MIGRATION_PLAN_01` |
| 17 | `KI_RECHNUNGEN_SAAS_BACKEND_API_CONTRACTS_FOUNDATION_01` |
| 18 | `KI_RECHNUNGEN_SAAS_UPLOAD_STORAGE_PIPELINE_01` |
| 19 | `KI_RECHNUNGEN_SAAS_WORKER_QUEUE_JOB_STATUS_PIPELINE_01` |
| 20 | `KI_RECHNUNGEN_SAAS_RESULT_REVIEW_ERROR_PERSISTENCE_01` |
| 21 | `KI_RECHNUNGEN_SAAS_EXPORT_REPORTING_API_01` |
| 22 | `KI_RECHNUNGEN_SAAS_BACKEND_E2E_SYNTHETIC_AND_COPIED_DATA_TESTS_01` |
| 23 | `KI_RECHNUNGEN_SAAS_FRONTEND_AUTH_WORKSPACE_TENANT_UI_01` |
| 24 | `KI_RECHNUNGEN_SAAS_FRONTEND_UPLOAD_AND_RUN_CONTROL_UI_01` |
| 25 | `KI_RECHNUNGEN_SAAS_FRONTEND_REVIEW_CORRECTION_EXPORT_UI_01` |
| 26 | `KI_RECHNUNGEN_SAAS_FRONTEND_ADMIN_SETTINGS_PROFILE_UI_01` |
| 27 | `KI_RECHNUNGEN_SAAS_AUTH_RBAC_TENANT_ISOLATION_TEST_GATE_01` |
| 28 | `KI_RECHNUNGEN_SAAS_LOGGING_MONITORING_ERROR_DIAGNOSTICS_01` |
| 29 | `KI_RECHNUNGEN_SAAS_BILLING_PLAN_MODEL_PREPARATION_01` |
| 30 | `KI_RECHNUNGEN_SAAS_PRIVACY_DELETION_DATA_EXPORT_FUNCTIONS_01` |
| 31 | `KI_RECHNUNGEN_SAAS_STAGING_DEPLOYMENT_SMOKE_TESTS_01` |
| 32 | `KI_RECHNUNGEN_SAAS_PILOT_ACCEPTANCE_GATE_01` |
| 33 | `KI_RECHNUNGEN_SAAS_PRODUCTION_READINESS_GATE_01` |
| 34 | `KI_RECHNUNGEN_SAAS_V1_RELEASE_GATE_01` |
