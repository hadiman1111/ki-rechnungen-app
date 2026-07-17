# KI-Rechnungen — SaaS Product Variant: Roter Faden & nächster Entwicklungsblock

| Feld | Wert |
|---|---|
| **Task ID** | `KI_RECHNUNGEN_SAAS_PRODUCT_VARIANT_RED_THREAD_AND_NEXT_DEVELOPMENT_BLOCK_01` |
| **Datum** | 2026-07-17 |
| **Branch** | `main` |
| **Baseline HEAD** | `66e0ab203c4e9b727900735f7ad2f79388c52a63` |
| **Initial Classification** | `READY_FOR_SAAS_RED_THREAD_BLOCK` |
| **Gewählter Block** | **A — SaaS Profile/Configuration Model Surface** (Foundation) |

## Mandatory Status

DER ROTE FADEN DER SAAS-PRODUKTVARIANTE IST WIEDERHERGESTELLT UND EIN ERSTER GENERISCHER ENTWICKLUNGSBLOCK WURDE UMGESETZT; DIE INTERNE LAUNCHER-APP BLEIBT ALS STABILER INTERNER STRANG UNVERÄNDERT, ES WURDE NICHT GEPUSHT, KEINE PRODUKTIVEN RECHNUNGEN VERARBEITET UND KEINE REALEN RECHNUNGSORDNER VERÄNDERT

---

## 1. Verbindlicher Roter Faden

1. **Interner Launcher** (`app_internal_launcher.py`, `invoice_tool/internal_launcher/`) bleibt die stabile interne Betriebsoberfläche für Hadi/SOMAA. Kein Redesign, kein Cutover zur Endkunden-UI.
2. **UI-v2** (`app_ui_v2.py`, `invoice_tool/ui_v2/`) ist die führende externe Produktoberfläche der SaaS-Variante.
3. **Verarbeitungskern** (`invoice_tool.run` / CLI) wird als generische Service-Schicht genutzt; UI-v2 koppelt nicht an den internen Launcher.
4. **Hadi-/SOMAA-Regeln** existieren nur als lokales Beispiel-/Arbeitsprofil (Application Support / lokale JSON), nicht als SaaS-Produktdefault.
5. SaaS braucht konfigurierbare Nutzerprofile: Scanmodell, Matching, Empfänger-/Absenderlogik, Ziele, Dateinamen, Zahlungs-/Kontierungshinweise, Review-Regeln.
6. Keine globale Produktlogik darf `SOMAA`, `Hadi`, `AMEX-1005`, `EP` oder ähnliche private Defaults voraussetzen.

### Stream-Grenze

| Strang | Entry | Package | Rolle |
|---|---|---|---|
| Intern | `app_internal_launcher.py` | `invoice_tool.internal_launcher` | Stabiler lokaler Betrieb |
| Extern / SaaS UI | `app_ui_v2.py` | `invoice_tool.ui_v2` | Führende Produkt-UI |
| Kern | `python -m invoice_tool.run` | `invoice_tool.*` (ohne UI) | Generischer Verarbeitungsdienst |
| Legacy UI | `app_main.py` / `gui.py` | `invoice_tool.ui_*` | Eingefroren, kein Feature-Pfad |

---

## 2. Inventar (Read-only)

### A. SaaS / UI-v2 Bestand

| Bereich | Stand |
|---|---|
| Einstieg | `app_ui_v2.py` → `invoice_tool.ui_v2.app` |
| Navigation | Arbeitsbereich, Konfigurationen, Profile (+ Review/Settings Pages) |
| Profile/Config Write | Adapter vorhanden (`profile_write_adapter`, `configuration_write_adapter`) |
| Upload/Verarbeitung in UI-v2 | **noch keine** produktive Service-Grenze; Workspace liest Runs read-only / Preview |
| Review | `pages/review.py` + `review_reader` (passiv) |
| Tests/Gates | `tests/test_ui_v2_*.py`, Design-/Import-Boundary-Scripts |
| Offene Schuld | Dirty WIP an UI-v2-Dateien; Rendering-Checks erwarten teils Label „SOMAA Profil“ |

### B. Verarbeitungskern

