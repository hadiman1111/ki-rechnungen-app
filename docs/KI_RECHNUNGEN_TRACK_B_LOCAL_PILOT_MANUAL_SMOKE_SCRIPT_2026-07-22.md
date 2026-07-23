# Track-B Local Pilot — Manual Smoke Script (Sandbox only)

**Task ID:** `KI_RECHNUNGEN_TRACK_B_LOCAL_PILOT_MANUAL_SMOKE_SCRIPT_01`
**Masterplan:** Prompt 7/34
**Product status (before this runbook):** `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY`
**Product status (after this docs task):** `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY_MANUAL_SMOKE_SCRIPT_READY`
**Date:** 2026-07-22

Dieses Dokument ist ein manuelles Smoke-Runbook für Hadi.
Es beschreibt einen sicheren Sandbox-Pilottest.
Es führt **keinen** echten Smoke auf realen Rechnungsordnern aus.

---

## 1. Title

Track-B Local Pilot Manual Smoke Script — kopierter Sandbox-Input, separater Sandbox-Output, Dry-Run only.

## 2. Scope

Dieses Runbook gilt nur für den akzeptierten Track-B Local Sandbox Pilot:

- UI-v2 lokal starten (`app_ui_v2.py`)
- kopierten Sandbox-Eingang nutzen
- expliziten Sandbox-Ausgang nutzen
- sicheren Core-Dry-Run starten
- Workspace-/Review-/Export-Vorschau beobachten
- Evidenz für Prompt 8/34 (`KI_RECHNUNGEN_TRACK_B_MANUAL_SMOKE_EVIDENCE_INTAKE_01`) sammeln

Dieses Runbook ist **kein**:

- Implementierungsauftrag
- Produktivlauf
- SaaS-/Cloud-/Multi-Tenant-Test
- OCR/AI-Produktionslauf auf Originalen
- finales Write/Move/Archive/Rename

Explizit: **nicht SaaS-ready**, **nicht production-ready**.

## 3. Preconditions

Vor Start müssen alle Punkte wahr sein:

1. Arbeitverzeichnis: `KI-Rechnungen-App` (Track-B-Repo).
2. Product status dokumentiert: `TRACK_B_LOCAL_PILOT_ACCEPTED_SANDBOX_ONLY`.
3. Acceptance Gate Prompt 6 vorhanden und PASSED.
4. Nur **kopierte**, nicht-kritische Sample-Dateien als Input.
5. Separater, leerer oder explizit für Preview vorgesehener Sandbox-Output.
6. Aktives Profil + aktive Konfiguration in UI-v2 verfügbar.
7. Kein Produktivmodus, kein Originalordner, kein realer Produktionspfad.
8. Hadi hat Zeit, bei Unsicherheit sofort zu stoppen.

## 4. Forbidden actions

**Verboten während dieses Smoke:**

- reale Produktions-Rechnungsordner als Input wählen
- Originalordner direkt verwenden
- Input und Output identisch setzen
- produktive Verarbeitung starten oder aktivieren
- finales Write / Move / Archive / Rename erwarten oder auslösen
- Originale umbenennen, verschieben, löschen oder archivieren
- `python -m invoice_tool.run` / `run_once` auf realen Ordnern
- OCR/AI absichtlich auf realen Originalpfaden starten
- `flet build` / `scripts/build_macos_app.sh`
- Release-Tags ändern oder erstellen
- Track-A (`app_main.py` / Legacy-UI) für diesen Smoke verwenden
- unsichere Ordnerwahl „ausprobieren“ ohne Stopp

Bei Unsicherheit über einen Ordnerpfad: **sofort stoppen**.

## 5. Folder setup

Empfohlene sichere Beispielpfade:

```text
/Users/hadi_neu/Desktop/KI-Rechnungen-Sandbox/input_copy
/Users/hadi_neu/Desktop/KI-Rechnungen-Sandbox/output_preview
```

