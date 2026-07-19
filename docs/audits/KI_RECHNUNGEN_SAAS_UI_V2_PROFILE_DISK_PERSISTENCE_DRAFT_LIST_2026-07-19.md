# KI-Rechnungen — SaaS UI-v2 Profil-Draft-Liste (lokal)

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_DRAFT_LIST_01` |
| **Datum** | 2026-07-19 |
| **Branch** | `main` |
| **Baseline HEAD** | `d7a9c3ff218fb94c0e2fa1854126e17798e2de33` |
| **Initial Classification** | `READY_FOR_SAAS_UI_V2_PROFILE_DRAFT_LIST` |

## Mandatory Status

DIE UI-V2 KANN MEHRERE GENERISCHE SAAS-PROFILENTWÜRFE ALS LOKALE LISTE VERWALTEN; INTERNE ARBEITSPROFILE UND SAAS-DRAFTS BLEIBEN GETRENNT, ES GIBT KEIN CLOUD-SYNC-ODER MANDANTEN-PERSISTENZ-VERSPRECHEN, PRIVATE DEFAULTS SIND NICHT ENTHALTEN, DAS LOKALE HADI-PROFIL UND DIE INTERNE LAUNCHER-APP BLEIBEN UNVERÄNDERT, ES WURDE NICHT GEPUSHT UND KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET

---

## 1. Umgesetzt

| Datei | Rolle |
|---|---|
| `invoice_tool/ui_v2/saas_profile_store.py` | `list_drafts` / `create_draft` / `load_draft` / `save_draft`; Draft-ID, Anzeigename, Zeitstempel; eine JSON-Datei pro Entwurf unter `drafts/` |
| `invoice_tool/ui_v2/saas_profile_draft_list_view.py` | Presenter/Panel „Lokale SaaS-Entwürfe“ inkl. Trennungstext und No-Cloud-Hinweis |
| `invoice_tool/ui_v2/state.py` | `saas_selected_draft_id`, Create/Select/Load/Save für die lokale Liste |
| `invoice_tool/ui_v2/pages/profiles.py` | Draft-Liste + Aktionen auf der Profilseite |
| `invoice_tool/ui_v2/pages/configurations.py` | gleiche Draft-Liste auf der Konfigurationsseite |
| `tests/test_saas_ui_v2_profile_draft_list.py` | Create/List/Load/Save, Corrupt/Missing, Private-/Cloud-/Launcher-/Profil-Guards |

### ID-/Namensstrategie

- Draft-ID: `draft_<12 hex>` (UUID-basiert)
- Anzeigename: Nutzerwert oder generisch `Lokaler Entwurf N`
- Metadaten in JSON: `draft_id`, `display_name`, `created_at`, `updated_at`

### Speicherstrategie

- Root: `~/Library/Application Support/KI-Rechnungen-SaaS-UI-v2/drafts/` (in Tests: injizierter `tmp_path`)
- Pro Entwurf eine JSON-Datei `{draft_id}.json`
- `persistence: local_disk_only`, `cloud: false`
- Kein Zugriff auf `profile_config.local.json` / Hadi-Application-Support-Profile

### Fehlerfälle

- Beschädigte Datei: in der Liste als „beschädigt“; Load setzt In-Memory-Drafts nicht überschreibend zurück
- Fehlende Datei: sicherer Fehlerstatus, kein Absturz, kein Default-Overwrite

### Explizit nicht

- Cloud-/Auth-/Mandantenbackend
- Sharing / Versionshistorie / Import-Export
- Produktive Verarbeitung
- Hadi/SOMAA Application-Support-Profil
- Interne Launcher-/Dock-App
- Routing / Recipient Guard / Supplier / Duplicate Lifecycle

---

## 2. Tests

Fokussierte Suite + `tests/test_ui_v2_*.py`: grün.

---

## 3. Nächster Task (Vorschlag)

`KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_DRAFT_RENAME_DELETE_01`  
— optional Anzeigename umbenennen und sicheres lokales Löschen einzelner SaaS-Entwürfe, weiterhin ohne Cloud und ohne Hadi/SOMAA-Defaults.
