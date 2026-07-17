# KI-Rechnungen — SaaS UI-v2 Profil-/Konfigurationsentwürfe generisch verwalten

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_PERSISTENCE_AND_CONFIG_EDITOR_GENERIC_01` |
| **Datum** | 2026-07-17 |
| **Branch** | `main` |
| **Baseline HEAD** | `c773dcd5e19abb3b7f5e5ed06167c5671dba84f0` |
| **Initial Classification** | `READY_FOR_SAAS_UI_V2_PROFILE_PERSISTENCE_BLOCK` |

## Mandatory Status

DIE UI-V2 VERWALTET GENERISCHE PROFIL- UND KONFIGURATIONSENTWÜRFE; DIE DEFAULTS BLEIBEN OHNE HADI-/SOMAA-/AMEX-1005-/EP-VORBELEGUNG, DIE INTERNE LAUNCHER-APP BLEIBT UNVERÄNDERT, ES WURDE NICHT GEPUSHT, KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET UND KEINE REALEN RECHNUNGSORDNER VERÄNDERT

---

## 1. Umgesetzt

| Datei | Rolle |
|---|---|
| `invoice_tool/ui_v2/saas_profile_state.py` | In-Memory `SaasProfileDraft` / `SaasConfigurationDraft` + Validierung + generische Editorfelder |
| `invoice_tool/ui_v2/state.py` | `saas_draft_store` im UI-v2-State |
| `invoice_tool/ui_v2/pages/profiles.py` | Editierbare Surface-Felder an Draft-Store |
| `invoice_tool/ui_v2/pages/configurations.py` | Generischer Config-Editor + Reorder/Aktivieren/Deaktivieren |
| `invoice_tool/ui_v2/saas_profile_surface.py` | Create-Draft ohne vorbelegten Namen; Hint statt Placeholder-Marker |
| `tests/test_saas_ui_v2_profile_state.py` | Draft/Validierung/Private-Guard/UX-Gate |

### Draft-Felder

- Profilname, Scanmodell, Dokumenttyp
- Matching Conditions, Ziel, Dateinamensmuster
- Review-Regel, Zahlung/Kontierung optional

### Explizit nicht

- Cloud-/User-Persistenz
- Auth, Billing, SaaS-Deployment
- Produktive Verarbeitung
- Interne Launcher-/Dock-App
- Routing / Recipient Guard / Supplier / Duplicate Lifecycle

---

## 2. Private-Default-Guard

Blank-Drafts laufen über `assert_saas_defaults_are_generic` / `find_private_saas_default_violations`.  
Keine Hadi-/SOMAA-/AMEX-1005-/EP-Vorbelegung in SaaS-Defaults.

---

## 3. UI-v2-UX-Altfehler

Behoben:

- Speichern-Label im Create-Modus (Handler-Contract)
- Aktivieren/Deaktivieren-Buttons
- `reorder_configurations` verdrahtet (Nach oben/unten)
- Placeholder-Auditor: `hint` / `GENERIC_CONFIG_NAME_HINT` statt Placeholder-Marker
- Create-Profilname leer → Feldvalidierung greift

Ergebnis: `tests/test_ui_v2_*.py` → 19 passed, 44 skipped, 0 failed.

---

## 4. Nächster Task (Vorschlag)

`KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_BOUNDED_01`  
— optionale, begrenzte Persistenz der generischen Surface-Felder jenseits Name/Scanmodell, weiterhin ohne private Defaults und ohne Cloud.
