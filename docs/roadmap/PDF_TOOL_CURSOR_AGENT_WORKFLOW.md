# PDF Tool – Cursor Agent Workflow

Dieses Dokument definiert den autonomen Agentenworkflow für das Projekt
**KI-Rechnungen-App** (`/Users/hadi_neu/Desktop/KI-Rechnungen-App`).

Es ist verbindliche Arbeitsgrundlage für alle Cursor-Aufträge in diesem Repo
und ergänzt die übrigen Projektregeln.

---

## 1. Zweck

Cursor soll Standardarbeiten selbstständiger ausführen können, ohne dass der
Nutzer nach jedem Mini-Schritt einen neuen Prompt schreiben oder ChatGPT
befragen muss. Ziel ist ein schnellerer Entwicklungsfluss bei gleichbleibender
oder höherer Qualität.

Leitsätze:
- **Weniger manuelles Hin-und-her** zwischen Cursor und ChatGPT.
- **Qualität, Originalschutz und Nachvollziehbarkeit** dürfen nicht reduziert werden.
- **ChatGPT** ist nur bei echten Architektur-, Risiko- oder Fehlentscheidungen nötig.
- **Entscheidungssignale** (WEITER IN CURSOR, NUTZERFREIGABE, CHATGPT FRAGEN, STOPP)
  bleiben die einzige autorisierte Kommunikationsform für Richtungsentscheidungen.

---

## 2. Arbeitsgrundlagen

Cursor arbeitet nach folgenden Dokumenten, in dieser Reihenfolge:

1. `.cursor/rules/ki-rechnungen-workflow.mdc` – Cursor-native Regeldatei (immer aktiv)
2. `docs/CURSOR_WORKFLOW_RULES.md` – vollständige Projektregeln
3. `docs/roadmap/PDF_TOOL_CURSOR_AGENT_WORKFLOW.md` – **diese Datei** (autonomer Workflow)
4. `docs/MASTERPLAN_PDF_DOCUMENT_TOOL.md` – strategische Roadmap

Bei Widersprüchen gilt: `.cursor/rules/ki-rechnungen-workflow.mdc` vor allen anderen.

---

## 3. Autonomer Fortsetzungsmodus

Cursor darf **bis zu 3 kleine, eindeutig sichere Schritte** nacheinander
ausführen, wenn der Nutzer `Weiter nach Projektregeln.` schreibt oder ein
Auftrag den autonomen Modus explizit aktiviert.

### Interne Prüfung nach jedem Teilschritt

Vor dem nächsten automatischen Schritt muss Cursor intern prüfen:

| # | Prüfung | Anforderung |
|---|---------|-------------|
| 1 | Scope eingehalten? | Kein Schritt außerhalb des freigegebenen Bereichs |
| 2 | Tests/Checks ausgeführt? | Passende Tests liefen und sind grün |
| 3 | Git diff plausibel? | Nur erwartete Dateien geändert |
| 4 | Working Tree sauber oder erwartbar? | Kein unerwarteter Dirty-State |
| 5 | Entscheidungssignal wäre WEITER IN CURSOR? | Alle obigen Punkte erfüllt |

**Wenn ja → automatisch mit dem nächsten kleinen Schritt fortfahren.**

**Wenn nein → sofort stoppen und Abschlussbericht ausgeben.**

Erst am Ende des gesamten Laufs (nach allen Teilschritten oder nach einem
Stop) gibt Cursor einen zusammenfassenden Abschlussbericht aus (→ Abschnitt 9).

---

## 4. Zulässige kleine Schritte

Folgende Schritte gelten als „kleine, eindeutig sichere Schritte" und können
im autonomen Modus ohne zusätzliche Freigabe ausgeführt werden:

- Dokumentations- oder Regeldateien ergänzen oder aktualisieren
- Tests ergänzen oder stabilisieren (keine Tests löschen)
- Kleine Prüf- oder Hilfsskripte verbessern (`scripts/`)
- Smoke-Test- oder Run-Checker verbessern
- Nicht-riskante CLI-Hilfen ergänzen
- Bestehende Preview- oder Report-Funktionen verbessern
- Kleine Profil- oder Runtime-Regel-Checks ergänzen
- Profile-Compiler-Methoden hinzufügen (bestehende Compilers als Vorbild)
- Masterplan-Status aktualisieren, wenn eine Implementierung abgeschlossen ist
- **Commit erstellen**, wenn ausdrücklich erlaubt oder vom Workflow freigegeben
- **Push** nur, wenn ausdrücklich erlaubt oder mit NUTZERFREIGABE empfohlen

