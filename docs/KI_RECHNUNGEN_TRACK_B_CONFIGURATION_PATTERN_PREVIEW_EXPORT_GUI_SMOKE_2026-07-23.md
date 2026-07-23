# Track-B Configuration Pattern Preview Export GUI Smoke

**Task ID:** `KI_RECHNUNGEN_TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_01`  
**Masterplan:** Prompt 25/34  
**Date:** 2026-07-23  
**Product status (after this task):** `TRACK_B_CONFIGURATION_PATTERN_PREVIEW_EXPORT_GUI_SMOKE_PASS_WITH_CONFIG_COVERAGE_GAPS`

Explizit: **keine produktive Verarbeitung**, **keine realen Rechnungsordner**, **nicht SaaS-ready**, **nicht production-ready**.

---

## Purpose

Manuelle GUI-/Export-Verifikation nach Prompt 24 dokumentieren: UI-getriebener Sandbox-Lauf und Preview Export erzeugen ein konsistentes Current-State-Preview-Paket. Kein Code-Repair, außer bei Blocker.

---

## Baseline from Prompt 24

- Preview Export nutzt aktuellen UI-/Run-State.
- Freshness-Guard aktiv; Stale → `PREVIEW_EXPORT_STALE_STATE_BLOCKED`.
- Manifest: `exported_from_current_state=true`, `previous_export_reused=false`, `state_freshness_checked=true`, `state_freshness_result=pass`.
- Product status vorher: `TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_READY`.
- HEAD / origin/main Baseline: `44357c82cdb7f2a14a1e59e234e42d97efb4b628`
- Prompt-24 Feature-HEAD: `f509294ed96cdde86b9326e9f3dc2d9e0db0ad69`

Docs:

- `docs/KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_REPAIR_2026-07-23.md`
- `docs/audits/KI_RECHNUNGEN_TRACK_B_PREVIEW_EXPORT_STATE_FRESHNESS_REPAIR_2026-07-23.md`

---

## Manual GUI/export verification evidence

Product Owner hat UI-v2 manuell gestartet, kontrollierte Input-/Output-Ordner gewählt, Sandbox-Lauf ausgeführt, Preview Export ausgelöst und den neuesten Export-Ordner geprüft.

**Controlled input:** `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`  
**Controlled output:** `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`  
**Input PDF count:** 5 (unverändert)

Hochgeladene manuelle Evidenz (PO):

- fünf Preview-PDFs (inkl. LUMITOP/Bootshop/Böttcher/Luxvenum/Storno)
- `manifest.json` / `manifest.csv`
- `README_PREVIEW_EXPORT.md`
- `review-items.md`

---

## Latest export folder

`preview-export-track-b-dry-61ff6af993d7-20260723T123451630008Z`

Vollständiger Pfad:

`/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output/preview-export-track-b-dry-61ff6af993d7-20260723T123451630008Z`

Preview-PDFs liegen unter `files/`.

---

## Exported PDF names

1. `REVIEW_REQUIRED__SUGGESTED__2026-05-11_er_er_LUMITOP_476,00_paypal.pdf`
2. `REVIEW_REQUIRED__SUGGESTED__2026-05-15_er_er_1A-Bootshop.de_105,75_paypal.pdf`
3. `REVIEW_REQUIRED__SUGGESTED__2026-05-23_er_er_Böttcher_AG_84,39_card.pdf`
4. `REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-05-11_er_er_Luxvenum_LED_GmbH_154,95_FEHLT_payment_field.pdf`
5. `REVIEW_REQUIRED__SUGGESTED__INCOMPLETE__2026-06-18_er_storno_Böttcher_AG_68,94_FEHLT_payment_field.pdf`

**Stale export signals absent in exported filenames:**

- kein LUMITOP `500,00`
- kein 1A-Bootshop `80,55`
- kein Böttcher-Storno-Dateiname mit stale `er_er` (Stattdessen `er_storno`)

**Corrected export signals present:**

- LUMITOP `476,00`
- 1A-Bootshop `105,75`
- Böttcher Storno `er_storno`

---

## Manifest freshness metadata

Aus `manifest.json` des neuesten Export-Ordners:

| Feld | Wert |
|---|---|
| `state_source` | `processing_run_state.current` |
| `exported_from_current_state` | `true` |
| `previous_export_reused` | `false` |
| `state_freshness_checked` | `true` |
| `state_freshness_result` | `pass` |
| `copied_file_count` | `5` |
| `review_count` | `5` |
| `final_write` | `false` |
| `productive_mode_requested` | `false` |
| `source_mutation` | `false` |
| `claims_saas_ready` | `false` |
| `claims_production_ready` | `false` |
| `dry_run` / `preview_export` | `true` |

