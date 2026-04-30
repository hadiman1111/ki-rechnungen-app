# Cursor Workflow Rules

## Projekt
- Projektpfad: `/Users/hadi_neu/Desktop/KI-Rechnungen-App`
- Dieses Projekt ist kein reines Rechnungsprogramm mehr, sondern ein allgemeines PDF-Dokumentenwerkzeug mit Rechnungen als erstem stabilem Anwendungsfall.

## Standardablauf
- Zu Beginn jedes Auftrags Git-Zustand prüfen:
  - Branch
  - letzter Commit
  - Branch-Abstand zu origin/main
  - staged / unstaged / untracked
- Am Ende jedes Auftrags Git-Zustand erneut prüfen.
- Wenn der Working Tree nicht clean ist und der Auftrag keinen Umgang damit ausdrücklich erlaubt: stoppen und berichten.

## Git-Regeln
- Kein Push außer ausdrücklich erlaubt.
- Kein Commit außer ausdrücklich erlaubt.
- Nur die für den Auftrag relevanten Dateien stagen.
- Keine generierten Output-, Runtime-, Smoke-Test- oder /tmp-Dateien committen.
- Lokale Profil-Dateien `profile_config.local*.json` und `config/profile_config.local*.json` sind privat/ignoriert und dürfen nicht committed werden.

## Datenschutz / sensible Daten
- Keine vollständigen IBANs ausgeben.
- Keine vollständigen Kartennummern ausgeben.
- Keine Zugangsdaten oder API-Keys ausgeben.
- Gekürzte Endungen wie `****1234` sind erlaubt, wenn sie bereits im Projekt vorhanden sind oder der Nutzer dies ausdrücklich freigegeben hat.
- Bei Berichten sensible Werte nur maskiert darstellen.

## Datei- und Originalschutz
- Original-PDFs niemals direkt verändern.
- Processing Core darf nur auf Snapshots bzw. freigegebenen Arbeitskopien arbeiten.
- Keine produktiven Dateien löschen, verschieben oder umbenennen, außer der Auftrag erlaubt es ausdrücklich.
- Output-Dateien nur in dafür vorgesehene Output- oder /tmp-Ordner schreiben.

## Profil- und Runtime-Regeln
- `office_rules.json` darf nicht dauerhaft durch Profil- oder UI-Einstellungen überschrieben werden.
- Nutzerprofile erzeugen Runtime Rules pro Lauf.
- `profile_config.local*.json` ist lokal/privat und git-ignoriert.
- `routing.payment_detection_rules` nutzt PREPEND:
  - Profilregeln zuerst
  - Basisregeln bleiben erhalten
- Ersetzte/generierte Bereiche müssen in `_meta.generated_sections` nachvollziehbar sein.
- Vorangestellte Bereiche müssen in `_meta.prepended_sections` nachvollziehbar sein.

## Tests und Smoke-Tests
- Bei Produktcodeänderungen vollständige Testsuite ausführen:
  - `./.venv/bin/pytest -q`
- Bei reinen Dokumentations- oder `.gitignore`-Änderungen sind Tests nicht nötig; das muss im Bericht begründet werden.
- Bei Smoke-Tests immer prüfen:
  - Final Status
  - Reports vollständig
  - `runtime_rules.json` gültig
  - `profile_snapshot.json` vorhanden, wenn Profil verwendet wird
  - `_meta.profile_applied`
  - Source unverändert
  - Laufwerte processed/document/duplicate/unclear/errors
- Wenn ein Smoke-Test abgebrochen wurde, darf er nicht als vollständig bestandener Smoke-Test dargestellt werden.

## Run-Verifikation mit check_profile_run.py

Nach jedem `run.py`-Lauf ist die manuelle Einzelprüfung durch diesen Befehl zu ersetzen:

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_profile_run.py \
  --run-dir "<RUN_DIR>" \
  --baseline "25,1,3,1,0"