---

## 5. Nicht zulässige autonome Schritte

Folgende Schritte erfordern immer eine **explizite Freigabe** (NUTZERFREIGABE
oder direkter Nutzerbefehl), bevor Cursor sie ausführt:

- Produktivlauf auf echten Zielordner
- Echte Original-PDFs verschieben, löschen oder umbenennen
- `office_rules.json` dauerhaft durch Profil- oder UI-Einstellungen überschreiben
- `invoice_config.json` ändern
- Neue Python-Dependencies hinzufügen
- Große Architekturänderungen
- UI-Strategieänderung
- Processing-Core-Umbau
- OCR-, OpenAI- oder Extraktionslogik wesentlich ändern
- Bulk-Operationen auf echten Dateien
- Neue Persistenz- oder Datenbanklogik einführen
- Automatische Löschung von Output- oder Archivordnern
- Push ohne ausdrückliche Freigabe

---

## 6. Stop-Kriterien

Cursor muss **sofort stoppen** und den Abschlussbericht ausgeben, wenn eines
der folgenden Kriterien eintritt:

- `CHATGPT ENTSCHEIDUNG NÖTIG` (Architektur, Regression, mehrere gleichwertige Wege)
- `STOPP – FREIGABE FEHLT` (Produktivlauf, Dateiänderung, Push ohne Erlaubnis)
- Working Tree unclean außerhalb des erwarteten Scopes
- Tests oder Smoke-Test schlagen fehl
- Regression gegenüber Baseline (→ Abschnitt 10)
- Source- oder Originalschutz nicht eindeutig gewährleistet
- Pfade unsicher oder außerhalb freigegebener Output-Orte
- Vollständige IBANs, Kartennummern, API-Keys oder Zugangsdaten erkannt
- Neue Dependency nötig
- Mehrere nächste Schritte mit unterschiedlichen Architekturfolgen
- Scope würde sich auf UI, Produktivlauf, Runtime-Vertrag oder Processing-Core erweitern
- Lauf wäre unsandboxed oder außerhalb freigegebener Output-Orte
- Cursor kann das Ergebnis nicht sicher prüfen

---

## 7. Entscheidungssignale

Am Ende jedes gesamten Laufs gibt Cursor genau ein Signal aus.
Die Signalformate sind in `.cursor/rules/ki-rechnungen-workflow.mdc` definiert.

Kurzübersicht:

| Signal | Wann |
|--------|------|
| `WEITER IN CURSOR` | Tests grün · Working Tree clean · keine Regression · keine Produktivdaten · keine offene Architekturentscheidung |
| `CHATGPT FRAGEN` | Architekturentscheidung · unerklärliche Regression · mehrere gleichwertige Wege · Scope-Erweiterung |
| `NUTZERFREIGABE` | Push · Produktivlauf · echte Dateien · Output außerhalb `/tmp` |
| `STOPP` | Working Tree unklar · sensible Vollwerte · Originalschutz unsicher · fehlende Datei · Test außerhalb Scope kaputt |

Jedes Signal enthält immer:

```
ENTSCHEIDUNGSSIGNAL: <Signal>
EMPFOHLENER MODUS: <Agent / Ask / Plan / ChatGPT>
CHATGPT NÖTIG: <ja / nein>
EMPFEHLUNG: <weiterarbeiten / freigeben / nicht freigeben / erst ChatGPT fragen>
BEGRÜNDUNG: <kurz und konkret>
NÄCHSTER BEFEHL oder FREIGABEFRAGE: <konkret formulieren>
ZAUBERWORT: Weiter nach Projektregeln.
```

---

## 8. Zauberwort

Wenn Cursor meldet:

```
ENTSCHEIDUNGSSIGNAL: WEITER IN CURSOR
```

darf der Nutzer schreiben:

> **Weiter nach Projektregeln.**

Cursor wählt dann selbst den nächsten sicheren kleinen Schritt, führt ihn aus,
prüft intern (→ Abschnitt 3), setzt ggf. bis zu **3 Teilschritte** insgesamt
fort und gibt am Ende einen zusammenfassenden Abschlussbericht aus.

Das Zauberwort darf **niemals** automatisch auslösen:

- Push
- Produktivlauf
- Echte Dateiänderungen (Original-PDFs, Zielordner)
- Löschung, Verschiebung oder Umbenennung echter Dateien
- Neue Dependencies
- Große Architekturänderungen
- Scope-Erweiterungen

Dafür ist immer NUTZERFREIGABE oder CHATGPT FRAGEN erforderlich.

