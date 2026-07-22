# KI-Rechnungen Track B UI-v2 — Profile Policy Completion

**Task ID:** `KI_RECHNUNGEN_TRACK_B_UI_V2_PROFILE_POLICY_COMPLETION_01`  
**Date:** 2026-07-21  
**Workstream:** KI-Rechnungen-App / Belegerfassung / Track B / General Product UI-v2 / Profile and Policy Completion  
**Masterplan position:** Prompt 4 of 12 bis Produktversion 1 / lokale Pilotfähigkeit

## 1. Task ID

`KI_RECHNUNGEN_TRACK_B_UI_V2_PROFILE_POLICY_COMPLETION_01`

## 2. Masterplan position: Prompt 4 of 12

Dieses Task vervollständigt die Track-B UI-v2 Profil- und Policy-Konfigurationsschicht,
damit die allgemeine Produkt-UI nutzer-/profilspezifische Regeln ohne hardcodierte
private Daten darstellen kann — ohne produktive Ausführung und ohne Processing-Core.

## 3. Purpose

1. Generische Profilidentität darstellen  
2. Profilkonfigurierbare Geschäfts-/Zahlungs-/Kontonachweise modellieren  
3. Policy-Regeln für unklare Nachweise ehrlich zeigen  
4. Dateiname ist nie Wahrheitsquelle  
5. Lieferanten-IBAN allein ist kein Zahlernachweis  
6. Generischer Kartentext ohne konfigurierte Referenz bleibt zur Prüfung  
7. Verbindung Profil ↔ Konfiguration ↔ Policy-Intent  
8. Keine privaten Defaults, keine produktive Ausführung, kein PDF-Processing  

## 4. What changed

Neu:

- `invoice_tool/ui_v2/profile_policy.py` — reine View-Model-/Readiness-Helfer  
- `tests/test_ui_v2_profile_policy.py`  
- `tests/test_ui_v2_profiles_page.py`  
- `tests/test_ui_v2_configurations_page.py`  
- dieses Audit-Dokument  

Aktualisiert:

- `invoice_tool/ui_v2/pages/profiles.py` — Profil-Policy-Readiness-Panel + Copy  
- `invoice_tool/ui_v2/pages/configurations.py` — Konfiguration↔Policy-Panel + Copy  
- `invoice_tool/ui_v2/policy_editor_controls.py` — Pflicht-Copy und Kernregeln  
- `tests/test_ui_v2_policy_editor_controls.py` — zusätzliche Regel-Tests  

## 5. Profile policy model/view model behavior

Modul: `profile_policy.py`

- `ProfilePolicyIdentity`, `BusinessEvidenceRule`, `PaymentEvidenceRule`,
  `AccountEvidenceRule`, `ProfilePolicyViewModel`  
- `build_profile_policy_view_model(...)` / `blank_profile_policy_view_model()`  
- `validate_profile_policy_readiness(...)`  
- Fehlende Nachweise → Readiness `review` / unklar, keine Fake-Sicherheit  
- Defaults leer/generisch; keine privaten Tenant-Werte  
- `align_profile_policy_with_runtime_intent(...)` nutzt den bestehenden Bridge  

## 6. Profiles page behavior

- Zeigt generische Profil-Policy-Copy (Pflichttexte)  
- Zeigt selected-profile Readiness  
- Leerer Zustand ohne privates Standardprofil  
- Geschäfts-/Zahlungs-/Kontoregeln als profilspezifisch gekennzeichnet  
- Keine produktive Ausführung  

## 7. Configurations page behavior

- Zeigt Konfigurationen als generische Routing-/Verarbeitungs-Setups  
- Zeigt Beziehung zu aktivem Profil / Policy-Readiness  
- Unklar-/Nicht-zugeordnet-Konzept ehrlich  
- Keine privaten Zielpfad-Defaults, kein Ordner-Scan, kein PDF-Processing  

## 8. Policy editor controls behavior

Kernregeln sichtbar:

