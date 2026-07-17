# KI-Rechnungen — SaaS UI-v2 Profile Surface an generisches Modell anbinden

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_SURFACE_WIRE_GENERIC_MODEL_01` |
| **Datum** | 2026-07-17 |
| **Branch** | `main` |
| **Baseline HEAD** | `db7d8952e4d5bff48706a6dfc5c731d2e06e023b` |
| **Initial Classification** | `READY_FOR_SAAS_UI_V2_GENERIC_PROFILE_WIRING` |

## Mandatory Status

DIE UI-V2-PROFILOBERFLÄCHE IST AN DAS GENERISCHE SAAS-PROFILMODELL ANGEBUNDEN; DIE DEFAULTS SIND GENERISCH UND OHNE HADI-/SOMAA-/AMEX-1005-/EP-VORBELEGUNG, DIE INTERNE LAUNCHER-APP BLEIBT UNVERÄNDERT, ES WURDE NICHT GEPUSHT, KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET UND KEINE REALEN RECHNUNGSORDNER VERÄNDERT

---

## 1. Umgesetzt

| Datei | Rolle |
|---|---|
| `invoice_tool/ui_v2/saas_profile_surface.py` | Adapter/Presenter: `build_blank_saas_profile()`, Create-Defaults, Surface-VM, Private-Default-Guard |
| `invoice_tool/ui_v2/pages/profiles.py` | Create nutzt `blank_profile_draft()`; Surface-Felder/Labels aus generischem Modell |
| `invoice_tool/ui_v2/pages/configurations.py` | Create-Overlay + generischer Name-Placeholder (kein „American Express“) |
| `tests/test_saas_ui_v2_profile_surface.py` | Defaults, Private-Guard, Feldvertrag, Launcher unverändert |

### Surface-Felder (UI)

- Profilname / Neues Profil
- Scanmodell wählen
- Dokumenttyp
- Matching-Bedingungen
- Ziel
- Dateinamensmuster
- Review-Regel
- Zahlung/Kontierung optional

### Explizit nicht

- Produktive Verarbeitung
- Persistenz aller Surface-Felder jenseits bestehender Profile/Config-Write-Pfade
- Änderungen an internem Launcher / Dock-App
- Routing / Recipient Guard / Supplier / Duplicate Lifecycle

---

## 2. Private-Default-Guard

Create-/Blank-Payloads laufen über `assert_saas_defaults_are_generic` / `assert_ui_surface_defaults_are_generic`.  
Geprüfte Marker u. a.: SOMAA, Hadi, AMEX-1005, EP, Bismarck, Steuer-/Adressfragmente.

---

## 3. UI-v2-Altfehler (Abgrenzung)

Bekannt vor diesem Task:

- `tests/test_ui_v2_ux_control_interactions.py::test_ui_v2_ux_interaction_gate_passes`
- Ursache: dirty UI-v2 WIP / Placeholder-/Handler-Contracts (nicht durch diesen Task eingeführt)
- Nicht abgeschwächt; fokussierte SaaS-Suite muss grün bleiben; keine neuen UI-v2-Fehler erwartet

Vorhandener Dirty-State an Layout-/UX-WIP-Dateien bleibt außerhalb des Staging-Scopes dieses Commits, außer den gezielten Profile-/Config-Anbindungen.

---

## 4. Nächster Task (Vorschlag)

`KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_PERSISTENCE_AND_CONFIG_EDITOR_GENERIC_01`  
— vollständige Persistenz der Surface-Felder + Aufräumen des UI-v2 UX-Interaction-Altfehlers ohne Private Defaults.