Generische Bausteine vorhanden bzw. im Worktree vorbereitet: Profile Compiler, Target Routing, Recipient Guard, Supplier Rules, Duplicate Lifecycle, Scan Models, Configuration Model, Profile Store, CLI `run`.

### C. Hadi-/SOMAA-Regelstatus

| Ort | Bewertung |
|---|---|
| Lokales Arbeitsprofil (Application Support) | Erlaubt als lokales Profil |
| `profile_config.example.json` | **SOMAA-/AMEX-Beispiel** — nicht SaaS-Default |
| `CategoryId` Enum `ai`/`ep`/`private`/`unklar` im Schema | Tenant-lastig; später generalisieren |
| `SOMAA_CANONICAL_FILENAME_TEMPLATE` / `somaa_canonical_*` | Lokaler/kanonischer Helfer — nicht SaaS-Blank |
| `recipient_guard` SOMAA-Marker in Reasons | Kernlogik mit Tenant-Spuren; aus SaaS-Defaults fernhalten |
| UI-v2 `rendering_checks` Label „SOMAA Profil“ | UI-Schuld; nicht Produkt-Default-Logik |
| Interner Launcher Docstrings „SOMAA“ | Interner Strang — belassen |

### D. Generisches Produktmodell (Soll)

Profile · Scanmodell · Matching Conditions · Filename Pattern · Destination · Review Queue · Unklar · Duplicate Handling · Supplier Rules · Recipient Guard — als **konfigurierbare** Konzepte, nicht als feste SOMAA-Werte.

---

## 3. Was in diesem Task implementiert wurde (Block A Foundation)

Neue, isolierte Dateien (keine Änderung an internem Launcher, keine produktiven Pfade):

| Datei | Zweck |
|---|---|
| `invoice_tool/saas_product_model.py` | Generische SaaS-Profil-/Konfigurationsoberfläche + Boundary + Private-Default-Guard |
| `tests/test_saas_product_model.py` | Absicherung: keine SOMAA/Hadi/AMEX-1005/ai/ep/amex Defaults; Launcher-Import-Grenze |
| dieses Audit | Verbindlicher Roter Faden + nächster Task |

Blank-SaaS-Profil liefert u. a.:

- Profilname `Neues Profil`
- Scanmodell `rechnungen` (generisch)
- leere Konfigurationen
- Review-Ordner `unklar`
- generisches Dateinamensmuster ohne SOMAA-Template
- Editor-Feldvertrag für UI-v2 (Profilname, Scanmodell, Dokumenttyp, Matching, Ziel, Dateiname, Review, Zahlungshinweis)

---

## 4. Bewusst nicht in diesem Commit

- Keine UI-v2-Wiring-Änderungen (Worktree bereits stark dirty an `ui_v2/**`)
- Kein Commit der untracked WIP-Module `configuration_model.py` / `profile_store.py` / `scan_models.py` (separater Integrationsblock)
- Kein Processing-Service (Block B)
- Kein Review-Queue-Ausbau (Block C)
- Kein Onboarding-Wizard (Block D)
- Keine Schema-Migration der CategoryId-Enums

---

## 5. Nächster exakter Task

**Task ID:** `KI_RECHNUNGEN_SAAS_UI_V2_PROFILE_SURFACE_WIRE_GENERIC_MODEL_01`

**Ziel:** UI-v2 Profile-/Konfigurationsseiten an `saas_product_model` anbinden:

1. Create/Edit-Defaults aus `build_blank_saas_profile()` / `blank_saas_profile_as_dict()`
2. Keine Vorbelegung aus `profile_config.example.json` oder aktivem SOMAA-Lokalprofil
3. Rendering-Checks von hartem „SOMAA Profil“-Label entkoppeln
4. Tests: SaaS-Create erzeugt generisches Profil; interne Launcher-Dateien unverändert
5. Optional danach Block B: Processing Service Boundary (dry-run/copy-run, selected profile, keine Produktivpfade)

---

## 6. Risiken

- Großer Dirty-State im Worktree erschwert UI-Commits; Foundation bewusst isoliert.
- Schema/`profile_config.example.json` bleiben tenant-lastig bis zur späteren Generalisierung.
- UI-v2-Verarbeitung fehlt weiterhin — bewusst Block B.