- Dateinamen sind keine Belegwahrheit  
- Unklare Nachweise bleiben zur Prüfung  
- Lieferanten-IBAN ist kein Zahlungsnachweis des Nutzers  
- Kartenhinweise ohne konfigurierte Referenz bleiben unklar  
- Profilspezifische Regeln treiben Entscheidungen  

Controls bleiben Readiness-only / disabled; kein produktiver Toggle.

## 9. RuntimePolicyIntent alignment

- Bridge bleibt generisch (`policy_runtime_bridge.py` unverändert im Kernverhalten)  
- Alignment-Helfer leitet `RuntimePolicyBridgeResult` ab  
- Fehlende Policy → `incomplete`  
- Filename nie SOT; Supplier-IBAN kein Payer; generische Karte → `unklar`  

## 10. Why this does not process real PDFs

- Keine Processing-Core-Imports in den neuen/geänderten UI-v2-Modulen  
- Keine OCR/AI-Aufrufe  
- Keine PDF-IO; nur View-Models und Readiness-Copy  

## 11. Why this does not touch real invoice folders

- Kein Folder-Scan / Folder-Create  
- Keine Pfad-Defaults (`Desktop`, `/Users`, private Tokens)  
- Zielorte erst nach sicherer Konfiguration (Copy/Readiness)  

## 12. Why this does not touch Track A

Nicht geändert / nicht staged:

- `app_main.py`, `app_internal_launcher.py`  
- `invoice_tool/gui.py`, `ui_shell.py`, `ui_workspace.py`, Legacy-UI-Module  

## 13. Why this does not touch processing-core

Nicht geändert:

- `invoice_tool/processing.py`  
- `invoice_tool/routing.py` / `routing_guards.py`  
- `invoice_tool/classification.py`  
- `invoice_tool/target_routing.py`  
- `invoice_tool/run.py`  

## 14. Tests added/updated

Neu:

- `tests/test_ui_v2_profile_policy.py`  
- `tests/test_ui_v2_profiles_page.py`  
- `tests/test_ui_v2_configurations_page.py`  

Aktualisiert:

- `tests/test_ui_v2_policy_editor_controls.py`  

## 15. Tests run and results

```text
.venv/bin/python -m pytest \
  tests/test_ui_v2_policy_editor_controls.py \
  tests/test_ui_v2_policy_runtime_bridge.py \
  tests/test_ui_v2_workspace_processing_contract.py \
  tests/test_ui_v2_review_workflow.py \
  tests/test_ui_v2_profile_policy.py \
  tests/test_ui_v2_profiles_page.py \
  tests/test_ui_v2_configurations_page.py
→ 86 passed

.venv/bin/python -m pytest tests/test_ui_v2_*.py tests/test_saas_ui_v2_*.py
→ 313 passed, 44 skipped
```

## 16. Generalization confirmation

- keine Hadi/SOMAA/Bismarck/AMEX/voba Defaults  
- keine Desktop/`/Users`-Pfad-Defaults  
- Dateiname keine Belegwahrheit  
- keine Fake-Zahlungs-/Konto-/Business-Klassifikation  
- keine Fake-Review-Items / Fake-Processing-Results  
- kein produktiver Ausführungs-Toggle  
- kein Ordner-Scan / keine Ordner-Erzeugung / kein PDF-Processing  
- Track A und Processing-Core unberührt  

## 17. Current progress

- Prompt 4/12 complete: **yes**  
- Remaining prompts: **8**  

## 18. Remaining gaps

- export/reporting completion  
- Track A regression gate  
- synthetic E2E  
- copied-real-data validation  
- quality fixes  
- packaging/onboarding  
- pilot acceptance  
- final release gate  

## 19. Exact next task recommendation

`KI_RECHNUNGEN_TRACK_B_UI_V2_EXPORT_REPORTING_COMPLETION_01`  
(Prompt 5/12 — Export/Reporting Completion für Track-B UI-v2, ohne produktive Ausführung)