```

Das Skript prüft automatisch:
- `report.json`, `runtime_rules.json`, `decision_trace.jsonl`, `routing_summary.csv`, `profile_snapshot.json`
- `_meta`-Felder (profile_applied, generated_sections, prepended_sections, protected_sections)
- Laufwerte gegen optionale Baseline
- Unklar-Fälle mit Dateiname, art, payment_field, final_assignment_rule und Grund
- Gibt PASS/FAIL und ein Entscheidungssignal nach Projektregeln aus

Die Baseline für den Standardarchiv-Lauf lautet: `25,1,3,1,0`.

## Berichtstruktur
Berichte kurz und entscheidungsfähig mit:
1. Git-Ausgangszustand
2. Änderung / Prüfung
3. Tests oder Begründung ohne Tests
4. Abschlussstand
5. Bewertung / nächster Schritt
6. **Entscheidungssignal** (immer am Ende, gemäß Abschnitt Entscheidungssignale)

## Entscheidungssignale

Jeder Bericht endet mit genau einem der folgenden Entscheidungssignale.

### 1. ENTSCHEIDUNGSSIGNAL: WEITER IN CURSOR
Verwenden, wenn:
- Tests/Smoke-Test erfolgreich
- Working Tree clean
- keine Regression
- keine Produktivdaten betroffen
- keine Architekturentscheidung offen

Ausgabeformat:
```
ENTSCHEIDUNGSSIGNAL: WEITER IN CURSOR
EMPFOHLENER MODUS: Agent / Ask / Plan
CHATGPT NÖTIG: nein
ZAUBERWORT: Weiter nach Projektregeln.
```

### 2. ENTSCHEIDUNGSSIGNAL: CHATGPT FRAGEN
Verwenden, wenn:
- Architekturentscheidung offen
- Regression oder unerklärliche Abweichung
- mehrere fachlich sinnvolle Wege
- Scope-Erweiterung nötig
- Tests fehlschlagen und Ursache nicht eindeutig ist

Ausgabeformat:
```
ENTSCHEIDUNGSSIGNAL: CHATGPT FRAGEN
EMPFOHLENER MODUS: ChatGPT
CHATGPT NÖTIG: ja
FRAGE AN CHATGPT: <konkrete Frage>
```

### 3. ENTSCHEIDUNGSSIGNAL: NUTZERFREIGABE
Verwenden, wenn:
- Push
- Commit außerhalb kleiner freigegebener Tasks
- echter Zielordnerlauf
- produktive Dateien verschieben, umbenennen oder löschen
- Output außerhalb /tmp erzeugt werden soll

Ausgabeformat:
```
ENTSCHEIDUNGSSIGNAL: NUTZERFREIGABE
EMPFOHLENER MODUS NACH FREIGABE: Agent
CHATGPT NÖTIG: nein, außer Nutzer ist unsicher
FREIGABEFRAGE: Soll ich <konkrete Aktion> ausführen?
EMPFEHLUNG: freigeben / nicht freigeben / erst ChatGPT fragen
BEGRÜNDUNG: <kurze sachliche Begründung, warum die Freigabe fachlich sinnvoll oder riskant ist>
```

Cursor gibt immer eine klare Empfehlung mit Begründung aus – der Nutzer soll nicht nur gefragt werden, sondern eine fachliche Einschätzung erhalten.

### 4. ENTSCHEIDUNGSSIGNAL: STOPP
Verwenden, wenn:
- Working Tree unklar
- sensible Vollwerte gefunden
- unsicherer Pfad
- Originalschutz nicht sicher
- fehlende Datei
- Tests außerhalb Scope kaputt

Ausgabeformat:
```
ENTSCHEIDUNGSSIGNAL: STOPP
EMPFOHLENER MODUS: Ask oder ChatGPT
CHATGPT NÖTIG: je nach Grund ja/nein
GRUND: <konkret>
NÄCHSTER SCHRITT: <was geklärt werden muss>
```

## Zauberwort

Wenn Cursor am Ende meldet `ENTSCHEIDUNGSSIGNAL: WEITER IN CURSOR`, darf der Nutzer schreiben:

> **Weiter nach Projektregeln.**

Cursor wählt dann selbst den nächsten sicheren Schritt, führt ihn innerhalb der Projektregeln aus, prüft angemessen und berichtet kurz.

**Das Zauberwort darf niemals automatisch auslösen:**
- Push
- Produktivlauf (echter Zielordner)
- Löschen, Verschieben oder Umbenennen echter Dateien
- Scope-Erweiterungen

Für diese Aktionen ist weiterhin `ENTSCHEIDUNGSSIGNAL: NUTZERFREIGABE` erforderlich.

## Autonomer Fortsetzungsmodus

Vollständige Definition in `docs/roadmap/PDF_TOOL_CURSOR_AGENT_WORKFLOW.md`.

Kurzfassung: Wenn der Nutzer `Weiter nach Projektregeln.` schreibt und das letzte Signal
`WEITER IN CURSOR` war, darf Cursor **bis zu 3 kleine, eindeutig sichere Schritte**
nacheinander ausführen. Nach jedem Teilschritt intern prüfen:
Scope · Tests/Checks · Git diff · Working Tree · Signal wäre WEITER IN CURSOR.
Am Ende: zusammenfassenden Abschlussbericht ausgeben.

## Arbeitsweise
- Keine unnötigen Alternativen.
- Keine großen Architekturvorschläge bei kleinen Prüf- oder Git-Aufträgen.
- Kleine Aufträge kurz halten.
- Bei riskanten Änderungen stoppen und berichten.
- Bei eindeutigem, freigegebenem Scope selbstständig umsetzen, testen und berichten.
