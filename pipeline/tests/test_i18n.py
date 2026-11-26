import pytest

from mtlhousing import i18n

NB = " "


def test_text_needs_both_languages():
    assert i18n.text("a", "b") == {"en": "a", "fr": "b"}
    with pytest.raises(ValueError):
        i18n.text("a", "")
    assert i18n.is_text({"en": "a", "fr": "b"})
    assert not i18n.is_text({"en": "a"}) and not i18n.is_text("a")


def test_quebec_number_formats():
    assert i18n.number_fr(1500) == f"1{NB}500"
    assert i18n.number_fr(89) == "89"
    assert i18n.pct_fr(0.006, 1) == f"0,6{NB}%"
    assert i18n.pct_fr(0.00019, 2) == f"0,02{NB}%"


def test_dates_and_lists():
    assert i18n.period_fr("October 2025") == "octobre 2025"
    assert i18n.quarter_fr("2026 Q2") == "deuxième trimestre de 2026"
    assert i18n.quarter_fr("2025 Q4") == "quatrième trimestre de 2025"
    assert i18n.and_list_fr(["A"]) == "A"
    assert i18n.and_list_fr(["A", "B", "C"]) == "A, B et C"
