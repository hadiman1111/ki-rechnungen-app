# KI-Rechnungen — General UI-v2 PO Confirmation Finalize

## 1. Task ID

`KI_RECHNUNGEN_GENERAL_UI_V2_PO_CONFIRMATION_FINALIZE_RETRY_01`

## 2. Date

`2026-07-21`

## 3. Previous technical result

`GENERAL_UI_V2_VISUAL_PARTIAL`

## 4. Technical start path

```text
.venv-flet085/bin/python app_ui_v2.py
```

## 5. Confirmed UI path

`app_ui_v2.py` → `invoice_tool.ui_v2.app.build_ui_v2`

## 6. Confirmed track

Track B / general product UI / UI-v2

## 7. Product Owner visual confirmation

> Jetzt hat es die richtige arbeitsoberfläche angezeigt

Meaning: The opened `app_ui_v2.py` window is the correct newest designed general product UI.

## 8. Final upgraded classification

`GENERAL_UI_V2_VISUAL_CONFIRMED`

## 9. Track separation

- `app_main.py` = Track A internal local app / package path
- `app_ui_v2.py` = Track B newest general product UI

## 10. Clarification

- `app_main.py` intentionally opens Track A and is not the newest general UI.
- `app_ui_v2.py` is the correct entrypoint for the latest general UI.

## 11. Safety confirmations

- no productive processing
- no real invoice changes
- no PDF processing
- no code changes
- no build
- known Legacy-UI dirty files remain local and uncommitted:
  - `invoice_tool/ui_profile_dialog.py` (modified, unstaged)
  - `invoice_tool/ui_document_rules.py` (untracked, unstaged)

## 12. Next decision

- continue Track B UI-v2 product development
- only run Track A macOS build smoke if explicitly desired separately

## 13. Retry note

Previous task `KI_RECHNUNGEN_GENERAL_UI_V2_PO_CONFIRMATION_FINALIZE_01` was blocked because known Legacy-UI dirty files were incorrectly classified as processing-core dirty. This retry applies the Legacy-UI allowlist and documents the PO confirmation without staging or committing those files.
