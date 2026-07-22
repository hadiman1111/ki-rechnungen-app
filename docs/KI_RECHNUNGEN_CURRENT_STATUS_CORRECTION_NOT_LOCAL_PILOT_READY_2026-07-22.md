# Statuskorrektur — noch nicht lokal pilotfähig

Stand: 2026-07-22  
Task: `KI_RECHNUNGEN_SAAS_COMPLETION_MASTERPLAN_AND_PROMPT_SEQUENCE_01`  
Arbeitsverzeichnis: `KI-Rechnungen-App`  
HEAD-Bezug: `65a735f3fd7df8d65f5623519e3897680d6cb276`

## 1. Bisheriger, zu früher Status

Die vorherige 12-Prompt-Sequenz schloss mit:

`PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS`

und dem Release-Tag `product-v1-local-pilot-2026-07-22`.

Diese Interpretation wird **verworfen**. Der Tag bleibt historisch bestehen, darf aber **nicht** als aktuelle Freigabe gelesen werden.

## 2. Warum der frühere Status verfrüht war

Ein lokaler Pilot ist nicht akzeptabel, wenn **kein echter Verarbeitungs­lauf** mit kopierten PDFs möglich ist.

Die vorherige Freigabe bewertete vor allem:

- Workspace-/Status-UI
- Profil-/Konfigurationsauflösung
- Sandbox-Gates und Originalschutz
- Review-/Export-**Struktur** und Synthetic-/Copied-Validation auf Adapter-Ebene
- produktive Sperre

Sie bewertete **nicht** als harte Pflicht:

- echten Lauf über bestehende Processing-Logik oder eine sichere Dry-Run-Äquivalenz
- echte Run-Ergebnisse aus kopierten PDFs
- anerkannte / unklare / fehlgeschlagene Fälle aus einem realen Laufzustand

Ohne diese Fähigkeiten ist „lokale Pilotversion“ inhaltlich falsch.

## 3. Korrigierter aktueller Status

**`NOT_LOCAL_PILOT_READY_CORE_DRY_RUN_API_REQUIRED`**

Korrekte Sprache:

- noch nicht lokal pilotfähig
- Core-Dry-Run-Schnittstelle erforderlich
- SaaS-Reife noch nicht erreicht

## 4. Evidenz aus dem Repo-Stand

### 4.1 Core-Bridge hat Path B gewählt

`invoice_tool/ui_v2/core_bridge.py` dokumentiert und implementiert Path B:

- bestehende Processing-Core-API ist kein sicherer Dry-/No-Mutation-Einstieg
- Bridge importiert/ruht den Core **nicht**
- Ergebnisstatus: `requires_core_dry_run_contract` / `core_dry_run_contract_required`
- keine erfundenen Erkennungs-/Review-/Export-Zeilen

Audit: `docs/audits/KI_RECHNUNGEN_TRACK_B_CORE_BRIDGE_SANDBOX_DRY_RUN_PARITY_2026-07-22.md`  
Klassifikation dort: `TRACK_B_CORE_BRIDGE_DRY_RUN_CONTRACT_REQUIRED_COMMITTED_AND_PUSHED`

### 4.2 `run_once` hat keinen sicheren Dry-Run-/No-Mutation-Vertrag

`invoice_tool.run.run_once` (Track A / Internal) schreibt Ausgaben, archiviert Quellen und legt technische Artefakte unter Application Support an. Es gibt keinen dokumentierten `dry_run`-/`no_mutation`-Vertrag für Track B.

Deshalb ist `run_once` **kein** sicherer Track-B-Sandbox-Einstieg.

### 4.3 Track B kann noch keinen echten kopierten-PDF-Lauf ausführen

Track-B UI-v2 kann:

- Workspace/Status zeigen
- Profil/Konfiguration auflösen
- kompakten Blocker-Status zeigen
- Originalordner schützen
- Produktivmodus gesperrt halten
- Export-/Reporting-Vorschaustruktur zeigen

Track-B UI-v2 kann **noch nicht**:

- echte Verarbeitung kopierter PDFs starten
- den internen Processing-Core sicher aufrufen
- echte Run-Ergebnisse aus kopierten PDFs erzeugen
- als echter lokaler Pilot gelten

## 5. Mindestkriterien lokaler Pilot

Ein echter lokaler Pilot muss mindestens:

1. kopierten Eingangsordner wählen  
2. expliziten Sandbox-Ausgabeordner wählen  
3. kontrollierten Sandbox-Lauf starten  
4. echte bestehende Processing-Logik oder sichere Dry-Run-Äquivalenz nutzen  
5. Originalordner nie mutieren  
6. erkannte Dokumente zeigen  
7. unklare/Prüffälle zeigen  
8. Fehlerfälle zeigen  
9. geplante Zielpfade zeigen  
10. Export-/Report-Vorschau aus realem Laufzustand erzeugen  

Erst wenn diese Kriterien bestehen, darf „lokal pilotfähig“ beansprucht werden.

## 6. Sofort erforderliche Bedingung

**Core-Dry-Run Sandbox API**

Nächster ausführbarer Implementierungs­prompt:

`KI_RECHNUNGEN_CORE_DRY_RUN_SANDBOX_API_CONTRACT_01`

## 7. Was dieser Status explizit nicht bedeutet

- keine SaaS-Reife
- keine produktive Verarbeitung
- keine Produktionsreife
- kein abgeschlossenes Release im Sinne einer aktuellen Freigabe
- der alte Tag `product-v1-local-pilot-2026-07-22` ist historisch und korrigierungsbedürftig in der Lesart, nicht gelöscht