Einmalig vorbereiten (Finder oder Terminal):

```bash
mkdir -p "/Users/hadi_neu/Desktop/KI-Rechnungen-Sandbox/input_copy"
mkdir -p "/Users/hadi_neu/Desktop/KI-Rechnungen-Sandbox/output_preview"
```

Regeln:

- `input_copy` = kopierter Sandbox-Eingang
- `output_preview` = expliziter separater Sandbox-Ausgang
- beide Pfade müssen existieren und Ordner sein
- Pfade müssen **verschieden** sein
- keine Original-/Produktionsordner darunter mappen

## 6. Input copy rule

1. Wähle nur eine **kleine, nicht-kritische** Sample-Menge (wenige PDFs/Belege).
2. **Kopiere** sie nach `input_copy` — verschiebe keine Originale.
3. Originale bleiben unberührt und außerhalb dieses Smoke.
4. Zähle Dateien in `input_copy` **vor** dem Lauf und notiere die Zahl.
5. Der UI-Eingang darf nur `input_copy` (oder gleichwertiger kopierter Sandbox-Ordner) sein.

Forbidden Input examples:

- echte Kunden-/Mandanten-Rechnungsordner
- produktive Archiv-/Eingangsordner
- irgendein Ordner, bei dem Unsicherheit besteht, ob es ein Original ist

## 7. Output sandbox rule

1. Output muss ein **expliziter separater** Sandbox-Ordner sein (z. B. `output_preview`).
2. Output darf **nicht** dem Input entsprechen.
3. Output darf **kein** Original-/Produktionsordner sein.
4. Erwartung: Preview-/Dry-Run-Daten only — **keine** final umbenannten Rechnungen als Produktergebnis.
5. Nach dem Lauf: prüfen, dass keine unerwarteten finalen Schreibvorgänge entstanden sind.

## 8. UI start rule

Track-B UI-v2 starten — **nicht** Track A:

```bash
cd "/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
.venv/bin/python app_ui_v2.py
```

Falls lokal das Flet-0.85-Venv üblich ist:

```bash
.venv-flet085/bin/python app_ui_v2.py
```

Startregeln:

- Einstieg: `app_ui_v2.py`
- Nicht starten: `app_main.py`, Internal Launcher für Produktivabsicht, Build-Skripte
- Notiere die verwendete Startmethode in der Evidenz

## 9. Step-by-step smoke procedure

Copy-paste Checkliste — der Reihe nach:

1. **Sandbox-Ordner vorbereiten**
   `input_copy` mit kleiner Kopie füllen; `output_preview` leer/explizit vorsehen.
2. **Dateizahl Input vor Lauf** notieren.
3. **UI-v2 starten** mit `app_ui_v2.py` (siehe §8).
4. **Workspace öffnen** (Hauptarbeitsfläche).
5. **Eingangsordner wählen** → nur kopierter Sandbox-Pfad (`input_copy`).
6. **Ausgabeordner wählen** → separater Sandbox-Pfad (`output_preview`).
7. **Profil + Konfiguration** aktiv/ausgewählt prüfen.
8. **Sandbox-Lauf starten** (Button-Label: `Sandbox-Lauf starten`).
9. **Während/nach Start beobachten:** Status „Prüfung läuft …“, danach ehrlicher Abschluss-/Prüf-/Fehler-/Blocker-Status.
10. **Workspace-Beobachtungen** nach §10 prüfen und notieren.
11. **Review-Bereich** öffnen und nach §11 prüfen.
12. **Export-Vorschau** nach §12 prüfen.
13. **Mutation Check** nach §13 (Input-Dateizahl nach Lauf, Originale unberührt).
14. Bei Stop-Bedingung (§16) sofort beenden und als Blocker/Fail klassifizieren.
15. Evidenz (§14) ausfüllen und Return-Format (§20) zurückgeben.

## 10. Expected workspace observations

Erwartet nach gültigem Sandbox-Dry-Run:

