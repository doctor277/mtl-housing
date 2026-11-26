"""Text the site shows from the data files, in both languages (M5.3a, owner's M5 decision 5).

A shown text is exported as {"en": ..., "fr": ...}; numbers never change with the language.
Only text the site displays is bilingual (campus and building names, credits, CMHC's grade
words, the crosswalk notes, out-of-scope reasons). Notes meant for developers (rule_note,
quantiles, label_keys, ...) stay in English.

French follows Québec usage (owner, M5 decisions 8 and M5.3 answers): a non-breaking space
before "%" and ":" and as the thousands separator, a decimal comma.
"""

from __future__ import annotations

NBSP = " "
LANGS = ("en", "fr")

MONTHS_EN_FR = {
    "January": "janvier",
    "February": "février",
    "March": "mars",
    "April": "avril",
    "May": "mai",
    "June": "juin",
    "July": "juillet",
    "August": "août",
    "September": "septembre",
    "October": "octobre",
    "November": "novembre",
    "December": "décembre",
}

# Statistics Canada's French quarter wording ("deuxième trimestre de 2026", table 46-10-0092-01).
QUARTERS_FR = {1: "premier", 2: "deuxième", 3: "troisième", 4: "quatrième"}


def text(en: str, fr: str) -> dict[str, str]:
    """A text shown on the site, in both languages."""
    if not en or not fr:
        raise ValueError("a shown text needs both an English and a French version")
    return {"en": en, "fr": fr}


def is_text(x: object) -> bool:
    """True for an exported {"en": ..., "fr": ...} text."""
    return (
        isinstance(x, dict) and set(x) == set(LANGS) and all(isinstance(x[k], str) for k in LANGS)
    )


def number_fr(x: float, decimals: int = 0) -> str:
    """1500 -> "1 500", 0.6 -> "0,6" (non-breaking space, decimal comma)."""
    s = f"{x:,.{decimals}f}"
    return s.replace(",", NBSP).replace(".", ",")


def pct_fr(share: float, decimals: int) -> str:
    """0.006 -> "0,6 %" (as Python's "{:.1%}" in English)."""
    return f"{number_fr(share * 100, decimals)}{NBSP}%"


def period_fr(period: str) -> str:
    """CMHC's "October 2025" -> "octobre 2025"."""
    month, year = period.split()
    return f"{MONTHS_EN_FR[month]} {year}"


def quarter_fr(label: str) -> str:
    """The English quarter label "2026 Q2" (statcan_rent.quarter_label) -> "deuxième
    trimestre de 2026"."""
    year, q = label.split(" Q")
    return f"{QUARTERS_FR[int(q)]} trimestre de {year}"


def and_list_fr(items: list[str]) -> str:
    """French list: a, b et c."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " et " + items[-1]
