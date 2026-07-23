# Track-B Real-PDF GUI Visual Smoke — Rerun Evidence

**Task ID:** `KI_RECHNUNGEN_TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_RERUN_01`  
**Masterplan:** Prompt 14/34  
**Date:** 2026-07-23  
**Classification:** `GUI_VISUAL_SMOKE_PASS`  
**Product status (after this task):** `TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_PASS_RECORDED`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Den erfolgreichen Nutzer-Rerun des Track-B Real-PDF GUI Visual Smokes nach Prompt 13 (Blank-Window-Repair) dokumentieren:

1. Blank-Window-Blocker ist aufgelöst (korrekte Flet-0.85-Umgebung).
2. UI zeigt sichtbaren abgeschlossenen Sandbox-Result-State.
3. Counts, Safety-Proof und Export-Vorschau sind sichtbar.
4. Leerer Output ist erwartetes Preview-Only-Verhalten.
5. Keine finalen Invoice-PDFs, keine produktive Verarbeitung, keine Originalordner.

Docs/Tests only — keine Runtime-Code-Änderung in diesem Task.

---

## User rerun evidence

Nach Prompt 13 wurde der GUI-Smoke mit korrigierter Flet-Umgebung neu gestartet.  
Beobachtung: sichtbarer grüner Completed-Status, Counts, Safety-Proof und Export-Vorschau; paralleler Folder-Monitor bestätigte Input 5 / Output 0.

Manuelle Klassifikation durch den Product Owner: **`GUI_VISUAL_SMOKE_PASS`**.

---

## App start command

Korrekter Start (Flet ≥ 0.85):

```bash
cd "$HOME/Desktop/Programm Belegerfassung/KI-Rechnungen-App"
.venv-flet085/bin/python app_ui_v2.py
```

Nicht als Primärstart für UI-v2: `.venv/bin/python app_ui_v2.py` (Flet 0.28 → Blank-Window / Diagnostik).

---

## Controlled input/output paths

| Rolle | Pfad |
|---|---|
| Input (kopierte Test-PDFs) | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` |
| Output (separat) | `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` |

Keine Original-/Produktivordner. Keine Pfade unter `/Users/hadi_neu/Desktop/RECHNUNGEN/**` oder `/Users/hadi_neu/Desktop/02_Rechnungseingang/**`.

---

## Input file list

| # | Datei |
|---|---|
| 1 | `320262919974.pdf` |
| 2 | `420260091336.pdf` |
| 3 | `FA011466.pdf` |
| 4 | `Rechnung RE-202605-14594.pdf` |
| 5 | `Rechnung-2026156019-102201.pdf` |

- **Input count:** 5  
- **Output count:** 0  

---

## GUI observed status

Sichtbarer Completed-State:

- **Abgeschlossen**
- **Sandbox-Lauf mit Prüffällen abgeschlossen.**

Zusätzliche sichtbare Detailzeilen (Auszug):

- „Sandbox-Lauf gestartet.“
- „Core-Dry-Run abgeschlossen ohne Source-Mutation. …“

---

## GUI observed counts

| Kennzahl | Wert |
|---|---|
| Erkannt | 0 |
| Prüfung | 5 |
| Fehler | 0 |
| Geplant | 5 |

UI-Textform: „Erkannt: 0 · Prüfung: 5 · Fehler: 0 · Geplant: 5“.

---

## GUI observed safety proof

Sichtbar in der UI:

- **Originale unverändert**
- **Produktiv gesperrt**
- **Export Vorschau**
- **Keine Originalordner wurden verwendet.**

---

## Export preview visible

Export-Vorschau war im Result-State sichtbar („Export Vorschau“ / Preview-Only).  
Keine finalen umbenannten Invoice-PDFs wurden geschrieben.

---

## Output empty interpretation

**Output count 0** ist **expected preview-only** — **nur** weil sichtbarer Result-State und Export Preview existieren.

Leerer Output allein wäre kein Pass; hier liegen Completed-Status, Counts, Safety-Proof und Export-Vorschau vor. Daher: Preview-Only akzeptabel, keine finalen Writes erwartet.

---

## Classification

**`GUI_VISUAL_SMOKE_PASS`**

---

## Blank window blocker status

**Aufgelöst.** Prompt-13-Ursache (Flet 0.28 vs. ≥ 0.85) ist durch Rerun mit `.venv-flet085/bin/python app_ui_v2.py` bestätigt behoben: Workspace und Completed-Sandbox-UI sind sichtbar.

---

## What is now proven

- UI-v2 startet mit korrekter Flet-Umgebung sichtbar (kein Blank Window).
- Sandbox-Lauf kann bis zum Completed-State geführt werden.
- Counts: Erkannt 0, Prüfung 5, Fehler 0, Geplant 5.
- Safety-Proof sichtbar: Originale unverändert, Produktiv gesperrt, Export Vorschau, keine Originalordner.
- Export-Vorschau sichtbar; Output leer als Preview-Only erwartbar.
- Keine finalen Invoice-Dateien im Output.
- Keine produktive Verarbeitung; keine realen Rechnungsordner.

---

## What is still not proven

- Review-Bucket-Usability / Aktionen (nächster Track-B-Schritt).
- Vollständige OCR/AI-Erkennung (bewusst 0 erkannt).
- Finale Rename-/Write-Pipeline.
- SaaS-Reife, Production-Ready, Release-Tauglichkeit.
- Track-A-Parität / produktive Ordnerflows.

---

## No productive processing

Ja — kein Produktivlauf, kein `run_once` auf Produktivpfaden, keine Source-Mutation laut UI-Safety-Proof.

## No real invoice folders

Ja — nur kontrollierter Ordner `KI-Rechnungen-Test`; **Keine Originalordner wurden verwendet.**

## Not SaaS-ready

Explizit **nicht SaaS-ready**.

## Not production-ready

Explizit **nicht production-ready**.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_REVIEW_BUCKET_USABILITY_AND_ACTIONS_01`
