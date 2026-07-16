# KI_RECHNUNGEN_FIRST_CONTROLLED_REAL_COPY_RUN_AND_LAUNCHER_RESULT_REVIEW_01

**Datum:** 2026-07-16  
**Task ID:** `KI_RECHNUNGEN_FIRST_CONTROLLED_REAL_COPY_RUN_AND_LAUNCHER_RESULT_REVIEW_01`  
**Initial classification:** `READY_WITH_PREEXISTING_REPOSITORY_LIMITATIONS`  
**Final classification:** `CONTROLLED_LAUNCHER_COPY_RUN_PASS_WITH_NOTES`

Evidence: `docs/audits/evidence/ki-rechnungen-first-controlled-real-copy-run-launcher-result-review-2026-07-16/`

---

## 1. Preflight

| Feld | Wert |
|---|---|
| pwd (Start) | `/Users/hadi_neu/Desktop/Programm Belegerfassung` |
| Repository root | `/Users/hadi_neu/Desktop/Programm Belegerfassung/KI-Rechnungen-App` |
| Branch | `main` |
| HEAD | `6399cb82c5e2dc062691128f232e90df6567146e` |
| Upstream | `origin/main` |
| Ahead/Behind | ahead 2 / behind 0 |
| Dirty-State | ja (vorbestehend; viele tracked + untracked) |
| Aktive Git-Operation | nein (`MERGE_HEAD` fehlt) |
| `.git/AUTO_MERGE` | vorhanden (stale, Inhalt `3373496a…`), kein Merge aktiv |
| Git lock | nein |
| Python `.venv` | 3.9.6 |
| Python `.venv-flet085` | 3.12.13 |
| Profilpfad | `$HOME/Library/Application Support/KI-Rechnungen/profile_config.local.json` |
| Profilhash (SHA-256) | `9ff8e3bdbe7265bcbe798c275f37b20b7c6336a8456ec2b3220b7888399dff16` |
| Profilcompiler | `validate_profile=[]`, `compile_profile_to_rules` OK |
| Scan-Modell | `rechnungen` |
| Recipient Guard | vorhanden (`invoice_tool/recipient_guard.py` + Profil `recipient_policy`) |
| Anthropic-Regel | vorhanden (`anthropic-ep-amex-1005`) |
| Amazon-Regel | vorhanden (`amazon-ai-amex`) |
| Same-run-Duplicate-Lifecycle | vorhanden (`file_lifecycle` + Lauf bestätigt) |
| Launcher-Script | `scripts/run_internal_launcher_flet085.sh` |
| Launcher-App | `app_internal_launcher.py` / `invoice_tool/internal_launcher/` |
| Hash `app_ui_v2.py` | `363768353192b718ef03df54349a172cf3214f8735477f289a388f6255fccbd5` |
| Hash Launcher-Script | `25694b24613663efbbc191d0499bafa00f9c0f186b7ac0c1ea92c561980d5fac` |
| Reale Dateien vor Lauf | 265 (ohne `.DS_Store`) |
| Sicher ohne Produktivordneränderung | ja |

**Initial classification Begründung:** Worktree korrekt, Profil OK, Launcher lauffähig, Fixtures vorhanden; Dirty-State + stale `AUTO_MERGE` + ahead-2 sind vorbestehende Repository-Limitationen, kein Ausführungsblocker.

---

## 2. Testroot und Input-Kopie

**Testroot:**  
`/Users/hadi_neu/Desktop/Programm Belegerfassung/20_SOMAA_Rechnungstest/Controlled_Launcher_Run_20260716_102853/`

**Input-Quelle (read-only):**  
`/Users/hadi_neu/Desktop/RECHNUNGEN/260714_Zu Verarbeiten Kopie`

| Check | Ergebnis |
|---|---|
| Input-Dateien vorher | 50 (48 PDF, 2 XLSX) |
| Amazon vorhanden | ja (`amazon1.pdf` …) |
| Anthropic vorhanden | ja (`Invoice-MQYKKQPM-0003.pdf`) |
| Martin-Kohnle-Referenz | ja (`RE26084_1.pdf`) |
| RE0072-Dublette | ja, byte-identisch (`6952951d…`) |
| XLSX | ja (2 AMEX-Abrechnungs-XLSX) |

