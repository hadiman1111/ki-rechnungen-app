# Track-B Configuration Product Restructure — 2026-07-27

Task: `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PRODUCT_RESTRUCTURE_01`

## Goal

Die Seite „Konfigurationen“ erklärt produktverständlich:

1. Woran erkennt die App diese Belege?
2. Was passiert dann damit?
3. Wie heißt die Datei danach?
4. Wohin kommt sie?
5. Muss der Nutzer später prüfen?

## Changes

- Aktives Profil: volle Breite, klickbarer Profilname
- „Neue Konfiguration erstellen“ nahe der Konfigurationsliste
- Erweiterte Hinweise / Import-Export: nicht primär; nur SHOW_DEV_SURFACES
- Labels: Name der Konfiguration, Erkennen wenn …, Prüfverhalten, Schreibweisen
- Dokumenttyp: Dropdown (Rechnung / Storno / Gutschrift / Sonstiges)
- Erkennung: Regelgruppe mit Merkmal / Vergleich / Schreibweisen + Verknüpfung
- Synonyme (amex / American Express) als Varianten-Chips
- Prüfverhalten: Auswahl (unterstützt: Bei Unsicherheit in Prüfung)
- Zahlung/Kontierung: nicht mehr unklarer Primär-Freitext (advanced/dev)
- Zielordner: voller Pfad sichtbar
- Kurzüberblick in Klartext vor dem Speichern

## Safety

- Kein Track-A / Processing-Core geändert
- Kein run_once / productive write
- Keine realen Rechnungsordner
- Release-Tags unverändert

## Classification

`TRACK_B_CONFIGURATION_PRODUCT_RESTRUCTURE_READY_COMMITTED_AND_PUSHED` (nach Commit/Push)
