# KI-Rechnungen — SaaS UI-v2 Profil-Draft Import/Export (lokal)

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_DRAFT_IMPORT_EXPORT_01` |
| **Datum** | 2026-07-20 |
| **Branch** | `main` |
| **Baseline HEAD** | `87163cd6fcfd943fa2f8240a5a486ef7581fe0d5` |
| **Initial Classification** | `READY_FOR_SAAS_UI_V2_PROFILE_DRAFT_IMPORT_EXPORT` |

## Mandatory Status

DIE UI-V2 KANN LOKALE GENERISCHE SAAS-PROFILENTWÜRFE SICHER IMPORTIEREN UND EXPORTIEREN; INTERNE ARBEITSPROFILE UND SAAS-DRAFTS BLEIBEN GETRENNT, ES GIBT KEIN CLOUD-SYNC-ODER MANDANTEN-PERSISTENZ-VERSPRECHEN, PRIVATE DEFAULTS SIND NICHT ENTHALTEN, DAS LOKALE HADI-PROFIL UND DIE INTERNE LAUNCHER-APP BLEIBEN UNVERÄNDERT, ES WURDE NICHT GEPUSHT UND KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET

---

## 1. Umgesetzt

| Datei | Rolle |
|---|---|
| `invoice_tool/ui_v2/saas_profile_store.py` | `export_draft` / `import_draft`; Export-Envelope; Schema/Kind/Private-Marker/Pfad-Guards |
| `invoice_tool/ui_v2/state.py` | `export_saas_draft` / `import_saas_draft`; Selection nach Import; Fehler lassen Prior-State |
| `invoice_tool/ui_v2/saas_profile_draft_list_view.py` | Aktionen „Exportieren“ / „Importieren“, Pfad-Platzhalter, Trennungshinweis |
| `invoice_tool/ui_v2/saas_profile_persistence_view.py` | UX-Labels für exported / imported |
| `invoice_tool/ui_v2/pages/profiles.py` | Import/Export-Verdrahtung |
| `invoice_tool/ui_v2/pages/configurations.py` | gleiche Verdrahtung |
| `tests/test_saas_ui_v2_profile_draft_import_export.py` | Envelope-, Private-, Corrupt-, Overwrite-, Profil-/Launcher-Guards |

### Export

- Exportiert genau den gewählten Draft an expliziten `export_path`
- Envelope: `schema_version`, `kind=saas_profile_draft_export`, `cloud=false`, `exported_at`, `draft`
- Keine privaten Defaults, keine Rechnungsdateien, keine internen Profile
- Nie `profile_config.local.json`

### Import

- Nur gültiges Envelope + erwartetes `kind` + `schema_version`
- Private Marker abgelehnt (SOMAA/Hadi/AMEX-1005/EP/Bismarck/Architektur/97368/DE189/voba)
- Gefährliche absolute/interne Pfade werden vor Persistenz entfernt
- Immer neuer Draft mit neuer ID — kein stilles Überschreiben
- Schreibzugriff nur im injizierbaren Store-Verzeichnis
- Beschädigte/falsche Dateien → sicherer Fehlerstatus

### Explizit nicht

- Cloud-/Auth-/Mandantenbackend
- Echter OS-FilePicker (Pfad-Platzhalter + State/Store getestet)
- Produktive Verarbeitung / Rechnungsimport
- Hadi/SOMAA Application-Support-Profil
- Interne Launcher-/Dock-App
- Routing / Recipient Guard / Supplier / Duplicate Lifecycle

---

## 2. Tests

Fokussierte Suite + `tests/test_ui_v2_*.py`: grün.

---

## 3. Nächster Task (Vorschlag)

`KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_DRAFT_FILE_PICKER_01`  
— optionale native FilePicker-Anbindung für Import/Export-Pfade, weiterhin ohne Cloud und ohne Hadi/SOMAA-Defaults.
