# Track-B Real-PDF GUI Visual Smoke — Guided

**Task ID:** `KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDED_01`  
**Masterplan:** Prompt 12/34  
**Product status (before):** `TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBLE_PREVIEW_ONLY`  
**Product status (after this docs task):** `TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_GUIDE_READY`  
**Date:** 2026-07-22

Geführter GUI-Visual-Smoke für Track-B mit **kopierten** Real-PDFs im kontrollierten Testordner.  
Dieser Task startet **keinen** Produktivlauf und schreibt **keine** finalen Invoice-PDFs.  
Explizit: **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Prüfen, ob das technisch erfolgreiche Prompt-11-Ergebnis (Real-PDF Dry-Run, Preview-Only) in der UI-v2 **sichtbar und verständlich** ist:

1. App/UI-v2 sicher starten
2. Kontrollierte Input-/Output-Ordner wählen
3. Sandbox-Lauf starten
4. Running-/Completed-/Review-State sehen
5. Counts, Safety-Proof, Export-Vorschau prüfen
6. Leeren Output nur mit sichtbarem Result-State als Preview-Only werten

Keine produktive Verarbeitung. Keine Originalordner. Keine finalen Writes/Moves/Archives/Renames.

---

## Current known technical result from Prompt 11

Baseline (technisch, Bridge/Contract — nicht GUI-bewiesen):

| Feld | Wert |
|---|---|
| Classification | `PASS_PREVIEW_ONLY` |
| Product status | `TRACK_B_REAL_PDF_SANDBOX_RESULT_VISIBLE_PREVIEW_ONLY` |
| Controlled input | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` |
| Controlled output | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` |
| PDF count | 5 |
| Review | 5 |
| Recognized | 0 (OCR/AI absichtlich nicht ausgeführt) |
| Planned | 5 (data-only) |
| Export preview | ja (data-only) |
| Output | leer (`OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY`) |
| Input hashes | unverändert |
| `run_once` | 0 |
| Produktiv-/Originalpfade | blockiert |
| Scope-Audit | `POST_REAL_PDF_SANDBOX_REPAIR_SCOPE_SYNC_AUDIT_WARN_ALLOWED_BUT_UNLISTED_UIV2_CONTRACT_CHANGE` — Prompt 12 mit dokumentierter Vorsicht erlaubt |

Was Prompt 11 **nicht** bewiesen hat: visuelle GUI-Verständlichkeit für Hadi.

---

## Controlled folders

| Rolle | Pfad |
|---|---|
| Input (kopierte Test-PDFs) | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` |
| Output (separat) | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` |
| Sandbox-Root | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test` |

Regeln:

- Input und Output müssen **getrennt** sein
- Nur dieser kontrollierte kopierte Testordner
- **Keine** realen Rechnungsordner / Originalordner / Produktivordner
- Erwartung vor Lauf: ca. **5 PDFs** im Input, Output leer oder preview-only

Nicht verwenden:

- `/Users/hadi_neu/Desktop/RECHNUNGEN/**`
- `/Users/hadi_neu/Desktop/02_Rechnungseingang/**`
- sonstige produktive/originale Rechnungsordner

---

## Diagnosis (before guided run)

1. **Prompt 11 technisch:** kontrollierte Sandbox-Testpfade erlaubt; Real-PDF Dry-Run mit 5 Review / 0 Recognized / 5 Planned; Export-Vorschau data-only; Output leer erwartet; Input unverändert.
2. **Noch GUI-zu prüfen:** Start, Ordnerwahl akzeptiert, CTA „Sandbox-Lauf starten“, Running-/Completed-State, Counts, Safety-Proof, Export-Vorschau, Review-Seite.
3. **Verfügbare Startmethoden (Repo-Evidenz):**
   - Primär belegt: `app_ui_v2.py` (ruft `invoice_tool.ui_v2.app.build_ui_v2` auf)
   - Optional Flet-0.85: `.venv-flet085/bin/python app_ui_v2.py` bzw. `scripts/run_ui_v2_flet085.sh`
4. **UI-v2-Entrypoint:** vorhanden als `app_ui_v2.py` + Modul `invoice_tool/ui_v2/app.py` (`build_ui_v2`).  
   **Nicht** als `-m`-Runnable: `invoice_tool.ui_v2.app` hat weder `__main__` noch `main`.
5. **Cursor/Terminal-Start:** ja, über Terminal-Befehl unten — GUI-Fenster selbst muss Hadi beobachten.
6. **Menschliche Beobachtung:** erforderlich (Visual Smoke).
7. **Falls Cursor die GUI nicht sehen kann:** Hadi liefert Return-Format + optional Screenshots (Workspace, Review, Export-Vorschau, Safety-Proof, Folder-Monitor).
8. **Leerer Output:** akzeptabel **nur** wenn UI nützlichen Result-State + Export-Vorschau zeigt; sonst Blocker.

---

## A. Parallel folder monitor

In einem **zweiten** Terminal (während des GUI-Smokes):

```bash
BASE="$HOME/Desktop/KI-Rechnungen-Test"
IN="$BASE/input"
OUT="$BASE/output"
while true; do
  clear
  echo "=== KI-Rechnungen-Test Sichtkontrolle ==="
  date
  echo ""
  echo "INPUT:"
  find "$IN" -maxdepth 1 -type f -print | sed 's|.*/||' | sort
  echo ""
  echo "INPUT COUNT:"
  find "$IN" -maxdepth 1 -type f | wc -l
  echo ""
  echo "OUTPUT:"
  find "$OUT" -maxdepth 2 -type f -print | sed "s|$OUT/||" | sort
  echo ""
  echo "OUTPUT COUNT:"
  find "$OUT" -type f | wc -l
  echo ""
  echo "Im Dry-Run darf OUTPUT leer bleiben, wenn die UI Result-State und Export-Vorschau zeigt."
  sleep 2
