# SaaS-Fertigstellungsplan — verbindlicher Masterplan

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_SAAS_COMPLETION_MASTERPLAN_AND_PROMPT_SEQUENCE_01`  
Prompt-Sequenz-Dokument: `docs/KI_RECHNUNGEN_SAAS_COMPLETION_PROMPT_SEQUENCE_2026-07-22.md`  
Statuskorrektur: `docs/KI_RECHNUNGEN_CURRENT_STATUS_CORRECTION_NOT_LOCAL_PILOT_READY_2026-07-22.md`

## 1. Scope

Dieser Plan ist die **verbindliche** Fertigstellungsroute vom aktuellen Track-B-Stand bis zur **echten SaaS-Reife**.

Er gilt nur für Planung und Gate-Steuerung. In diesem Task:

- keine Core-Bridge-Implementierung
- keine processing-core-Änderung
- keine Track-A-Änderung
- kein SaaS-Code
- kein Claim auf Pilot- oder SaaS-Reife

## 2. Aktueller Stand (ehrlich)

Track-B UI-v2 liefert eine lokale Shell mit Gates, Profil-/Konfigurationsauflösung, Originalschutz, Produktivsperre und Export-/Reporting-Vorschaustruktur.

Der Processing-Core (`run_once`) ist für Track A nutzbar, aber **kein** sicherer Track-B-Dry-Run-Einstieg.

Die Core-Bridge (Path B) blockiert bewusst mit `requires_core_dry_run_contract`.

## 3. Korrigierter Status

`NOT_LOCAL_PILOT_READY_CORE_DRY_RUN_API_REQUIRED`

- noch nicht lokal pilotfähig
- Core-Dry-Run-Schnittstelle erforderlich
- SaaS-Reife noch nicht erreicht
- Fertigstellungsplan bis SaaS-Reife: **34 große Cursor-Prompts ab aktuellem Stand**

## 4. Definitionen

### 4.1 Lokaler Pilot (Minimum)

Siehe Statuskorrektur §5. Kurz: echter Sandbox-Lauf mit kopierten PDFs, echte Ergebnis-/Review-/Fehlerdarstellung, keine Originalmutation, Exportvorschau aus realem Laufzustand.

### 4.2 Lokale Produktversion

Nach lokalem Pilot: kontrolliertes lokales Produktivverhalten mit Originalschutz, Backup/Undo/Run-Journal, Rollback-Tests und eigener Abnahme. **Nicht** SaaS.

### 4.3 SaaS-Reife (True SaaS readiness)

Mindestens erforderlich:

- echte Verarbeitungspipeline
- sichere Trennung Dry-Run / Produktivlauf
- Web-/Cloud-Architektur
- Authentifizierung
- Rollen und Berechtigungen
- Mandantenisolation
- persistentes Datenmodell
- Dokumentenspeicher
- Upload-Pipeline
- Queue/Worker-Verarbeitung
- Job-Status-Tracking
- persistenter Review-Workflow
- persistentes Export/Reporting
- Audit-Logs
- Löschung / Datenexport
- Monitoring/Logging
- Staging-/Production-Trennung
- Billing/Plan-Modell oder klar zurückgestellte Billing-Architektur
- Security-/Privacy-Dokumentation
- Legal-/Tax-Limitation-Wortlaut
- SaaS-Acceptance-Gate
- Production-Readiness-Gate
- Release-Gate

## 5. Sieben Phasen / 34 Prompts

| Phase | Prompts | Ziel |
|------:|--------:|------|
| 1 Functional local pilot | 1–6 | Core Dry-Run API + Track-B Real-Sandbox-Lauf + lokale Pilot-Abnahme |
| 2 Controlled local productive | 7–11 | Sicheres lokales Produktivverhalten + lokale Produktversions-Abnahme |
| 3 SaaS architecture | 12–16 | Zielarchitektur, Tenant/RBAC, Daten-/Security-Modelle, Migrationsplan |
| 4 SaaS backend & pipeline | 17–22 | API, Upload/Storage, Worker/Queue, Persistence, Export-API, E2E |
| 5 SaaS frontend | 23–26 | Auth/Workspace, Upload/Run, Review/Export, Admin/Settings |
| 6 Ops / security / billing / deploy | 27–31 | Isolation-Gate, Monitoring, Billing-Prep, Privacy, Staging-Smoke |
| 7 SaaS acceptance & release | 32–34 | SaaS-Pilot-, Production-Readiness- und V1-Release-Gate |

Exakte Task-IDs und Stop-Gates: siehe Prompt-Sequenz-Dokument.

Prompt 1/34: `KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`  
Prompt 34/34: `KI_RECHNUNGEN_SAAS_V1_RELEASE_GATE_01`

## 6. Abhängigkeiten (vereinfacht)

```text
Core Dry-Run Contract (1)
  → No-Mutation Implementation (2)
    → Track-B Bridge Wiring (3)
      → Result Mapping / Review (4)
        → Export/Reporting Parity (5)
          → Local Pilot Acceptance (6)
            → Local Productive Design… (7–11)
              → SaaS Architecture (12–16)
                → Backend Pipeline (17–22)
                  → Frontend (23–26)
                    → Ops/Security/Billing/Deploy (27–31)
                      → Acceptance/Release Gates (32–34)