Inventar: `evidence/.../input_copy_inventory.tsv`

---

## 3. Launcher-Prüfung

| Punkt | Ergebnis |
|---|---|
| Launcher startet | ja (Smoke ~4s, Prozess lief, dann beendet) |
| Crash beim Start | nein |
| Source-/Output-Picker (Code) | vorhanden (`FilePicker`/Directory-Picker, Source/Output, Start, Progress, Ergebnis öffnen, Profilanzeige) |
| GUI-Automation End-to-End | nicht durchgeführt (macOS Accessibility / Agent-GUI-Grenze) |
| CLI-Fallback | genutzt; identisch zu `RunController.build_command` |

**Hinweis:** Fachlicher Lauf über denselben CLI-Pfad, den der Launcher subprocess ausführt.

---

## 4. Kontrollierter Lauf

**Modus:** CLI-Fallback (Launcher-äquivalent)

```bash
.venv-flet085/bin/python -m invoice_tool.run \
  --source ".../Controlled_Launcher_Run_20260716_102853/01_Input_Copy" \
  --output ".../Controlled_Launcher_Run_20260716_102853/02_Output" \
  --profile "$HOME/Library/Application Support/KI-Rechnungen/profile_config.local.json"
```

| Feld | Wert |
|---|---|
| Exit-Code | `0` |
| Start | 2026-07-16T10:29:28+02:00 |
| Ende | 2026-07-16T10:33:56+02:00 |
| Laufzeit | ≈ 268 s |
| Run-ID | `20260716_102928` |
| Technischer Run-Ordner | `$HOME/Library/Application Support/KI-Rechnungen/runs/20260716_102928` |

---

## 5. Postrun-Inventar

| Metrik | Wert |
|---|---|
| Verarbeitete PDFs | 48 |
| Ausgaben (PDF/Docs) | 47 fachliche Outputs + 1 Duplicate-Report-Datei |
| Output nach Ordner | ai 16, amex 25, documents 2, private 2, unklar 2, `_duplicate_reports` 1 |
| Archiviert unter `archiv/20260716_102928/` | 48 (inkl. 1 unter `duplikate/`) |
| Dubletten | 1 |
| Direkte Input-PDFs nach Lauf | 0 |
| Direkte Input-XLSX nach Lauf | 2 (unverändert liegen geblieben) |
| Direkte Input-Dateien nach Lauf | nur die 2 XLSX |

---

## 6. Fachliche Zielergebnisse

### A. Amazon (`amazon1.pdf` und weitere Amazon-Kopien)

- Ordner: `amex`
- art: `ai`
- payment: `amex` (keine Kartenendung)
- nicht `vobaai`
- Beispiel: `amex/260527_er_ai_amazon-eu-s-a-r-l-nied_40.55_amex.pdf`
- Regel: `amazon-ai-amex` (supplier/issuer)

### B. Anthropic (`Invoice-MQYKKQPM-0003.pdf`)

- Ordner: `amex`
- art: `ep`
- payment: `amex-1005`
- Datei: `amex/260623_er_ep_anthropic-pbc_90.00_amex-1005.pdf`
- **Hinweis:** Zusätzliche Quelle `Receipt-2146-4098-2697.pdf` (ebenfalls Anthropic) → zweite Ausgabe `…amex-1005__2.pdf` (Collision-Rename). Keine parallele EP-Ordner-Ausgabe; Invoice selbst genau eine Ausgabe.

### C. Martin Kohnle (`RE26084_1.pdf`)

- Ordner: `unklar`
- art: `unklar` (nicht private)
- Recipient-Guard: fremder Empfänger
- Datei: `unklar/260621_er_unklar_martin-kohnle_3172.31_unklar.pdf`

### D. RE0072-Dublette

- Genau eine fachliche Ausgabe: `ai/260629_er_ai_superpunkt-kalashn_1997.71_vobaai.pdf`
- Primärquelle archiviert unter `archiv/20260716_102928/Rechnung_RE0072.pdf`
- Dublette unter `archiv/20260716_102928/duplikate/Rechnung_RE0072_29.06.2026.pdf`
- Keine RE0072-PDF mehr direkt im Input
- Duplicate-Report: `02_Output/_duplicate_reports/Rechnung_RE0072_29.06.2026.txt`

