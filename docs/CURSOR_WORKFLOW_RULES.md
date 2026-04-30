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

## Berichtstruktur
Berichte kurz und entscheidungsfähig mit:
1. Git-Ausgangszustand
2. Änderung / Prüfung
3. Tests oder Begründung ohne Tests
4. Abschlussstand
5. Bewertung / nächster Schritt

## Arbeitsweise
- Keine unnötigen Alternativen.
- Keine großen Architekturvorschläge bei kleinen Prüf- oder Git-Aufträgen.
- Kleine Aufträge kurz halten.
- Bei riskanten Änderungen stoppen und berichten.
- Bei eindeutigem, freigegebenem Scope selbstständig umsetzen, testen und berichten.
