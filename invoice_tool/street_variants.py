"""Street Variant Generator
==========================
Erzeugt eine deduplizierte, stabile Liste von Matching-Varianten aus einem
kanonischen deutschen Straßennamen (z. B. „Rötestraße 58").

Varianten enthalten:
- Originalschreibung mit Umlauten (ö, ü, ä, ß)
- Expandierte Form ohne Umlaute (ö→oe, ü→ue, ä→ae, ß→ss)
- Zusammengezogen, durch Leerzeichen oder Bindestrich getrennt
- Vollbezeichnung (straße/strasse) und Abkürzungen (str., str)
- Optionale Hausnummern-Varianten
- Optionale benutzerdefinierte Varianten (advanced_variants)

Design: Isoliertes Modul ohne Seiteneffekte auf routing.py / matching.py /
office_rules.json. Gedacht als Grundlage für einen späteren Profile Compiler
und die UI-Adresseingabe.
"""
from __future__ import annotations

# Suffixe in absteigender Länge, damit längere Matches zuerst geprüft werden
# (z. B. "strasse" vor "str", "straße" vor "str").
_STRASSEN_SUFFIXE: list[str] = sorted(
    [
        "straße",
        "strasse",
        "allee",
        "gasse",
        "platz",
        "damm",
        "pfad",
        "ring",
        "str.",
        "weg",
        "str",
    ],
    key=len,
    reverse=True,
)

# Alle vier Schreibweisen des "Straße"-Typs liefern dieselben Varianten.
_STRASSE_TYPES: frozenset[str] = frozenset({"straße", "strasse", "str.", "str"})


def _expand_umlauts(s: str) -> str:
    """Expandiert deutsche Umlaute: ä→ae, ö→oe, ü→ue, ß→ss."""
    for src, dst in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]:
        s = s.replace(src, dst)
    return s


def _split_street_suffix(street: str) -> tuple[str, str]:
    """Zerlegt einen kanonischen Straßennamen in (Basis, Suffix-Typ).

    Beispiele:
        „Rötestraße"     → („Röte", „straße")
        „Bismarckstraße" → („Bismarck", „straße")
        „Rötestr."       → („Röte", „str.")
        „Hauptweg"       → („Haupt", „weg")
        „Unknown"        → („Unknown", „")
    """
    stripped = street.strip()
    lower = stripped.lower()
    for suffix in _STRASSEN_SUFFIXE:
        if lower.endswith(suffix):
            base = stripped[: len(stripped) - len(suffix)].rstrip(" -")
            return base, suffix
    return stripped, ""


def _base_variants(base: str) -> list[str]:
    """Gibt [Umlaut-Form, expandierte Form] zurück (dedupliziert).

    Für Basen ohne Umlaute (z. B. „Bismarck") enthält die Liste nur einen
    Eintrag. Für Basen mit Umlauten (z. B. „Röte") enthält sie zwei:
    „röte" und „roete".
    """
    umlaut_form = base.lower()
    expanded_form = _expand_umlauts(umlaut_form)
    if umlaut_form == expanded_form:
        return [umlaut_form]
    return [umlaut_form, expanded_form]


def generate_street_variants(
    street: str,
    house_number: str | None = None,
    advanced_variants: list[str] | None = None,
) -> list[str]:
    """Erzeugt eine sortierte, deduplizierte Liste von Matching-Varianten.

    Args:
        street: Kanonischer Straßenname, z. B. „Rötestraße" oder
                „Bismarckstraße". Hausnummer muss separat übergeben werden.
        house_number: Optionale Hausnummer, z. B. „58". Falls angegeben,
            werden zusätzliche Varianten mit angehängter Hausnummer erzeugt.
            Varianten *ohne* Hausnummer bleiben immer enthalten.
        advanced_variants: Optionale Liste mit zusätzlichen Varianten.
            Werden getrimmt, lowercase gemacht, Leerstrings ignoriert und
            Duplikate entfernt.

    Returns:
        Sortierte, deduplizierte Liste von Varianten in Kleinschreibung.
        Varianten enthalten echte Umlaute (z. B. „rötestr.").

    Raises:
        ValueError: Falls street leer oder nur aus Whitespace besteht.
    """
    if not street or not street.strip():
        raise ValueError(
            f"street darf nicht leer sein, erhalten: {street!r}"
        )

    base_str, suffix_type = _split_street_suffix(street)
    bases = _base_variants(base_str)
    umlaut_base = bases[0]  # immer die Umlaut-erhaltende Form

    seen: set[str] = set()
    result: list[str] = []

    def _add(v: str) -> None:
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            result.append(v)

    if suffix_type in _STRASSE_TYPES:
        # 1. Originalform mit ß – nur mit der Umlaut-Basis, nur zusammengezogen
        _add(umlaut_base + "straße")

        # 2. "strasse"-Form: alle Basen × Separatoren "", " ", "-"
        for b in bases:
            for sep in ["", " ", "-"]:
                _add(b + sep + "strasse")

        # 3. Abkürzungsformen "str." und "str": alle Basen × "" und " "
        for b in bases:
            for abbr in ["str.", "str"]:
                _add(b + abbr)
                _add(b + " " + abbr)

    elif suffix_type:
        # Andere Suffix-Typen (weg, allee, platz, …): zusammengezogen + Leerzeichen
        norm_suffix = suffix_type.lower()
        for b in bases:
            _add(b + norm_suffix)
            _add(b + " " + norm_suffix)

    else:
        # Kein erkanntes Suffix: nur Basis
        for b in bases:
            _add(b)

    # Hausnummer-Varianten werden *zusätzlich* ergänzt
    if house_number:
        hn = house_number.strip()
        if hn:
            for v in list(result):
                _add(v + " " + hn)

    # Benutzerdefinierte Varianten
    if advanced_variants:
        for av in advanced_variants:
            if av and av.strip():
                _add(av.strip().lower())

    return sorted(result)