### E. Weitere Routing-Beobachtungen

- AI-/Bankbelege überwiegend unter `ai` mit `vobaai`
- AMEX-Monatsabrechnung / Apple / Adobe / Cursor gemäß Profil unter `amex` (teilweise `art=private` durch exclusive Vendor-Regeln)
- EasyPark-Beleg → `ai`/`vobaai` (gemäß erkannten Zahlungswegen, nicht zwingend Ordner `ep`)
- Fremdempfänger (Bootshop) → `unklar`

### F. XLSX

- Beide XLSX blieben direkt in `01_Input_Copy` liegen
- Nicht gelöscht, nicht ins Archiv verschoben

---

## 7. DATEV-Bytevergleich

Mindestens 8 Paare geprüft (siehe `byte_compare.json`):

| Label | Classification |
|---|---|
| Amazon | `OUTPUT_BYTE_IDENTICAL` |
| Anthropic | `OUTPUT_BYTE_IDENTICAL` |
| RE0072 | `OUTPUT_BYTE_IDENTICAL` |
| Martin Kohnle | `OUTPUT_BYTE_IDENTICAL` |
| AMEX | `OUTPUT_BYTE_IDENTICAL` |
| EasyPark | `OUTPUT_BYTE_IDENTICAL` |
| Cursor AI | `OUTPUT_BYTE_IDENTICAL` |
| unklar Bootshop | `OUTPUT_BYTE_IDENTICAL` |
| RE0072 Duplikat-Archiv vs. Ausgabe | byte-identisch (kein zweiter Output) |

Keine DATEV-Korrektur implementiert. Keine pauschale Metadaten-/Datumskorrektur.

---

## 8. Reale RECHNUNGEN-Integrität

| | Vorher | Nachher |
|---|---|---|
| Dateianzahl (ohne `.DS_Store`) | 265 | 265 |
| SHA-256-Inventar | identisch | identisch |

`REAL_INTEGRITY_OK` — keine neuen/gelöschten/geänderten Dateien unter `/Users/hadi_neu/Desktop/RECHNUNGEN`.

---

## 9. Tests

Fokussiert mit `.venv/bin/python -m pytest`:

- `tests/test_amazon_supplier_rule.py`
- `tests/test_recipient_duplicate_anthropic_fix.py`
- `tests/test_file_lifecycle.py`

**Ergebnis:** 34 passed, 0 failed.  
Unrelated Full-Suite nicht ausgeführt.

Profilcompiler post-run: OK.

---

## 10. Integrität Code/UI/Launcher

| Check | Ergebnis |
|---|---|
| `app_ui_v2.py` Hash unverändert | ja |
| Launcher-Script Hash unverändert | ja |
| UI-v2 App/Shell Hashes unverändert | ja |
| OCR/AI-Provider geändert | nein |
| Profil geändert | nein (nur gelesen) |
| Commit | nein |
| Push | nein |

---

## 11. Hinweise (PASS_WITH_NOTES)

1. GUI-End-to-End-Lauf nicht automatisiert; CLI-Fallback mit launcher-identischen Parametern.
2. Zweite Anthropic-Quelle (Receipt) erzeugt Collision-Rename `__2` — fachlich erwartbar bei zwei Anthropic-PDFs mit gleichem Zielnamen.
3. Vorbestehender Dirty-State / stale `AUTO_MERGE` / ahead-2 unverändert; nicht Gegenstand dieses Tasks.

---

## 12. Nächster Task (nicht ausgeführt)

`KI_RECHNUNGEN_COMMIT_PREPARATION_AND_DIRTY_STATE_REVIEW_01`

- Dirty-State sortieren
- vorbestehende vs. neue Änderungen trennen
- stale AUTO_MERGE prüfen
- ahead-2 erklären
- sichere Commit-Gruppen vorschlagen
- nichts verwerfen, nicht pushen ohne Freigabe

---

## 13. Empfehlung Produktiveinsatz

**Noch nicht als blinden Produktivlauf freigeben.**  
Kontrollierter Kopienlauf fachlich bestanden; vor Produktiv: Commit-Vorbereitung/Dirty-State-Review und bewusste manuelle Launcher-Bedienung mit echten Ordnern nach PO-Freigabe.