- Zwischenstatus: `Prüfung läuft …`
- Endstatus ehrlich, z. B.:
  - `Sandbox-Lauf abgeschlossen.`
  - `Sandbox-Lauf mit Prüffällen abgeschlossen.`
  - `Sandbox-Lauf fehlgeschlagen.`
  - oder kompakter Blocker-Text bei ungültiger Auswahl
- reale Counts sichtbar (erkannt / Prüfung / Fehler — Zahlen, kein Fake-Success ohne Counts)
- Safety-Proof sichtbar:
  `Originale unverändert · Produktiv gesperrt · Export Vorschau`
- geplante Ziele nur als Vorschau/Daten, nicht als finale Schreibbestätigung
- produktive Finalaktionen disabled/blocked

Nicht erwartet:

- Fake-Success ohne Counts
- „Produktiv fertig“ / finales Archivieren
- Schreiben in Originalordner

## 11. Expected review observations

Im Review-/Prüfbereich:

- Prüffälle aus dem realen Dry-Run-State (keine erfundenen Demo-Dokumente)
- Review getrennt von Errors
- erkannte Fälle nicht fälschlich als Review gemischt
- Hinweis auf keine Dateimutation / keine finale Freigabe
- leichte Export-Vorschau-Summary möglich, aber **preview-only**
- finale Approve/Write-Aktionen bleiben disabled/blocked

Wenn kein Prüffall vorliegt: ehrlicher Empty-State ist OK — kein erfundes Dokument.

## 12. Expected export/reporting observations

In Export-Vorschau / Reporting Preview:

- Bereich/Titel mit Export-Vorschau sichtbar
- Preview-Text sichtbar (ja/nein in Evidenz notieren)
- Sandbox-Quell-/Zielpfad gespiegelt (wenn Lauf vorhanden)
- Counts / Safety-Hinweise aus dem Dry-Run-State
- Wording bleibt sandbox-only / nicht produktiv freigegeben
- kein produktiver DATEV-/Cloud-Export
- keine finalen Produktivdateien als Claim

## 13. Mutation check

Nach dem Lauf **zwingend**:

1. Dateizahl in `input_copy` **nach** dem Lauf = Dateizahl **vor** dem Lauf.
2. Dateinamen/Inhalte in `input_copy` nicht unerwartet geändert/verschwunden.
3. Kein realer Original-/Produktionsordner wurde berührt.
4. `output_preview` enthält keine final umbenannten Produktivrechnungen als Schreibziel-Ergebnis.
5. Safety-Proof bleibt sichtbar / konsistent mit „Originale unverändert · Produktiv gesperrt · Export Vorschau“.

Jeder Verstoß → sofort stoppen → `MANUAL_SMOKE_FAIL_UNSAFE` oder `MANUAL_SMOKE_BLOCKED`.

## 14. Evidence checklist

Hadi muss notieren:

| Feld | Wert |
|------|------|
| date/time | |
| app start method | z. B. `.venv/bin/python app_ui_v2.py` |
| input folder path | |
| output folder path | |
| number of files in copied input before | |
| number of files in copied input after | |
| whether any original folder was touched | yes/no |
| workspace status text | |
| recognized count | |
| review count | |
| error count | |
| planned destination count | |
| export preview text visible | yes/no |
| safety proof visible | yes/no |
| screenshot optional | path or n/a |
| blocker/error text if any | |
| final classification | siehe unten |

Erlaubte Endklassifikationen (genau eine):

- `MANUAL_SMOKE_PASS`
- `MANUAL_SMOKE_PASS_WITH_NOTES`
- `MANUAL_SMOKE_BLOCKED`
- `MANUAL_SMOKE_FAIL_UNSAFE`

## 15. Failure/blocker checklist

Als Blocker/Fail markieren, wenn:

