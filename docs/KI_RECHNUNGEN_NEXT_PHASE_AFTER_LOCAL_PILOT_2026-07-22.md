# Nächste Phase nach lokaler Pilotreife

Stand: 2026-07-22  
Ausgangspunkt: Produktversion 1 lokale Pilotversion mit Limitationen freigegeben  
Masterplan Prompt 1–12: abgeschlossen

## Empfehlung (erster Fokus)

**Kontrollierte echte OCR/AI-Sandbox-Validierung mit kopierten Daten** — als eigener, freizugebender Arbeitsschritt.

Die aktuelle Freigabe bleibt **nicht SaaS-bereit**. Voraussetzungen bleiben:

- keine Originalordner
- keine produktive Verarbeitung
- keine privaten Defaults
- Track A und Processing-Core nur mit expliziter Freigabe ändern
- ehrliche Nicht-Claims (nicht SaaS-bereit, kein DATEV-Produktivexport)

## Optionsübersicht (nicht priorisiert als erledigt)

| Option | Zweck | Hinweis |
|--------|-------|---------|
| Echte OCR/AI-Sandbox-Validierung | Validierung mit kopierten Daten und realen Engine-Läufen unter Sandbox-Grenze | Empfohlener nächster Fokus |
| Explizite Core dry/no-mutation API | Falls weiterhin nötig: klarer Dry-Run ohne Dateimutation | Nur mit Core-Freigabe |
| Kontrolliertes Produktivlauf-Design | Architektur/Policy für späteren Produktivlauf | Design only; keine Freigabe hier |
| Packaging/Build-Prompt | Separater macOS-/App-Build-Prompt | Nicht Teil von Prompt 12 |
| Installation/Distribution | Verteilungs- und Installationskonzept | Nach Packaging |
| SaaS-Architekturplan | Login/Mandant/Cloud-Produkt als Plan | Kein Claim auf aktuelle Reife |
| Auth/Tenant/Billing | Produkt- und Abrechnungsdesign | Außerhalb lokaler Pilotversion |
| DATEV-/Cloud-Export-Design | Produktivexport-Design | Design only; kein Produktivclaim |
| Legal/Tax Review | Steuer-/rechtliche Prüfung | Externe Freigabe nötig |
| Pilot-Feedback-Loop | Rückmeldungen aus lokaler Pilotnutzung sammeln | Unter Sandbox-Regeln |

## Was die nächste Phase nicht sein darf

- Stille Produktivfreigabe
- Originalordner-Nutzung
- SaaS-Ready-Claim ohne Architektur und Gates
- DATEV-/Cloud-Produktivexport ohne separates Design und Freigabe
- Track-A- oder Processing-Core-Änderungen ohne expliziten Task

## Statusanker

Aktuelle Freigabe bleibt:

`PRODUCT_VERSION_1_LOCAL_PILOT_RELEASED_WITH_LIMITATIONS`

bis ein späterer, dokumentierter Gate das bewusst ändert.
