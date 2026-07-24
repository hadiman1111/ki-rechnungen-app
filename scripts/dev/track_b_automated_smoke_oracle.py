#!/usr/bin/env python3
"""Dev-only Track-B automated smoke oracle runner.

Usage:
  KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS=1 .venv/bin/python \\
    scripts/dev/track_b_automated_smoke_oracle.py

Never calls run_once / productive processing. Controlled folders only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("KI_RECHNUNGEN_UI_V2_DEV_DEFAULTS", "1")

from invoice_tool.ui_v2.automated_smoke_oracle import (  # noqa: E402
    ORACLE_PROFILE_ID,
    run_track_b_automated_smoke_oracle,
)
from invoice_tool.ui_v2.dev_defaults import (  # noqa: E402
    CONTROLLED_TEST_ROOT,
    TRACK_B_DEV_INPUT_DEFAULT,
    TRACK_B_DEV_OUTPUT_DEFAULT,
)


def main() -> int:
    print("=== Track-B Automated Smoke Oracle ===")
    print(f"repo: {ROOT}")
    print(f"input: {TRACK_B_DEV_INPUT_DEFAULT}")
    print(f"output: {TRACK_B_DEV_OUTPUT_DEFAULT}")
    print(f"controlled_root: {CONTROLLED_TEST_ROOT}")

    storage = TRACK_B_DEV_OUTPUT_DEFAULT / "automated-smoke-profile-store"
    storage.mkdir(parents=True, exist_ok=True)

    result = run_track_b_automated_smoke_oracle(
        repo_root=ROOT,
        input_root=TRACK_B_DEV_INPUT_DEFAULT,
        output_root=TRACK_B_DEV_OUTPUT_DEFAULT,
        profile_id=ORACLE_PROFILE_ID,
        profile_storage_dir=storage,
        skip_git_preflight_stop=False,
        create_folders_if_missing=True,
    )

    print(f"evidence: {result.evidence_folder}")
    print(f"preview_export: {result.preview_export_folder}")
    print(f"paypal_ok: {result.paypal_result.get('ok')}")
    print(
        "documents: "
        + ", ".join(
            f"{d.source_filename}={'PASS' if d.ok else 'FAIL'}"
            for d in result.document_results
        )
    )
    print(
        "finalization: ready="
        f"{result.finalization_preview.get('ready_count')} "
        f"blocked={result.finalization_preview.get('blocked_count')}"
    )
    print(f"dry_run: {result.dry_run.get('package_root')}")
    print(f"sandbox_final_write: {result.sandbox_final_write.get('sandbox_final_write_root')}")
    print(f"hashes_unchanged: {result.hashes_before == result.hashes_after}")
    if result.blockers:
        print("blockers:")
        for item in result.blockers:
            print(f"  - {item}")
    # Exact final status line required by the task contract.
    print(result.status)
    if result.status.endswith("FAIL_UNSAFE"):
        return 2
    if result.status.endswith("BLOCKED") and not result.status.startswith(
        "TRACK_B_AUTOMATED_SMOKE_ORACLE_PARTIAL"
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