---

## 9. Standardbericht am Ende eines autonomen Laufs

Am Ende jedes Laufs (nach allen Teilschritten oder nach einem Stop) gibt Cursor
einen zusammenfassenden Abschlussbericht aus:

1. **Ausgeführte Teilschritte** – was wurde in welcher Reihenfolge gemacht?
2. **Geänderte Dateien** – vollständige Liste
3. **Tests/Checks** – pytest-Ergebnis oder Begründung warum nicht nötig
4. **Commits** – Hash und Message, oder „kein Commit"
5. **Push** – ja/nein
6. **Working Tree** – CLEAN / DIRTY + Details
7. **Risiken oder Abweichungen** – falls vorhanden
8. **Entscheidungssignal** – (→ Abschnitt 7)
9. **Empfehlung** – konkret
10. **Nächster Befehl oder Freigabefrage** – konkret formuliert

---

## 10. Standard-Baselines

Die bekannte Baseline für Profil- und Smoke-Tests auf dem lokalen Testarchiv:

| Kennzahl | Wert |
|----------|------|
| processed | 25 |
| document | 1 |
| duplicate | 3 |
| unclear | 1 |
| errors | 0 |

Prüfbefehl:
```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_profile_run.py \
  --run-dir "<RUN_DIR>" \
  --baseline "25,1,3,1,0"
```

Oder automatisiert über den Dev-Assistenten:
```bash
PYTHONPATH=. ./.venv/bin/python scripts/dev_assistant.py --mode next
```

**Abweichungen müssen erklärt werden.**
**Verschlechterungen gelten als Regressionen**, bis das Gegenteil belegt ist.

Hinweis `system_fallbacks`: Wenn OpenAI im Sandbox-/Rate-Limit-Kontext nicht
erreichbar ist, nutzt das System Tesseract als Fallback. Die Routing-Baseline
bleibt dabei korrekt. Für Produktivläufe ist OpenAI-Verfügbarkeit sicherzustellen.

---

## 11. Akustisches Signal

Falls `scripts/dev_assistant.py` existiert (oder ein vergleichbares Hilfsskript
später erstellt wird), soll bei folgenden Signalen ein akustischer Hinweis
ausgegeben werden:

| Signal | Akustik |
|--------|---------|
| NUTZERFREIGABE | `osascript -e 'beep'` (macOS) |
| CHATGPT FRAGEN | `osascript -e 'beep'` (macOS) |
| STOPP | `osascript -e 'beep'` (macOS) |
| WEITER IN CURSOR | kein Signal |

Fehler beim Beep-Aufruf dürfen den Lauf nicht unterbrechen (kein harter Fehler).

---

## 12. Beispielauftrag

Der folgende Text kann direkt als Prompt an Cursor übergeben werden, um den
autonomen Fortsetzungsmodus zu aktivieren:

---

> Arbeite nach `docs/roadmap/PDF_TOOL_CURSOR_AGENT_WORKFLOW.md`.
>
> **Autonomer Fortsetzungsmodus:**
> Führe bis zu 3 kleine, eindeutig sichere Schritte nacheinander aus.
>
> Nach jedem Teilschritt:
> 1. Prüfe Scope, Tests/Checks, git diff und Working Tree.
> 2. Wenn alles innerhalb Scope ist und das Entscheidungssignal WEITER IN CURSOR
>    wäre, starte automatisch den nächsten kleinen Schritt.
> 3. Erstelle erst am Ende des gesamten Laufs einen zusammenfassenden Abschlussbericht.
>
> Stoppe sofort und berichte, wenn eines davon eintritt:
> - CHATGPT ENTSCHEIDUNG NÖTIG
> - STOPP – FREIGABE FEHLT
> - Produktivlauf / echter Zielordner ohne Freigabe
> - Neue Dependency nötig
> - Test/Smoke-Test schlägt fehl
> - Working Tree unclean außerhalb Scope
> - Mehrere nächste Schritte mit unterschiedlichen Architekturfolgen
>
> Am Ende:
> - Alle Teilschritte zusammenfassen
> - Commits nennen
> - Tests/Checks nennen
> - Entscheidungsinfobox ausgeben:
>
> ```
> ENTSCHEIDUNGSSIGNAL: ...
> EMPFOHLENER MODUS: ...
> CHATGPT NÖTIG: ...
> EMPFEHLUNG: ...
> BEGRÜNDUNG: ...
> ZAUBERWORT: Weiter nach Projektregeln.
> ```

---

*Zuletzt aktualisiert: 2026-04-30*
