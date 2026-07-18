# KI-Rechnungen — SaaS UI-v2 Profilpersistenz UX-Härtung

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_UX_HARDENING_01` |
| **Datum** | 2026-07-18 |
| **Branch** | `main` |
| **Baseline HEAD** | `e1638c12d1fc9a1bcf09bcee048b91639a289143` |
| **Initial Classification** | `READY_FOR_SAAS_UI_V2_PROFILE_PERSISTENCE_UX_HARDENING` |

## Mandatory Status

DIE UI-V2 KENNZEICHNET GENERISCHE SAAS-PROFILENTWÜRFE UND IHRE LOKALE PERSISTENZ KLAR; INTERNE ARBEITSPROFILE UND SAAS-DRAFTS SIND IN DER UI GETRENNT, ES GIBT KEIN CLOUD-SYNC-VERSPRECHEN, PRIVATE DEFAULTS SIND NICHT ENTHALTEN, DAS LOKALE HADI-PROFIL UND DIE INTERNE LAUNCHER-APP BLEIBEN UNVERÄNDERT, ES WURDE NICHT GEPUSHT UND KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET

---

## 1. Umgesetzt

| Datei | Rolle |
|---|---|
| `invoice_tool/ui_v2/saas_profile_persistence_view.py` | Status-ViewModel/Presenter: Labels, Trennungstext, No-Cloud-Hinweis, Zeitstempel, Corrupt-Fehler |
| `invoice_tool/ui_v2/state.py` | Persistenz-Statusfelder + `saas_persistence_status_vm()` |
| `invoice_tool/ui_v2/saas_profile_store.py` | Corrupt-Label an UX angeglichen (`Lokaler Draft beschädigt`) |
| `invoice_tool/ui_v2/pages/profiles.py` | Persistenz-Statuspanel + Save/Load-Feedback |
| `invoice_tool/ui_v2/pages/configurations.py` | gleiches Statuspanel |
| `tests/test_saas_ui_v2_profile_persistence_view.py` | Blank/Saved/Loaded/Corrupt, Trennung, Private-/Cloud-Guards, Launcher-Guard |

### Sichtbare Status

| Fall | UX-Label |
|---|---|
| Blank / fehlende Datei | Nicht gespeichert |
| Save ok | Lokal gespeichert |
| Load ok | Lokal geladen |
| Beschädigte Datei | Lokaler Draft beschädigt |

### UX-Trennung

- Scope: „SaaS-Profilentwurf (lokal)“
- Trennung: „Dieser Entwurf gehört zur SaaS-/UI-v2-Variante und ist nicht das interne Arbeitsprofil.“
- Cloud: „Noch keine Cloud-Synchronisierung.“ (kein Sync-/Mandantenversprechen)

### Explizit nicht

- Cloud-/Auth-/Mandantenbackend
- Multi-Draft-Liste
- Produktive Verarbeitung
- Hadi/SOMAA Application-Support-Profil
- Interne Launcher-/Dock-App
- Routing / Recipient Guard / Supplier / Duplicate Lifecycle

---

## 2. Nächster Task (Vorschlag)

`KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_DRAFT_LIST_01`  
— optionale Liste mehrerer lokaler SaaS-Entwürfe, weiterhin ohne Cloud und ohne Hadi/SOMAA-Defaults.