UI-Werte und Export-Dateinamen/Manifest/Review-Report stimmen überein.

---

## Source invoice value cross-check

| Beleg | Export-Dateiname Kern | Source-/Manifest-Cross-Check |
|---|---|---|
| LUMITOP | `476,00` / `paypal` | Total / PayPal `476,00` — nicht stale `500,00` |
| 1A-Bootshop | `105,75` / `paypal` | Gesamtpreis Brutto / PayPal `105,75` — nicht stale `80,55` |
| Böttcher Rechnung | `84,39` / `card` | Gesamtwert `84,39`; generische Karte, nicht AMEX |
| Luxvenum | `154,95` / `FEHLT_payment_field` | Betrag `154,95`; payment_field fehlt explizit |
| Böttcher Storno | `68,94` / `er_storno` | Gesamtwert `68,94`; STORNORECHNUNG → `art=storno`; payment_field fehlt explizit |

Input-SHA-256 (unverändert, keine Mutation):

- `320262919974.pdf` → `291510fd…`
- `420260091336.pdf` → `5ef12c1d…`
- `FA011466.pdf` → `50f62bc8…`
- `Rechnung RE-202605-14594.pdf` → `7b24dcd7…`
- `Rechnung-2026156019-102201.pdf` → `678751f9…`

Manifest belegt byte-gleiche Preview-Kopien (`source_sha256` = `preview_sha256`, `source_mutated=no`).

---

## Configuration guidance evidence

Aus `README_PREVIEW_EXPORT.md` und `review-items.md`:

- **PayPal guidance:** „PayPal erkannt, aber keine aktive PayPal-Konfiguration vorhanden.“ → Aktion: PayPal-Konfiguration ergänzen oder manuell prüfen.
- **Generic card / no AMEX:** „Kreditkarte erkannt, aber AMEX nicht belegt; keine passende Nicht-AMEX-Karten-Konfiguration vorhanden.“ / Matching-Grund `generic credit card detected, AMEX not proven`.
- **Missing payment_field:** Luxvenum und Böttcher Storno mit `FEHLT_payment_field`; Nutzerhinweis „Zahlungsfeld nicht sicher erkannt…“; fehlende Platzhalter nicht stillschweigend entfernt.
- Suggested actions / sichere nächste Schritte sichtbar: Konfiguration ergänzen; anpassen; manuell prüfen; als Unklar belassen.
- Keine automatische Erstellung/Änderung von Nutzerkonfigurationen.

---

## Safety guarantees

- Preview only / Review required
- Keine finalen Produktivdateien (`final_write=false`)
- Originale unverändert (`source_mutation=false`)
- Produktivverarbeitung gesperrt (`productive_mode_requested=false`)
- Keine realen Rechnungsordner berührt (nur kontrollierte Testpfade)
- nicht SaaS-ready
- nicht production-ready
- Release-Tags unverändert (`internal-working-version-2026-07-21`, `product-v1-local-pilot-2026-07-22`)
- Track A / Processing-Core unverändert in diesem Task

---

## What is now proven

1. Manueller UI-Sandbox-Lauf + Preview Export erzeugen Current-State-Paket.
2. Export-Dateinamen zeigen korrigierte Beträge und Storno-Art.
3. Manifest-Freshness-Metadaten passen zur Prompt-24-Reparatur.
4. Review-/Config-Guidance bleibt sichtbar (PayPal, Non-AMEX-Card, missing payment_field).
5. Input bleibt unverändert; keine produktive Verarbeitung.

---

## What is still not proven

- Kein sicherer Nutzer-Flow zum Erstellen/Bearbeiten von Konfigurationsregeln in der UI.
- Keine produktive Freigabe / kein Final-Export.
- Keine SaaS-/Production-Reife.

---

## Remaining gap

Aktive Konfigurationsabdeckung fehlt weiterhin für:

- PayPal (erkannt, aber keine aktive PayPal-Konfiguration)
- generische Nicht-AMEX-Karte (erkannt, AMEX nicht belegt)

Deshalb bleiben diese Fälle begründet **Unklar**. Nächster sinnvoller Schritt: sicherer Konfigurations-Regel-Erstellen-/Bearbeiten-Flow.

---

## Test result

Siehe Audit — Docs-/Safety-Tests und volle Track-B / UI-v2 / SaaS-Suite.

---

## No productive processing

Ja — Preview/Sandbox only.

## No real invoice folders

Ja — nur `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/...`.

## Not SaaS-ready

Explizit unverändert — **nicht SaaS-ready**.

## Not production-ready

Explizit unverändert — **nicht production-ready**.

## Next step

`KI_RECHNUNGEN_TRACK_B_CONFIGURATION_RULE_CREATION_AND_EDITING_FLOW_01`
