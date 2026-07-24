# Audit — Track-B Automated Smoke Oracle (2026-07-24)

1. **Task ID:** `KI_RECHNUNGEN_TRACK_B_AUTOMATED_SMOKE_ORACLE_2026-07-24`
2. **HEAD before:** `36e039dce84aefe91b9177996d793a2ea74c85fa`  
   **HEAD after:** *(filled after commit)*
3. **Files changed:**
   - `invoice_tool/ui_v2/automated_smoke_oracle.py` (new)
   - `scripts/dev/track_b_automated_smoke_oracle.py` (new)
   - `tests/test_track_b_automated_smoke_oracle.py` (new)
   - `docs/KI_RECHNUNGEN_TRACK_B_AUTOMATED_SMOKE_ORACLE_2026-07-24.md` (new)
   - `docs/audits/KI_RECHNUNGEN_TRACK_B_AUTOMATED_SMOKE_ORACLE_2026-07-24.md` (new)
4. **Oracle command:**
   ```bash
   KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python \
     scripts/dev/track_b_automated_smoke_oracle.py
   ```
5. **Controlled paths:**
   - input: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/input`
   - output: `/Users/hadi_neu/Desktop/KI-Rechnungen-Test/output`
   - preview reused: `preview-export-track-b-dry-61ff6af993d7-20260723T123451630008Z`
6. **PayPal result:** ok=true; condition `payment_field ist paypal`; target `.../output/geplant/paypal`; idempotent (no duplicate); no business_category
7. **Document verification result:** all 5 PASS (LUMITOP, 1A-Bootshop, Böttcher card, Luxvenum, Böttcher Storno)
8. **Böttcher/AMEX result:** card remains Unklar / not American Express
9. **Missing-payment result:** Luxvenum + Böttcher Storno remain Unklar / missing_payment_field
10. **Storno result:** art=storno verified for `420260091336.pdf`
11. **Finalization preview result:** ready=1 blocked=0 (automated smoke review decision on PayPal item)
12. **Dry-run result:** package under controlled output `finalization-dry-run-*`; `final_write_allowed=false`
13. **Sandbox final-write result:** package under controlled output `sandbox-final-write-*`; `final_write_allowed_for_production=false`; copies only
14. **Hash/original mutation result:** hashes unchanged before/after
15. **Safety result:** no run_once; no production final-write; no real invoice folders; originals unchanged
16. **Tests run/results:**
    - focused: 132 passed (`test_track_b_automated_smoke_oracle`, dev_defaults, smoke_duplicate_repair, sandbox_final_write, track_a_protection)
    - UI-v2/SaaS: 576 passed, 44 skipped
    - `git diff --check`: clean on staged files
17. **No productive processing:** yes
18. **No real invoice folders:** yes
19. **No release tag changes:** yes
20. **Product status after task:** `TRACK_B_AUTOMATED_SMOKE_ORACLE_READY_AND_EXECUTED`
21. **Exact next step:** UI-v2 Review-Oberfläche entschlacken (Debug-Text, Navigation, CTA-Klarheit) — rein UX/manuell; Terminal-Oracle als Regressionsgate behalten.
