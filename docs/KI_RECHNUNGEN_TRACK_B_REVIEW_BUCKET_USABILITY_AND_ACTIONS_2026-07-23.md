# Track-B Review-Bucket Usability and Actions

**Task ID:** `KI_RECHNUNGEN_TRACK_B_REVIEW_BUCKET_USABILITY_AND_ACTIONS_01`  
**Masterplan:** Prompt 15/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_REVIEW_BUCKET_USABILITY_AND_ACTIONS_READY`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Nach dem erfolgreichen Prompt-14 Real-PDF GUI Visual Smoke prüfen und verbessern, ob Nutzer mit den fünf Prüffällen im Review-Bucket („Zur Prüfung“) arbeiten können — sichtbar, verständlich, mit sicheren Preview-only-Aktionen und ohne finale Dateischreibung.

---

## Baseline from Prompt 14

- Classification: `GUI_VISUAL_SMOKE_PASS`
- Product status: `TRACK_B_REAL_PDF_GUI_VISUAL_SMOKE_PASS_RECORDED`
- UI: „Abgeschlossen“, „Sandbox-Lauf mit Prüffällen abgeschlossen.“
- Counts: Erkannt 0 · Prüfung 5 · Fehler 0 · Geplant 5
- Safety: Originale unverändert · Produktiv gesperrt · Export Vorschau
- Controlled input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input` (5 PDFs)
- Controlled output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output` (0 Dateien, expected preview-only)
- App start: `.venv-flet085/bin/python app_ui_v2.py`

Noch nicht bewiesen war: Review-Bucket-Usability (Liste, Details, sichere Preview-Aktionen).

---

## Current Review bucket behavior

Vor diesem Task:

- Review-Seite konnte injizierte `ProcessingRunState.review_items` listen.
- Felder: Dokumentname, Grund, Status, nächster Schritt.
- Legacy-Prüfaktionen waren sichtbar, aber **disabled** („noch nicht verbunden“).
- Keine Item-Auswahl / Detail-Panel-Usability.
- Keine lokalen Preview-only-Aktionen.

Nach diesem Task (UI-v2-only):

- Sichtbare Prüffall-Liste mit Dateiname, Kategorie „Zur Prüfung“, Prüfgrund, geplantem Ziel/Aktion, Preview-/No-Write-Markern.
- Auswahl öffnet Prüffall-Details.
- Preview-Aktionen ändern nur in-memory UI-v2-State.
- Legacy-Aktionen bleiben disabled; produktive Final-Aktionen bleiben blockiert.

---

## Implemented / verified usability

| Anforderung | Status |
|---|---|
| Liste/Tabelle der Prüffälle | implementiert + getestet |
| Quelldateiname | sichtbar |
| Prüfgrund | sichtbar |
| Geplantes Ziel / Aktion | sichtbar, wenn im Lauf vorhanden |
| Preview-only / keine finalen Dateien | Badge + Banner |
| Item auswählen / öffnen | implementiert |
| Detailansicht | implementiert |
| Sichere Preview-Aktionen | implementiert (lokal) |
| Kein `run_once` / keine Writes | garantiert + getestet |

---

## Review list fields

Pro Listeneintrag:

- Quelldateiname (`source_filename`)
- Kategorie: **Zur Prüfung**
- **Grund der Prüfung**
- Geplantes Ziel / Aktion (falls vorhanden)
- Konfidenz/Status
- Badges: **Vorschau**, **Keine finalen Dateien geschrieben**, **Produktiv gesperrt**
- Preview-Status (in Prüfung / als geprüft Preview / aus Export-Vorschau ausgeschlossen)

---

## Review detail fields

Bei Auswahl:

- Quelldatei
- Grund der Prüfung
- Geplantes Ziel / Aktion
- Sicherheitsstatus
- Export-Vorschau-Status
- Produktiv gesperrt
- Originale unverändert
- Preview-only-Banner
- Empty-Output-Erklärung

---

## Safe preview-only actions

| Aktion | Wirkung |
|---|---|
| Als geprüft markieren (Preview) | lokaler Checked-State |
| In Prüfung belassen | Checked/Exclude zurücknehmen; bleibt im Bucket |
| Aus Export-Vorschau ausschließen | lokaler Export-Preview-Include-State |
| Auswahl zurücksetzen | Selection/Checked/Exclude zurücksetzen |

Diese Aktionen:

- rufen **nicht** `run_once` auf
- verarbeiten **keine** PDFs
- schreiben **keine** finalen Dateien
- mutieren **keinen** Input
- berühren **keine** realen Rechnungsordner
- ändern **nicht** Track A / Processing-Core

---

## Safety guarantees

- `actions_disabled=True` für Legacy-/Final-Aktionen
- `productive_actions_exposed=False`
- `final_actions_blocked=True`
- `mutates_files=False`
- Banner: „Preview only — Keine finalen Dateien geschrieben — Produktiv gesperrt“
- Keine Hardcodes privater Hadi/SOMAA-Routing-Defaults

---

## Empty output interpretation

Der Review-UI erklärt klar:

> Output bleibt in Vorschau/Dry-Run leer, bis ein späterer explizit freigegebener Export-/Finalisierungsschritt folgt. Keine finalen Dateien geschrieben.

Leerer Output ist **kein** Fehlerhinweis für fehlgeschriebene PDFs, sondern erwartetes Preview-Only-Verhalten.

---

## What is now proven

- Review-Bucket zeigt 5 Prüffälle als nutzbare Liste.
- Dateiname, Prüfgrund, geplantes Ziel, Safety/Preview-Marker sind sichtbar.
- Detailansicht für ausgewählten Prüffall existiert.
- Preview-Aktionen ändern nur UI-v2-State.
- Keine produktive Verarbeitung, keine finalen Dateien, keine realen Rechnungsordner.
- Track-A-Schutztests bleiben grün.

---

## What is still not proven

- Finaler Approval-to-Write / produktiver Export
- Download-/Export-User-Flow (nächster Prompt)
- Vollständige OCR/AI-Erkennung
- Track-A-Parität / Produktivordnerflows
- SaaS-/Production-Reife

---

## No productive processing

Ja — Preview-only; kein Produktivlauf.

## No real invoice folders

Ja — nur kontrollierter Sandbox-/Testkontext bzw. injizierter Run-State in Tests.

## Not SaaS-ready

Explizit **nicht SaaS-ready**.

## Not production-ready

Explizit **nicht production-ready**.

---

## Next step

`KI_RECHNUNGEN_TRACK_B_EXPORT_PREVIEW_USER_FLOW_AND_DOWNLOAD_01`