done
```

---

## B. Safe app start commands

Arbeitsverzeichnis:

```bash
cd "$HOME/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
```

### B.1 Repo-Evidenz zum Einstieg

| Kandidat | Repo-Status |
|---|---|
| `invoice_tool/ui_v2/app.py` | vorhanden (`build_ui_v2`) |
| `python -m invoice_tool.ui_v2.app` | **kein** unterstützter Runnable-Entrypoint (kein `__main__` / kein `main`) — nicht erfinden |
| `app_ui_v2.py` | **belegter** UI-v2-Start (ruft `build_ui_v2` auf) |
| `app_main.py` / Track A | **nicht** für diesen Smoke verwenden |

### B.2 Empfohlener sicherer Start (Track-B UI-v2)

```bash
cd "$HOME/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
.venv/bin/python app_ui_v2.py
```

Falls lokal das Flet-0.85-Venv üblich ist:

```bash
cd "$HOME/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
.venv-flet085/bin/python app_ui_v2.py
```

Optional (Repo-Skript, gleiche Entry `app_ui_v2.py`):

```bash
cd "$HOME/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
./scripts/run_ui_v2_flet085.sh
```

### B.3 Nicht verwenden

- `app_main.py` / Internal Launcher mit Produktivabsicht
- `python -m invoice_tool.run` / `run_once` auf realen Ordnern
- `flet build` / `scripts/build_macos_app.sh`
- Original-/Produktivordner als Input/Output

Notiere die verwendete Startmethode im Return-Format.

---

## C. UI selections

| Feld | Wert |
|---|---|
| Input | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` |
| Output | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` |

Expected:

- 5 PDFs input
- Result state visible
- Review count around 5
- Planned count around 5
- Recognized count around 0 (OCR/AI nicht ausgeführt — ehrliche Abweichung erlaubt, wenn erklärt)
- Export preview visible
- Safety proof visible
- Output empty is acceptable only with visible result state

---

## Guided UI steps

Copy-paste Checkliste — der Reihe nach:

1. **Folder-Monitor** in Terminal 2 starten (Abschnitt A).
2. **Counts before** notieren (Input-PDFs, Output-Dateien).
3. **UI-v2 starten** mit belegtem Befehl aus B.2 — **nicht** Track A.
4. **Workspace** öffnen.
5. **Eingangsordner wählen** → `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`.
6. **Ausgabeordner wählen** → `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`.
7. Prüfen: Input ≠ Output; Pfade werden akzeptiert (kein Original-/Produktiv-Blocker für diesen Testordner nach Prompt 11).
8. Profil/Konfiguration aktiv prüfen.
9. **„Sandbox-Lauf starten“** klicken.
10. **Running-State** beobachten (z. B. „Prüfung läuft …“ / „Läuft“ / „Sandbox-Lauf gestartet.“).
11. **Completed/Review-State** beobachten (z. B. „Abgeschlossen“ / „Sandbox-Lauf mit Prüffällen abgeschlossen.“).
12. **Counts** ablesen: Erkannt / Prüfung / Fehler / Geplant.
13. **Sicherheitsnachweis** sichtbar prüfen (Sandbox/Test bestätigt, Originale ausgeschlossen, Produktiv gesperrt, Dry-Run/no mutation).
14. **Export-Vorschau** im Workspace prüfen.
15. **Review-Seite** öffnen und Prüffälle sichtbar prüfen.
16. **Mutation-Check** mit Monitor: Input unverändert; Output leer oder ohne finale umbenannte Invoice-PDFs.
17. Return-Format ausfüllen (Abschnitt D).

---

## Expected Workspace observations

- Ordnerauswahl zeigt die kontrollierten Pfade
- CTA „Sandbox-Lauf starten“ verfügbar
- Laufstatus wechselt von Bereit → laufend → abgeschlossen / mit Prüffällen
- Compact-Counts etwa: `Erkannt: 0 · Prüfung: 5 · Fehler: 0 · Geplant: 5`  
  (ehrliche Abweichung dokumentieren, falls UI anders zeigt)
- Safety-Proof-Zeilen / Sicherheitsnachweis sichtbar
- Export-Vorschau-Sektion sichtbar (keine finalen Writes behaupten)
- Kein Produktivmodus, keine Originalordner-Freigabe

---

## Expected Review observations

- Review-/Prüfseite erreichbar
- Etwa **5** Prüffälle sichtbar (oder ehrliche Abweichung + Grund)
- Keine Fake-Erkennungen als Produkterfolg
- Hinweise wie OCR/AI nicht ausgeführt sind erlaubt und erwartet

---

## Expected Export preview observations

- Abschnitt „Export-Vorschau“ sichtbar
- Preview aus echtem Run-State (nicht erfunden)
- Keine Behauptung final geschriebener Invoice-PDFs
- Geplante Ziele als Vorschau/data-only

---

## Expected empty-output interpretation

| Situation | Bewertung |
|---|---|
| Output leer **und** UI zeigt Result-State + Counts + Export-Vorschau + Safety-Proof | `OUTPUT_EMPTY_EXPECTED_PREVIEW_ONLY` — **kein** Fail |
| Output leer **und** UI zeigt keinen nützlichen Result-State | Blocker / Fail für Visual Smoke |
| Output enthält finale umbenannte Invoice-PDFs | **UNSAFE** — sofort stoppen |

Leerer Output ist im Dry-Run **erlaubt**, weil der Flow data-only Preview ist und keine finalen PDFs schreibt.

---

## Mutation check

Nach dem Lauf:

1. Input-Dateizahl und Dateinamen unverändert (Monitor / `find`).
2. Output ohne finale umbenannte Invoice-PDFs.
3. Kein Touch auf `/RECHNUNGEN/`, `/02_Rechnungseingang/` oder andere Originale.
4. Keine produktive Verarbeitung, kein `run_once`-Produktivpfad.

---

## Evidence checklist

- [ ] Date/time
- [ ] App start command
- [ ] Input path / Output path
- [ ] Input PDF count before/after
- [ ] Output file count before/after
- [ ] Workspace status
- [ ] Recognized / Review / Error / Planned counts
- [ ] Safety proof visible
- [ ] Export preview visible
- [ ] Review page visible
- [ ] Final files written? (erwartet: no)
- [ ] Input files changed? (erwartet: no)
- [ ] Productive/original folder touched? (erwartet: no)
- [ ] Screenshots optional
- [ ] Observed problems
- [ ] Classification

---

## Pass / pass-with-notes / blocked / unsafe

| Classification | Wann |
|---|---|
| `GUI_VISUAL_SMOKE_PASS` | Start ok, Pfade akzeptiert, Running+Completed, Counts ≈ 5/0/5, Safety+Export+Review sichtbar, Output leer ok, keine Mutation |
| `GUI_VISUAL_SMOKE_PASS_WITH_NOTES` | Wesentlich sichtbar, aber kleine ehrliche Abweichungen/Hinweise |
| `GUI_VISUAL_SMOKE_BLOCKED` | Start/Ordnerwahl/CTA/Result-State nicht nutzbar, ohne unsichere Mutation |
| `GUI_VISUAL_SMOKE_FAIL_UNSAFE` | Originale/Produktiv berührt, finale Writes, Input mutiert, oder unsichere Aktion |

---

## Stop conditions

**Sofort stoppen**, wenn:

- falsches Worktree / Track-A-UI gestartet wird
- Original-/Produktivordner gewählt werden sollen
- Input == Output
- produktive Verarbeitung startet oder freigeschaltet wirkt
- finale Write/Move/Archive/Rename-Aktionen sichtbar werden
- Input-Dateien sich ändern
- reale Rechnungsordner berührt werden
- Fake-Success ohne Counts/Result-State
- Unsicherheit bei Ordnerwahl

Keine produktive Verarbeitung. Keine realen Rechnungsordner.

---

## D. Return format for Hadi

```text
GUI VISUAL SMOKE RESULT

Date/time:
App start command:
Input path:
Output path:
Input PDF count before:
Input PDF count after:
Output file count before:
Output file count after:
Workspace status:
Recognized count:
Review count:
Error count:
Planned count:
Safety proof visible: yes/no
Export preview visible: yes/no
Review page visible: yes/no
Final files written: yes/no
Input files changed: yes/no
Any productive/original folder touched: yes/no
Screenshots captured: yes/no
Observed problems:
Classification:
GUI_VISUAL_SMOKE_PASS / GUI_VISUAL_SMOKE_PASS_WITH_NOTES / GUI_VISUAL_SMOKE_BLOCKED / GUI_VISUAL_SMOKE_FAIL_UNSAFE
```

Nächster Evidence-Intake-Task:  
`KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_01`

---

## Not SaaS-ready / not production-ready

Dieser Guided Visual Smoke beweist **keine** SaaS-Reife und **keine** Production-Reife.  
Er bereitet nur die visuelle Prüfung des kontrollierten Preview-Only-Dry-Runs vor.
