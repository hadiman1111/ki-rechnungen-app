# Track-B UI-v2 Information Architecture Cleanup (2026-07-24)

## Purpose

Restructure UI-v2 so the primary navigation and page layouts follow the real user workflow:

**Profil → Konfiguration → Eingang/Ausgang → Vorschau prüfen → Zur Prüfung → Ergebnis**

Internal/dev artifacts (Pilotstatus, Sandbox-Wording, Import/Export, Policy/Readiness) are de-emphasized.

## Product-owner UX findings (addressed)

- Navigation did not match the user workflow (Konfigurationen before Profile; Einstellungen felt primary).
- Arbeitsbereich mixed Pilot/Sandbox/Testordner/Exportvorschau into the primary setup.
- Profile/Konfigurationen opened with confusing draft/policy boxes.
- Review filenames showed internal `REVIEW_REQUIRED` / `SUGGESTED` prefixes.
- Settings looked like a core workflow step.

## New workflow order

Primary nav:

1. Arbeitsbereich  
2. Profile  
3. Konfigurationen  
4. Zur Prüfung  

Secondary / advanced:

- Erweiterte Einstellungen (group: ERWEITERT)

## Workspace cleanup

Primary order:

1. Profil card (`Profil ändern` → Profile)  
2. Konfiguration card (`Konfigurationen bearbeiten` → Konfigurationen)  
3. Eingangs-/Ausgangsordner (checkmarks, distinct colors, activity while running)  
4. Run: **Belege prüfen — nur Vorschau** + helper that originals stay unchanged  
5. Compact result summary with **Zur Prüfung öffnen**

Moved under Entwickler / Diagnose or Test & Nachweis:

- Pilotstatus / Pilot-Details  
- Kontrollierte Testordner erstellen  
- Exportvorschau as primary setup  

## Profile cleanup

- Page explains what a profile is.  
- Active profile summary at top.  
- Create uses **Profil erstellen** / **Name des neuen Profils**.  
- Policy/readiness under **Erweiterte Profilinformationen**.  
- Draft wording rewritten away from “lokaler UI-v2 Profil Entwurf”.  

## Configuration cleanup

- Top summary: active profile, counts, missing targets if actionable.  
- **Neue Konfiguration** remains clickable.  
- Create/save labels: **Konfiguration erstellen** / **Konfiguration speichern**.  
- Edit form near top when editing; no internal side scrollbar.  
- Target paths use smart truncation (preserve end) + full path row.  
- Hint/policy/import-export collapsed as advanced.  

## Review clarification mode

- User-facing proposed filename stripped of `REVIEW_REQUIRED` / `SUGGESTED`.  
- Status shown separately: `Zur Prüfung · Vorschlag · Nicht final geschrieben`.  
- Schema note: fixed filename schema; free-form edit secondary.  
- Plain guidance for missing payment / card-AMEX / PayPal / Storno.  

## Settings de-emphasis

- Nav label: **Erweiterte Einstellungen** under ERWEITERT.  
- Page title matches.  
- Dev/pilot notes collapsed under Entwickler / Diagnose.  

## Clean user filenames / status separation

Display helper `clean_user_facing_filename()` removes internal prefixes (including single-underscore variants). Status line is separate from the filename text.

## Full/smart path display

`display_path_value` and `smart_path_display` truncate the beginning and keep the path end.

## Run activity indication

While a run is active, folder cards show a small ProgressRing and “Prüfung läuft…”.

## Pilot/Sandbox wording

Primary CTA and workspace status use Vorschau/Prüfung wording. Sandbox/Pilot copy remains only in advanced/dev areas or technical modules.

## Safety guarantees

- No productive processing  
- No `run_once`  
- No real invoice folders  
- No production final-write  
- Track A / processing-core / release tags unchanged  
- Terminal oracle still passes  

## Tests

- `tests/test_track_b_ui_v2_information_architecture_cleanup.py`  
- `tests/test_track_b_review_clarification_mode.py`  
- Prior Track-B review/oracle/protection suites  
- `tests/test_ui_v2_*.py` / `tests/test_saas_ui_v2_*.py`  

## What remains

- Full rule-learning from review clarification is not implemented.  
- Payment-type picker UI for clarification is prepared via guidance copy only.  
- Productive final-write remains disabled.  