```

Keine Phase darf „fertig“ claimen, bevor ihre Gate-Kriterien erfüllt sind.

## 7. Risikoflächen

| Risiko | Warum kritisch | Gate-Reaktion |
|--------|----------------|---------------|
| `run_once` ohne Dry-Run | mutiert Quellen, schreibt Outputs/Artefakte | Prompt 1–2 Pflicht vor Bridge-Wiring |
| Originalordner | Datenverlust / Compliance | jederzeit Hard-Stop bei Originalpfaden |
| Track-A-Regression | interne App bricht | Track-A-Schutztests in relevanten Gates |
| Fake-Ergebnisse in UI | falsche Pilotwahrheit | keine erfundenen Rows; echte Run-State-Mapping |
| Blind endless Cursor-Lauf | unkontrollierte Scope-/Sicherheitsverletzung | Stop-Gates nach jedem Prompt |
| Vorzeitige SaaS-/Release-Claims | Produktwahrheit zerstört | nur Gate-Klassifikationen nach Kriterien |
| Billing ohne Architektur | spätere Umbaukosten | Prompt 29 nur Vorbereitung, kein Fake-Billing |
| Privacy/Deletion spät | rechtliches Risiko | Prompt 15 + 30 explizit |

## 8. Stop-Gates (verbindlich)

Nach **jedem** Prompt muss Cursor stoppen mit:

1. Tests / Checks ausgeführt
2. Audit-Dokument (soweit im Prompt vorgesehen)
3. Commit (nur erlaubter Scope)
4. Push nur bei sicheren Gates
5. Exact next task ID
6. Exact final classification
7. Kein „fertig/release/SaaS-ready“-Claim ohne erfüllte Kriterien

High-risk Übergänge (mindestens):

- nach Prompt 6 (Local Pilot Acceptance)
- nach Prompt 11 (Local Product Version Acceptance)
- nach Prompt 16 (Migration Plan)
- nach Prompt 22 (Backend E2E)
- nach Prompt 27 (Auth/RBAC/Isolation Gate)
- nach Prompt 32 / 33 / 34 (SaaS Acceptance / Production / Release)

## 9. Abnahmekriterien je Ebene

### 9.1 Local Pilot Gate (Prompt 6)

Nur wenn die 10 Mindestkriterien aus der Statuskorrektur erfüllt sind.

### 9.2 Local Product Version Gate (Prompt 11)

Nur wenn kontrolliertes lokales Produktivverhalten, Schutz/Backup/Undo/Journal und Rollback-Tests greifen — ohne SaaS-Claim.

### 9.3 SaaS V1 Release Gate (Prompt 34)

Nur wenn Architektur, Backend, Frontend, Ops/Security/Privacy und die Gates 32–33 erfüllt sind. Billing darf vorbereitet oder klar deferred sein, aber nicht stillschweigend behauptet werden.

## 10. Warum ein One-Shot-Endless-Lauf unsicher ist

Ein blinder 34-Prompt-Dauerlauf:

- überspringt Stop-Gates und PO-Review
- vermischt Core-, Track-A-, SaaS- und Deploy-Risiken
- begünstigt vorzeitige „fertig“-Claims
- erschwert Auditierbarkeit und Rollback
- kann Originalschutz / Dry-Run-Trennung unter Druck verletzen

Deshalb: **volle Sequenz ist geplant**, aber **Ausführung ist schrittweise**.

## 11. Auto-Run / Operating Rule für Cursor

Cursor darf die 34 Prompts **nicht** blind ohne Stop-Gates durchlaufen.

Stattdessen:

- Der Masterplan definiert die volle Sequenz.
- Jeder Prompt ist ein großer ausführbarer Block.
- Innerhalb eines Prompts: maximale Automatisierung (Implementierung, Tests, Audit, Commit, Push — soweit erlaubt und sicher).
- Jeder Prompt endet mit Final Classification und exact next prompt.
- Der nächste Prompt wird danach gesendet.
- Kein Prompt darf Readiness claimen, wenn Acceptance-Kriterien fehlen.
- High-risk Übergänge brauchen explizite Gate-Klassifikation.
- Verbotene Sprache bis Gate-Erfüllung: „lokale Pilotversion ist fertig“, „Produktversion 1 ist fertig“, „SaaS-ready“, „produktionsreif“, „fertiges SaaS“, „Release abgeschlossen“ (außer klar als korrigierter Alt-Status).

## 12. Wie Cursor pro Prompt vorgehen soll

1. Preflight (Worktree, HEAD, staged, locks, dirty-Schutzflächen)
2. Erlaubten Scope lesen
3. Nur erlaubte Dateien ändern
4. Tests/Gates im Prompt ausführen
5. Audit schreiben
6. Explizit stagen (kein `git add .` / `-A`)
7. Commit mit vorgesehener Message
8. Push nur bei Safe-Gates
9. Stoppen mit Classification + next task

## 13. Acceptance Language (verbindlich)

Korrekt:

- „noch nicht lokal pilotfähig“
- „Core-Dry-Run-Schnittstelle erforderlich“
- „SaaS-Reife noch nicht erreicht“
- „Fertigstellungsplan bis SaaS-Reife“
- „34 große Cursor-Prompts ab aktuellem Stand“

## 14. Nächster Schritt

Sofort ausführbar: **Prompt 1/34**  
`KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`
