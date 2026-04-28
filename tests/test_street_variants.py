"""Tests für invoice_tool/street_variants.py.

Prüft alle geforderten Varianten, Hausnummern-Logik, advanced_variants,
Deduplizierung, stabile Sortierung und ValueError bei leerer Eingabe.
"""
from __future__ import annotations

import pytest

from invoice_tool.street_variants import generate_street_variants


# ---------------------------------------------------------------------------
# A. Rötestraße – Mindest-Variantensatz
# ---------------------------------------------------------------------------


def test_generate_roete_street_variants() -> None:
    """Prüft, dass für street='Rötestraße' alle erwarteten Varianten enthalten sind."""
    variants = generate_street_variants("Rötestraße")

    expected = [
        "rötestraße",
        "roetestrasse",
        "rötestrasse",
        "roete strasse",
        "röte strasse",
        "roete-strasse",
        "röte-strasse",
        "roetestr.",
        "rötestr.",
        "roetestr",
        "rötestr",
    ]
    for form in expected:
        assert form in variants, (
            f"Erwartete Variante {form!r} fehlt. Vorhanden: {variants}"
        )


# ---------------------------------------------------------------------------
# B. Rötestraße mit Hausnummer
# ---------------------------------------------------------------------------


def test_generate_roete_variants_with_house_number() -> None:
    """Varianten ohne Hausnummer bleiben erhalten; mit Hausnummer kommen dazu."""
    variants_no_hn = generate_street_variants("Rötestraße")
    variants_with_hn = generate_street_variants("Rötestraße", house_number="58")

    # Alle Varianten ohne Hausnummer müssen enthalten bleiben
    for v in variants_no_hn:
        assert v in variants_with_hn, (
            f"Variante ohne Hausnummer {v!r} fehlt in der Hausnummern-Liste."
        )

    # Zusätzliche Varianten mit Hausnummer müssen vorhanden sein
    assert "rötestr. 58" in variants_with_hn, (
        "Variante 'rötestr. 58' fehlt."
    )
    assert "roetestrasse 58" in variants_with_hn, (
        "Variante 'roetestrasse 58' fehlt."
    )
    assert "rötestrasse 58" in variants_with_hn, (
        "Variante 'rötestrasse 58' fehlt."
    )
    assert "roetestr. 58" in variants_with_hn, (
        "Variante 'roetestr. 58' fehlt."
    )

    # Die Hausnummern-Liste muss länger sein als die ohne
    assert len(variants_with_hn) > len(variants_no_hn)


# ---------------------------------------------------------------------------
# C. Bismarckstraße – Mindest-Variantensatz
# ---------------------------------------------------------------------------


def test_generate_bismarck_street_variants() -> None:
    """Prüft alle erwarteten Varianten für street='Bismarckstraße'."""
    variants = generate_street_variants("Bismarckstraße")

    expected = [
        "bismarckstraße",
        "bismarckstrasse",
        "bismarck strasse",
        "bismarck-strasse",
        "bismarckstr.",
        "bismarck str.",
        "bismarckstr",
        "bismarck str",
    ]
    for form in expected:
        assert form in variants, (
            f"Erwartete Variante {form!r} fehlt. Vorhanden: {variants}"
        )


# ---------------------------------------------------------------------------
# D. Deduplizierung und stabile Sortierung
# ---------------------------------------------------------------------------


def test_street_variants_are_deduplicated_and_stable() -> None:
    """Keine Duplikate; zwei Aufrufe mit gleicher Eingabe liefern exakt dieselbe Liste."""
    for street in ["Rötestraße", "Bismarckstraße", "Hauptweg"]:
        first = generate_street_variants(street)
        second = generate_street_variants(street)

        assert first == second, (
            f"Zwei Aufrufe für {street!r} liefern unterschiedliche Ergebnisse."
        )
        assert len(first) == len(set(first)), (
            f"Duplikate in Varianten für {street!r}: {first}"
        )
        assert first == sorted(first), (
            f"Varianten für {street!r} sind nicht sortiert: {first}"
        )


# ---------------------------------------------------------------------------
# E. advanced_variants
# ---------------------------------------------------------------------------


def test_advanced_variants_are_included_and_deduplicated() -> None:
    """advanced_variants werden aufgenommen, getrimmt, lowercase und dedupliziert."""
    base_variants = generate_street_variants("Rötestraße")

    advanced = [
        "  Röte Str  ",      # Leerzeichen + Großschreibung → getrimmt + lowercase
        "ROETESTR",          # Großschreibung → lowercase
        "roetestr",          # Duplikat (schon in base_variants)
        "",                  # Leerstring → ignorieren
        "   ",              # Nur Whitespace → ignorieren
        "custom-variante",   # Neu
    ]
    result = generate_street_variants("Rötestraße", advanced_variants=advanced)

    # Alle Basis-Varianten müssen enthalten sein
    for v in base_variants:
        assert v in result, f"Basis-Variante {v!r} fehlt nach Hinzufügen von advanced_variants."

    # Sinnvolle advanced_variants müssen enthalten sein
    assert "röte str" in result, "'röte str' aus '  Röte Str  ' fehlt."
    assert "roetestr" in result, "'roetestr' fehlt."
    assert "custom-variante" in result, "'custom-variante' fehlt."

    # Keine Duplikate trotz doppeltem "roetestr"
    assert len(result) == len(set(result)), "Duplikate in result nach advanced_variants."

    # Leere Einträge dürfen nicht in der Liste auftauchen
    assert "" not in result
    assert "   " not in result


# ---------------------------------------------------------------------------
# F. ValueError bei leerer Eingabe
# ---------------------------------------------------------------------------


def test_empty_street_raises_value_error() -> None:
    """Leerer String oder nur Whitespace soll ValueError werfen."""
    with pytest.raises(ValueError):
        generate_street_variants("")

    with pytest.raises(ValueError):
        generate_street_variants("   ")


# ---------------------------------------------------------------------------
# Zusatz: Alle Varianten sind lowercase
# ---------------------------------------------------------------------------


def test_all_variants_are_lowercase() -> None:
    for street in ["Rötestraße", "Bismarckstraße", "Hauptweg"]:
        for v in generate_street_variants(street):
            assert v == v.lower(), (
                f"Variante {v!r} für {street!r} ist nicht lowercase."
            )