- [ ] App verlangt/zeigt produktiven Originalordner als Startvoraussetzung
- [ ] App bietet finale Write/Move/Archive/Rename-Aktion an und wirkt ausführbar
- [ ] App schreibt in Originalordner
- [ ] Dateien in `input_copy` verschwinden oder ändern sich unerwartet
- [ ] `output_preview` erhält final umbenannte Rechnungen statt Preview-only
- [ ] Workspace zeigt Fake-Success ohne Counts
- [ ] Review- oder Export-Vorschau fehlt vollständig trotz erfolgreichem Lauf
- [ ] produktive Verarbeitung startet
- [ ] irgendein realer Rechnungsordner ändert sich
- [ ] Unsicherheit bei der Ordnerauswahl

## 16. Stop rules

**Sofort stoppen** bei:

1. App fragt nach / akzeptiert produktivem Originalordner als Input.
2. App bietet finale Write/Move/Archive/Rename-Aktion an.
3. App schreibt in einen Originalordner.
4. `input_copy`-Dateien verschwinden/ändern sich unerwartet.
5. `output_preview` erhält final umbenannte Rechnungen statt Preview-only.
6. Workspace zeigt Fake-Success ohne Counts.
7. Review/Export-Vorschau fehlt vollständig.
8. Produktive Verarbeitung startet.
9. Irgendein realer Rechnungsordner ändert sich.
10. Unsicherheit über Ordnerauswahl.

Stop-Verhalten:

- UI schließen
- keine weiteren Ordner wählen
- keine „Reparaturversuche“ auf Originalen
- Evidenz mit Blocker-/Fail-Klassifikation zurückgeben

## 17. Cleanup notes

Nach dem Smoke (nur Sandbox):

- Sandbox-Ordner dürfen bleiben für Prompt-8 Evidence Intake.
- Originale wurden nie verwendet → kein Original-Cleanup nötig.
- Keine Git-Operationen für diesen manuellen Smoke nötig.
- Keine Tags erstellen/ändern.
- Optional: `output_preview` leeren, wenn nur lokale Preview-Artefakte entstanden sind — **niemals** Originale anfassen.

## 18. What this proves

Wenn `MANUAL_SMOKE_PASS` / `MANUAL_SMOKE_PASS_WITH_NOTES`:

- lokaler UI-v2 Sandbox-Pilot ist manuell bedienbar
- kopierter Input + separater Output funktionieren im Dry-Run-Pfad
- Workspace zeigt ehrliche Status/Counts/Safety-Proof
- Review-Buckets und Export-Vorschau sind beobachtbar
- Originale bleiben unverändert
- produktive Verarbeitung bleibt gesperrt

## 19. What this does not prove

Dieses Smoke beweist **nicht**:

- SaaS-ready
- production-ready
- cloud-/multi-tenant-/billing-ready
- freigegebene produktive Verarbeitung
- finales Write/Move/Archive/Rename
- sichere Verarbeitung echter Originalordner
- produktive OCR/AI-Pipeline
- DATEV-/Cloud-Produktivexport

Nach diesem Runbook-Task bleiben noch **27** Prompts bis echter SaaS-Reife.
Nächster Task nach Hadis Lauf: `KI_RECHNUNGEN_TRACK_B_MANUAL_SMOKE_EVIDENCE_INTAKE_01`.

## 20. Exact return format Hadi should paste back

Bitte exakt ausfüllen und zurückgeben:

```text
MANUAL_SMOKE_EVIDENCE
date_time:
app_start_method:
input_folder_path:
output_folder_path:
files_in_copied_input_before:
files_in_copied_input_after:
original_folder_touched: yes|no
workspace_status_text:
recognized_count:
review_count:
error_count:
planned_destination_count:
export_preview_text_visible: yes|no
safety_proof_visible: yes|no
screenshot_optional:
blocker_or_error_text:
final_classification: MANUAL_SMOKE_PASS | MANUAL_SMOKE_PASS_WITH_NOTES | MANUAL_SMOKE_BLOCKED | MANUAL_SMOKE_FAIL_UNSAFE
notes:
```
