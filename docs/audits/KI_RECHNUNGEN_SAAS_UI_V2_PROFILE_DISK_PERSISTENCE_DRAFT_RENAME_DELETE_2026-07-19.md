# KI-Rechnungen — SaaS UI-v2 Profil-Draft Rename/Delete (lokal)

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_DRAFT_RENAME_DELETE_01` |
| **Datum** | 2026-07-19 |
| **Branch** | `main` |
| **Baseline HEAD** | `e910c762b368a6abfdfacaadb4a9049e8531accc` |
| **Initial Classification** | `READY_FOR_SAAS_UI_V2_PROFILE_DRAFT_RENAME_DELETE` |

## Mandatory Status

DIE UI-V2 KANN LOKALE GENERISCHE SAAS-PROFILENTWÜRFE SICHER UMBENENNEN UND LÖSCHEN; INTERNE ARBEITSPROFILE UND SAAS-DRAFTS BLEIBEN GETRENNT, ES GIBT KEIN CLOUD-SYNC-ODER MANDANTEN-PERSISTENZ-VERSPRECHEN, PRIVATE DEFAULTS SIND NICHT ENTHALTEN, DAS LOKALE HADI-PROFIL UND DIE INTERNE LAUNCHER-APP BLEIBEN UNVERÄNDERT, ES WURDE NICHT GEPUSHT UND KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET

---

## 1. Umgesetzt

| Datei | Rolle |
|---|---|
| `invoice_tool/ui_v2/saas_profile_store.py` | `rename_draft` / `delete_draft`; Anzeigename-Normalisierung; Pfad-Guard im Store-Verzeichnis |
| `invoice_tool/ui_v2/state.py` | `rename_saas_draft` / `delete_saas_draft` mit Bestätigung für aktiven Draft; sichere `selected_draft_id`-Aktualisierung |
| `invoice_tool/ui_v2/saas_profile_draft_list_view.py` | Aktionen „Entwurf umbenennen“ / „Entwurf löschen“, Warntext, Rename-Feld |
| `invoice_tool/ui_v2/saas_profile_persistence_view.py` | UX-Labels für renamed / deleted / delete_needs_confirm |
| `invoice_tool/ui_v2/pages/profiles.py` | Rename/Delete-Verdrahtung |
| `invoice_tool/ui_v2/pages/configurations.py` | gleiche Verdrahtung |
| `tests/test_saas_ui_v2_profile_draft_rename_delete.py` | Rename/Delete-, Corrupt-/Missing-, Private-/Cloud-/Launcher-/Profil-Guards |

### Rename

- Ändert nur `display_name` / Metadaten (`updated_at`)
- Draft-ID und Dateiname bleiben unverändert
- Leere Namen werden abgelehnt
- Steuerzeichen werden zu Whitespace normalisiert und kollabiert
- Beschädigte Drafts: listen-/löschbar, nicht still umbenannt

### Delete

- Entfernt nur `{draft_id}.json` im injizierbaren Store-Verzeichnis
- Fehlende Datei → sicherer Fehlerstatus, kein Absturz
- Aktiver Draft: zweistufig (`delete_needs_confirm` → bestätigt löschen)
- Nach Delete des aktiven Drafts: Selection auf verbleibenden Draft oder leer; In-Memory-Draft nicht still mit Defaults überschrieben

### Explizit nicht

- Cloud-/Auth-/Mandantenbackend
- Papierkorb/Undo
- Produktive Verarbeitung
- Hadi/SOMAA Application-Support-Profil
- Interne Launcher-/Dock-App
- Routing / Recipient Guard / Supplier / Duplicate Lifecycle

---

## 2. Tests

Fokussierte Suite + `tests/test_ui_v2_*.py`: grün.

---

## 3. Nächster Task (Vorschlag)

`KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_DRAFT_IMPORT_EXPORT_01`  
— optional begrenzter lokaler Export/Import generischer SaaS-Entwürfe, weiterhin ohne Cloud und ohne Hadi/SOMAA-Defaults.
