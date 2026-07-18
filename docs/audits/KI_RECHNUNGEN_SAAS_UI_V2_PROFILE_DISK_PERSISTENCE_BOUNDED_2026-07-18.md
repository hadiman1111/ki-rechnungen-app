# KI-Rechnungen — SaaS UI-v2 Profilentwürfe lokale Disk-Persistenz (bounded)

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_BOUNDED_01` |
| **Datum** | 2026-07-18 |
| **Branch** | `main` |
| **Baseline HEAD** | `62a4133866f963d44bba02c77f1b48d85eb0d219` |
| **Initial Classification** | `READY_FOR_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE` |

## Mandatory Status

DIE UI-V2 KANN GENERISCHE SAAS-PROFILENTWÜRFE LOKAL SPEICHERN UND LADEN; PRIVATE HADI-/SOMAA-/AMEX-1005-/EP-DEFAULTS SIND NICHT ENTHALTEN, DAS LOKALE HADI-PROFIL UND DIE INTERNE LAUNCHER-APP BLEIBEN UNVERÄNDERT, ES WURDE NICHT GEPUSHT, KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET UND KEINE REALEN RECHNUNGSORDNER VERÄNDERT

---

## 1. Umgesetzt

| Datei | Rolle |
|---|---|
| `invoice_tool/ui_v2/saas_profile_store.py` | JSON Save/Load für generische SaaS-Drafts; injizierbarer Pfad; Validierung; Korrupt-Fehlerstatus |
| `invoice_tool/ui_v2/state.py` | `saas_disk_store`, Save/Load-Hooks, Persistenz-Label |
| `invoice_tool/ui_v2/pages/profiles.py` | Status + „Entwurf lokal speichern/laden“ |
| `invoice_tool/ui_v2/pages/configurations.py` | Persistenz-Status (kein Cloud-Claim) |
| `tests/test_saas_ui_v2_profile_store.py` | Roundtrip, Private-Guard, Missing/Corrupt, tmp_path, Launcher-Guard |

### Store-Pfad-Strategie

- Standard: `~/Library/Application Support/KI-Rechnungen-SaaS-UI-v2/drafts/saas_profile_draft.json`
- Isoliert von `~/Library/Application Support/KI-Rechnungen` (Hadi/SOMAA-Arbeitsprofil)
- Tests nutzen ausschließlich injizierten `tmp_path`
- `profile_config.local.json` wird nie geschrieben

### Verhalten

| Fall | Ergebnis |
|---|---|
| Save gültiger Draft | JSON geschrieben, Status `Lokal gespeichert` |
| Load vorhandene Datei | Draft rekonstruiert, Status `Lokal geladen` |
| Fehlende Datei | generischer Blank-Draft, Status `Nicht gespeichert` |
| Beschädigtes JSON | `ok=False`, Status `Beschädigte Datei`, kein stiller Fallback auf falsche Defaults |
| Private Marker | Save/Load abgelehnt |

### Explizit nicht

- Cloud-/Auth-/Mandantenbackend
- Produktive Verarbeitung
- Hadi/SOMAA Application-Support-Profil
- Interne Launcher-/Dock-App
- Routing / Recipient Guard / Supplier / Duplicate Lifecycle

---

## 2. Nächster Task (Vorschlag)

`KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_DISK_PERSISTENCE_UX_HARDENING_01`  
— optional: Draft-Liste mehrerer lokaler Entwürfe, klarere Trennung Arbeitsprofil vs. SaaS-Draft in der UI, weiterhin ohne Cloud.
