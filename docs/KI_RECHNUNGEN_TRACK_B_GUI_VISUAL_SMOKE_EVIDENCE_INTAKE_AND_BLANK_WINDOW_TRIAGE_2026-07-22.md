# Track-B GUI Visual Smoke — Evidence Intake & Blank-Window Triage

**Task ID:** `KI_RECHNUNGEN_TRACK_B_GUI_VISUAL_SMOKE_EVIDENCE_INTAKE_AND_BLANK_WINDOW_TRIAGE_01`  
**Masterplan:** Prompt 13/34  
**Date:** 2026-07-22  
**Classification (user evidence):** `GUI_VISUAL_SMOKE_BLOCKED`  
**Product status (after this task):** `TRACK_B_GUI_VISUAL_SMOKE_BLANK_WINDOW_REPAIRED_READY_FOR_RERUN`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## User observed evidence

| Feld | Beobachtung |
|---|---|
| Startbefehl | `.venv/bin/python app_ui_v2.py` |
| Fenster | öffnet, aber leer / weiß / leicht bläulich |
| Track-B Workspace | nicht sichtbar |
| Input/Output-Auswahl | nicht sichtbar |
| „Sandbox-Lauf starten“ | nicht sichtbar |
| Counts / Export-Vorschau / Safety-Proof | nicht sichtbar |
| Terminal | keine Python-Exception / kein Traceback sichtbar |
| Sandbox-Lauf | nicht gestartet |
| Produktivlauf | nicht gestartet |
| Reale Rechnungsordner | nicht verwendet |
| Input (Monitor) | 5 PDFs im kontrollierten Ordner |
| Output (Monitor) | 0 Dateien |

Manuelle Klassifikation vor Triage: **`GUI_VISUAL_SMOKE_BLOCKED`** — UI-v2-Fenster startet, rendert aber keinen Workspace.

---

## Diagnosis

1. **`app_ui_v2.py`** ruft den UI-v2-Start auf und übergibt `main` an `flet.app` / `flet.run`.
2. Root-Builder ist **`invoice_tool.ui_v2.app.build_ui_v2`**: setzt Page-Titel/Größe/`bgcolor`, baut Shell + Workspace (`NAV_WORKSPACE`), ruft `page.add(shell.root)` und `page.update()`.
3. Mit **richtiger** Umgebung (`.venv-flet085`, Flet **0.85.3**) erzeugt `build_ui_v2` den sichtbaren Shell-Root (`ui-v2-shell`).
4. Mit **`.venv`** (Flet **0.28.3**, Python 3.9) scheitert der Workspace-Build an:
   - `AttributeError: type object 'Padding' has no attribute 'symmetric'`
   - Aufrufkette: `build_ui_v2` → `build_workspace_page` → `secondary_button` → `_outline_button_style` → `ft.Padding.symmetric(...)`
5. Die Exception trat **vor** `page.add(shell.root)` auf → Fenster blieb bei Page-Hintergrund (`COLOR_PAGE_BG` / Canvas `#f3f2ef`, hell / leicht kühl) **ohne Controls**.
6. Flet Desktop zeigte das leere Fenster; ein klarer Traceback war für den Nutzer im Terminal nicht sichtbar (geschluckt / nicht auffällig).
7. Prompt-12-Guide nannte `.venv/bin/python app_ui_v2.py` als Primärstart — das ist für UI-v2 **falsch**; korrekt ist Flet 0.85.

---

## Root cause

**Environment / Flet-Version mismatch (klar und begrenzt):**

- Beobachteter Start: `.venv` → Flet **0.28.3**
- UI-v2-API-Bedarf: Flet **≥ 0.85** (`.venv-flet085`, belegt 0.85.3)
- Folge: Startup-Exception → **leeres Fenster**, kein Workspace

Nicht die Ursache: fehlende Page-Registration an sich, fehlendes Root-Component in 0.85, produktive Verarbeitung, Track-A-Pfad.

---

## Repair implemented

Begrenzt auf UI-v2 Startup/Root:

| Datei | Änderung |
|---|---|
| `invoice_tool/ui_v2/startup_diagnostics.py` | **neu** — Flet-Version-Guard, sichtbare Diagnostik-Panel, `start_ui_v2()` |
| `app_ui_v2.py` | nutzt `start_ui_v2()` statt ungeschütztem `build_ui_v2()` |

Verhalten:

- Flet **&lt; 0.85**: sichtbare Diagnostik mit Hinweis auf `.venv-flet085/bin/python app_ui_v2.py` + Log auf stderr (kein leeres Fenster).
- Flet **≥ 0.85**: normaler Workspace via `build_ui_v2`.
- Andere Startup-Exceptions: sichtbare Diagnostik + Traceback auf stderr.

Keine PDF-Verarbeitung, kein `run_once`, keine Track-A-/Core-Änderungen, keine Input-/Output-Ordner-Mutation.

---

## What Hadi should rerun

**Korrekter Start (Flet 0.85):**

```bash
cd "$HOME/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
.venv-flet085/bin/python app_ui_v2.py
```

Alternativ:

```bash
./scripts/run_ui_v2_flet085.sh
```

**Nicht** als Primärstart für UI-v2:

```bash
.venv/bin/python app_ui_v2.py
```

(zeigt jetzt eine Diagnostik statt leerem Fenster — Workspace kommt erst mit Flet 0.85.)

Kontrollordner unverändert:

- Input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`
- Output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`

Folder-Monitor parallel wie in Prompt 12.

---

## Expected rerun observations

Mit `.venv-flet085/bin/python app_ui_v2.py`:

1. Fenster öffnet mit **sichtbarem** Track-B Shell/Workspace (Sidebar „NAME.IT PRO“, Nav „Arbeitsbereich“, …).
2. Ordnerwahl Input/Output sichtbar.
3. CTA „Sandbox-Lauf starten“ erreichbar (noch nicht zwingend ausgeführt in diesem Task).
4. Kein leeres weiß/bläuliches Fenster.
5. Keine produktive Verarbeitung durch bloßes Starten.
6. Output darf leer bleiben, bis ein Sandbox-Lauf bewusst gestartet wird; nach Lauf gelten Prompt-11/12-Erwartungen (Preview-Only).

Mit `.venv/bin/python app_ui_v2.py` (Regressionsschutz):

- Kein Blank-Window mehr; Diagnostik-Text zur Flet-Version sichtbar; stderr-Hinweis.

---

## Safety / maturity

- Keine produktive Verarbeitung in diesem Task
- Keine realen Rechnungsordner berührt
- Keine Release-Tags geändert
- **Nicht** SaaS-ready
- **Nicht** production-ready

---

## Next task

`KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_RERUN_01`
