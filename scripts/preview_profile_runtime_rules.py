"""Preview Profile Runtime Rules
=================================
Compiles a profile_config into runtime rules and writes the result as JSON,
WITHOUT performing any PDF processing or API calls.

Usage::

    PYTHONPATH=. ./.venv/bin/python scripts/preview_profile_runtime_rules.py \\
        --profile profile_config.example.json \\
        --output /tmp/ki-rechnungen-profile-preview.json

    # Optional: specify a different base rules file
    PYTHONPATH=. ./.venv/bin/python scripts/preview_profile_runtime_rules.py \\
        --profile profile_config.example.json \\
        --rules office_rules.json \\
        --output /tmp/preview.json

This script is safe to run at any time:
- Does NOT modify office_rules.json
- Does NOT modify invoice_config.json
- Does NOT process any PDFs
- Does NOT make OpenAI or OCR calls
- Does NOT create run directories
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/preview_profile_runtime_rules.py",
        description=(
            "Compile a profile_config into runtime rules and write the result "
            "as JSON. No PDFs, no API calls, no run directories created."
        ),
    )
    parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        metavar="FILE",
        help="Path to profile_config.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        metavar="FILE",
        help="Output path for the compiled runtime_rules JSON.",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path to office_rules.json. Defaults to ./office_rules.json.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    profile_path = args.profile.resolve()
    output_path = args.output.resolve()
    rules_path = (args.rules.resolve() if args.rules else Path("office_rules.json").resolve())

    # --- load ---
    if not profile_path.exists():
        print(f"Fehler: Profil-Datei nicht gefunden: {profile_path}", file=sys.stderr)
        return 1
    if not rules_path.exists():
        print(f"Fehler: Regeldatei nicht gefunden: {rules_path}", file=sys.stderr)
        return 1

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Fehler: Profil ist kein gültiges JSON: {exc}", file=sys.stderr)
        return 1

    try:
        base_rules_dict = json.loads(rules_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Fehler: Regeldatei ist kein gültiges JSON: {exc}", file=sys.stderr)
        return 1

    # --- validate ---
    from invoice_tool.profile_compiler import compile_profile_to_rules, validate_profile

    issues = validate_profile(profile)
    if issues:
        print("[preview] Profilvalidierung – Hinweise:")
        for issue in issues:
            print(f"  - {issue}")
        print()

    # --- compile + merge ---
    from invoice_tool.config import merge_rules_dicts

    active_preset = base_rules_dict.get("active_preset", "office_default")
    generated = compile_profile_to_rules(profile, preset_name=active_preset)
    merged = merge_rules_dicts(base_rules_dict, generated)

    # --- build _meta ---
    gen_preset = generated.get("presets", {}).get(active_preset, {})
    gen_routing = gen_preset.get("routing", {})
    generated_sections = [
        f"routing.{section}"
        for section in (
            "strassen", "prioritaetsregeln", "konten",
            "business_context_rules", "payment_detection_rules",
        )
        if section in gen_routing
    ]
    if "classification" in gen_preset:
        generated_sections.append("classification")

    prepended_sections = [
        f"routing.{section}"
        for section in ("payment_detection_rules",)
        if section in gen_routing
    ]

    all_protected = [
        "routing.konten",
        "routing.business_context_rules",
        "routing.final_assignment_rules",
        "routing.output_route_rules",
        "classification",
        "supplier_cleaning",
        "dateiname_schema",
        "invoice_fallbacks",
    ]
    protected_sections = [s for s in all_protected if s not in generated_sections]

    merged["_meta"] = {
        "profile_applied": True,
        "base_rules_source": str(rules_path),
        "profile_source": str(profile_path),
        "generated_sections": generated_sections,
        "prepended_sections": prepended_sections,
        "protected_sections": protected_sections,
        "merge_strategy": "replace_generated_sections_prepend_payment_detection",
        "preview_mode": True,
    }

    # --- write output ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- summary ---
    print()
    print("=" * 50)
    print("PROFILE RUNTIME RULES PREVIEW")
    print("=" * 50)
    print(f"  profile_applied:    True")
    print(f"  profile_source:     {profile_path.name}")
    print(f"  base_rules_source:  {rules_path.name}")
    print(f"  generated_sections: {generated_sections}")
    print(f"  protected_sections: {protected_sections}")
    print(f"  output:             {output_path}")
    print("=" * 50)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
