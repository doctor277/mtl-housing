"""M5.3a (owner's M5 decision 5): the bilingual re-export changes only text, never a number.

The site's data files now carry each shown text as {"en": ..., "fr": ...}. These tests prove,
on the committed files, that:
- every number (and every key, null and boolean) is exactly what the last English-only export
  wrote, and
- every English text is unchanged too, except the two credit lines the owner asked to fix
  ("licensed under CC BY 4.0", M4.3/M6).

The pre-M5.3a values are pinned as SHA-256 fingerprints, computed from the files on main at
6b88ece. CI checks out one commit only, so the old files can't be read from git there.
The fingerprints describe those inputs only: once the data is refreshed (new schedules, a new
StatCan quarter, ...), the pinned check skips and says so, and the structural checks still run.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from mtlhousing import config, i18n

FILES = ("commute.json", "rent.json", "neighbourhoods.geojson")


def english(obj):
    """The file as an English-only export would have written it: {"en","fr"} -> its "en"."""
    if i18n.is_text(obj):
        return obj["en"]
    if isinstance(obj, dict):
        return {k: english(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [english(v) for v in obj]
    return obj


def leaves(obj, path=""):
    """(path, value) for every leaf, in file order."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{path}/{i}")
    else:
        yield path, obj


# Written at every export, so not part of the comparison.
VOLATILE = {"/meta/generated_at"}


def fingerprint(pairs) -> str:
    data = json.dumps([[p, v] for p, v in pairs], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def numbers_fingerprint(obj) -> str:
    """Every non-text leaf (numbers, booleans, nulls) with its path."""
    return fingerprint(
        (p, v) for p, v in leaves(english(obj)) if not isinstance(v, str) and p not in VOLATILE
    )


def english_text_fingerprint(obj, replace: dict[str, str] | None = None) -> str:
    """Every English text leaf with its path; `replace` maps an old text to its fixed one."""
    replace = replace or {}
    return fingerprint(
        (p, replace.get(v, v))
        for p, v in leaves(english(obj))
        if isinstance(v, str) and p not in VOLATILE
    )


def load(name: str):
    return json.loads((config.WEB_DATA_DIR / name).read_text(encoding="utf-8"))


# The two English credit lines the owner asked to fix, old -> new (DATA_SOURCES.md wording).
CREDIT_FIXES = {
    "Transit schedules: Société de transport de Montréal, Réseau express métropolitain and exo, "
    "CC BY 4.0. Travel times are derived from these schedules.": "Transit schedules: Société de "
    "transport de Montréal, Réseau express métropolitain and exo, licensed under CC BY 4.0. "
    "Travel times are derived from these schedules.",
    "Contains data from the Ville de Montréal open data portal, CC BY 4.0.": "Contains data from "
    "the Ville de Montréal open data portal, licensed under CC BY 4.0.",
}

# Fingerprints of the last English-only export (main at 6b88ece), English texts with the two
# credit fixes applied.
PINNED = {
    "commute.json": (
        "f4d4d9976ba5a0494ebc895c24d4cad39fb368a13ed2958e8a51db9f356a4f18",
        "2a9fe66bb85469a27cb35abb0af7ee06cbb1316e7239f81fa791a18084d895cf",
    ),
    "rent.json": (
        "1990e1b5cc58b5885c240661bb1e711ac8364dab08cafd0d10e62f70b1f6e483",
        "163413744d3633341609e6298f69916e1640714641f7036e2f56c5d3845c5848",
    ),
    "neighbourhoods.geojson": (
        "cd3986cd80b54ebac330b7c756b8b4eaf9f758bfef63ee510d398e40f86cc4e3",
        "770a8cabce13adb561f2a0e15272c5c33a91b8be1339fe96171429190970352f",
    ),
}

# The inputs of that export. The pinned check applies only while the files still come from them.
PINNED_INPUTS = {
    "analysis_date": "2026-12-01",
    "gtfs_feeds": [
        {
            "name": "stm",
            "version": "20261029135439_26N",
            "start": "2026-08-24",
            "end": "2027-01-03",
        },
        {"name": "rem", "version": "20260520", "start": "2026-05-19", "end": "2026-12-31"},
        {"name": "exo_trains", "version": None, "start": "2026-10-19", "end": "2027-01-03"},
    ],
    "osm_date": "2026-11-19T21:22:20Z",
    "cmhc_period": "October 2025",
    "statcan_quarter": "2026 Q2",
    "statcan_released": "2026-09-09",
}


def current_inputs() -> dict:
    c, r = load("commute.json")["meta"], load("rent.json")["meta"]
    return {
        "analysis_date": c["analysis_date"],
        "gtfs_feeds": c["gtfs_feeds"],
        "osm_date": c["osm_date"],
        "cmhc_period": r["cmhc"]["period"],
        "statcan_quarter": r["statcan"]["quarter"],
        "statcan_released": r["statcan"]["released"],
    }


have_files = all((config.WEB_DATA_DIR / f).exists() for f in FILES)
pytestmark = pytest.mark.skipif(not have_files, reason="run export and rent-export first")


@pytest.mark.parametrize("name", FILES)
def test_reexport_keeps_every_number(name):
    if current_inputs() != PINNED_INPUTS:
        pytest.skip("data refreshed since M5.3a: the pinned pre-M5.3a fingerprints no longer apply")
    got = numbers_fingerprint(load(name))
    assert got == PINNED[name][0], f"{name}: a number, key or null changed"


@pytest.mark.parametrize("name", FILES)
def test_reexport_keeps_every_english_text_but_the_two_credit_fixes(name):
    if current_inputs() != PINNED_INPUTS:
        pytest.skip("data refreshed since M5.3a: the pinned pre-M5.3a fingerprints no longer apply")
    got = english_text_fingerprint(load(name))
    assert got == PINNED[name][1], f"{name}: an English text changed"


def test_the_credit_fixes_are_in_the_files():
    files = [load("commute.json"), load("rent.json")]
    credits = [english(s) for f in files for s in f["meta"]["sources"]]
    for fixed in CREDIT_FIXES.values():
        assert fixed in credits
    for old in CREDIT_FIXES:
        assert old not in credits


def shown_texts(obj, path=""):
    """Every bilingual text in a file, with its path."""
    if i18n.is_text(obj):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from shown_texts(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from shown_texts(v, f"{path}/{i}")


def test_every_text_the_site_shows_is_bilingual():
    c, r = load("commute.json")["meta"], load("rent.json")["meta"]
    shown = [*c["sources"], *r["sources"], *[o["reason"] for o in c["out_of_scope"]]]
    shown += [n["text"] for n in r["crosswalk_notes"]] + list(r["grade_words"].values())
    for camp in c["campuses"].values():
        shown += [camp["name"], *[d["name"] for d in camp["destinations"]]]
    assert all(i18n.is_text(x) for x in shown)
    # Same in both languages on purpose: proper names, and CMHC's "excellent" (its French legend).
    same_ok = {"excellent"}
    for path, t in [*shown_texts(c), *shown_texts(r)]:
        assert t["en"].strip() and t["fr"].strip(), path
        assert t["fr"] != t["en"] or path.endswith("/name") or t["en"] in same_ok, (
            f"{path}: French equals English"
        )


def test_no_bilingual_text_in_the_geometry_file():
    assert list(shown_texts(load("neighbourhoods.geojson"))) == []
