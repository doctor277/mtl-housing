import json
import math

import pandas as pd
import pytest

from mtlhousing import cmhc_rent, config, export, rent, rent_export
from mtlhousing.rent_export import NONE_KEY, label_key, round_rent

NAN = math.nan


@pytest.mark.parametrize(
    "x, out",
    [
        (1612.5, 1625),  # a tie goes up, not to even
        (1637.5, 1650),
        (1612.49, 1600),
        (1604.3, 1600),
        (2238.32, 2250),
        (720.0, 725),
        (710.0, 700),
        (NAN, None),
        (None, None),
    ],
)
def test_round_rent_half_up_to_25(x, out):
    assert round_rent(x) == out


def test_round_rent_refuses_non_positive():
    with pytest.raises(ValueError, match="positive"):
        round_rent(0.0)


@pytest.mark.parametrize(
    "level, reliability, key",
    [
        ("neighbourhood", "ok", "neighbourhood"),
        ("zone", "ok", "zone"),
        ("neighbourhood", "low", "neighbourhood_low"),
        ("zone", "low", "zone_low"),
        (None, None, NONE_KEY),
        (NAN, NAN, NONE_KEY),  # what a DataFrame holds for None
    ],
)
def test_label_keys(level, reliability, key):
    assert label_key(level, reliability) == key


# --- build_rent on synthetic tables -----------------------------------------------------


def _table(values):
    rows = [
        {"area": a, "unit": u, "rent": float(v), "grade": g}
        for a, (v, g) in values.items()
        for u in cmhc_rent.UNITS
    ]
    df = pd.DataFrame(rows)
    df["usable"] = df["grade"].isin(cmhc_rent.USABLE_GRADES)
    return df


CMHC = {
    "neighbourhood": _table({"N1": (1100, "b"), "N2": (NAN, None), "N3": (900, "d")}),
    "zone": _table({"Z": (NAN, None)}),
    "cma": _table({"Montréal": (1000, "a")}),
}
QM = pd.DataFrame(
    {
        "quartier_id": ["01", "02", "02", "03"],
        "quartier_name": ["A", "B", "B", "C"],
        "cmhc_neighbourhood": ["N1", "N1", "N2", "N3"],
        "share": [1.0, 0.85, 0.15, 1.0],
        "confidence": ["verified", "verified", "verified", "high"],
        "note": ["", "", "", "matched by name"],
    }
)
ZM = pd.DataFrame({"cmhc_neighbourhood": ["N1", "N2", "N3"], "cmhc_zone": ["Z", "Z", "Z"]})
ASKING = pd.DataFrame(
    {"value": [1500.0] * 4 + [712.4], "status": "", "usable": True},
    index=pd.Index([*rent.UNITS, "room"], name="unit"),
)
REPORT = {
    # crosswalk.verify: 03 has no tract with rental units (n_tracts NaN)
    "quartiers": pd.DataFrame(
        {"quartier_id": ["01", "02", "02", "03"], "n_tracts": [2, 1, 1, NAN]}
    ),
    # a sliver folded into a split quartier: re-weighted over both kept parts
    "folded": pd.DataFrame(
        {"quartier_id": ["02"], "cmhc_neighbourhood": ["N9"], "raw_share": [0.012]}
    ),
    "homes_without_units_share": 0.017,
    "unallocated": pd.DataFrame({"ct_name": ["0001.00"], "units": [89]}),
    "unallocated_share": 0.00019,
}


def _build(asking=ASKING):
    est = rent.estimate_all(QM, ZM, CMHC, asking)
    return rent_export.build_rent(est, QM, REPORT, CMHC["cma"], asking, "2026 Q2", "2026-09-09")


def test_build_rent_rounds_labels_and_nulls():
    out = _build()
    r = out["results"]
    assert set(r) == {"01", "02", "03"} and all(set(q) == set(rent.UNITS) for q in r.values())
    assert r["01"]["2br"] == {
        "estimate": 1650,  # 1.1 x 1500
        "label": "neighbourhood",
        "grade": "b",
        "coverage_pct": None,
        "cmhc_areas": [{"type": "area", "name": "N1", "share": 1.0, "grade": "b"}],
    }
    assert r["02"]["1br"]["coverage_pct"] == 85  # N2 suppressed, N1 covers 85%
    assert r["02"]["1br"]["cmhc_areas"][0]["share"] == 0.85
    assert r["03"]["studio"]["label"] == "neighbourhood_low"
    assert r["03"]["studio"]["estimate"] == 1350  # 0.9 x 1500
    assert out["meta"]["room"]["estimate"] == 700  # 712.4 -> 700
    # valid JSON: no NaN anywhere
    json.dumps(out, allow_nan=False)


def test_not_enough_data_is_null_with_no_areas():
    cmhc = dict(
        CMHC, neighbourhood=_table({"N1": (NAN, None), "N2": (NAN, None), "N3": (NAN, None)})
    )
    est = rent.estimate_all(QM, ZM, cmhc, ASKING)
    out = rent_export.build_rent(est, QM, REPORT, CMHC["cma"], ASKING, "2026 Q2", "2026-09-09")
    e = out["results"]["01"]["studio"]
    assert e == {
        "estimate": None,
        "label": "none",
        "grade": None,
        "coverage_pct": None,
        "cmhc_areas": [],
    }


def test_meta_carries_sources_grade_words_and_crosswalk_notes():
    m = _build()["meta"]
    assert m["rounding"] == {"step": 25, "mode": "half_up"}
    assert m["shown_bedroom_types"] == ["studio", "1br", "2br"]
    assert m["grade_words"] == {
        "a": {"en": "excellent", "fr": "excellent"},
        "b": {"en": "very good", "fr": "très bon"},
        "c": {"en": "good", "fr": "bon"},
        "d": {"en": "use with caution", "fr": "utiliser avec prudence"},
    }
    assert m["statcan"]["quarter"] == "2026 Q2" and m["statcan"]["experimental"] is True
    assert m["montreal"]["1br"] == {"cmhc_average": 1000.0, "statcan_asking": 1500.0}
    assert any("Canada Mortgage and Housing Corporation" in s["en"] for s in m["sources"])
    assert any("Société canadienne d’hypothèques et de logement" in s["fr"] for s in m["sources"])
    notes = {(n["kind"], n["quartier_id"]): n for n in m["crosswalk_notes"]}
    link = notes[("unconfirmed_link", "03")]
    assert link["cmhc_area"] == "N3" and "detail" not in link  # no internal CSV note
    assert link["text"]["en"].endswith("none of its census tracts has CMHC rental units.")
    assert link["text"]["fr"].startswith("Rattaché au secteur de la SCHL N3 d’après son nom.")
    folded = notes[("folded", "02")]
    assert folded["share"] == 0.012 and folded["counted_with"] == ["N1", "N2"]
    assert "counted with N1 and N2 instead" in folded["text"]["en"]
    # Québec format: decimal comma, non-breaking space before %, "et" in lists.
    assert folded["text"]["fr"].startswith("1,2 % de ses logements locatifs")
    assert "plutôt comptés avec N1 et N2." in folded["text"]["fr"]
    assert ("homes_without_units", None) in notes and ("unallocated_units", None) in notes
    ville = m["sources"][-1]
    assert ville["en"].startswith("With data from Quartiers de référence en habitation taken")
    assert "Ville de Montréal open data website, licensed under CC BY 4.0." in ville["en"]
    cmhc = m["sources"][0]["en"]
    assert cmhc.endswith("endorsement by Canada Mortgage and Housing Corporation of this product.")
    assert "données ouvertes de la Ville de Montréal, sous licence CC BY 4.0." in ville["fr"]


@pytest.mark.parametrize("grade, key", [("a", "zone"), ("d", "zone_low")])
def test_zone_values_list_the_zone_once_with_the_parts_shares_summed(grade, key):
    # N1 and N2 suppressed, both in zone Z -> quartier 02 uses Z for its whole 100%
    cmhc = dict(
        CMHC,
        neighbourhood=_table({"N1": (NAN, None), "N2": (NAN, None), "N3": (900, "d")}),
        zone=_table({"Z": (1050, grade)}),
    )
    est = rent.estimate_all(QM, ZM, cmhc, ASKING)
    out = rent_export.build_rent(est, QM, REPORT, CMHC["cma"], ASKING, "2026 Q2", "2026-09-09")
    e = out["results"]["02"]["2br"]
    assert e["label"] == key and e["grade"] == grade and e["coverage_pct"] is None
    assert e["cmhc_areas"] == [{"type": "zone", "name": "Z", "share": 1.0, "grade": grade}]
    assert e["estimate"] == round_rent(1.05 * 1500)


@pytest.mark.parametrize(
    "room, match",
    [
        ({"status": "E"}, "room"),
        ({"usable": False}, "room"),
    ],
)
def test_build_rent_stops_on_a_flagged_room_value(room, match):
    asking = ASKING.copy()
    for k, v in room.items():
        asking.loc["room", k] = v
    with pytest.raises(ValueError, match=match):
        _build(asking)


# --- the committed file (also runs in CI) -------------------------------------------------

committed = pytest.mark.skipif(not rent_export.RENT_JSON.exists(), reason="run rent-export first")


@committed
def test_committed_rent_json_is_consistent():
    d = json.loads(rent_export.RENT_JSON.read_text(encoding="utf-8"))
    gj = json.loads(export.NEIGHBOURHOODS_GEOJSON.read_text(encoding="utf-8"))
    residents = {
        f["properties"]["id"] for f in gj["features"] if not f["properties"]["no_residents"]
    }
    assert set(d["results"]) == residents
    keys = set(d["meta"]["label_keys"])
    step = d["meta"]["rounding"]["step"]
    for qid, units in d["results"].items():
        assert set(units) == set(d["meta"]["bedroom_types"]), qid
        for unit, e in units.items():
            assert e["label"] in keys, (qid, unit)
            assert (e["estimate"] is None) == (e["label"] == "none"), (qid, unit)
            if e["estimate"] is None:
                assert e["cmhc_areas"] == [] and e["grade"] is None
                continue
            assert e["estimate"] > 0 and e["estimate"] % step == 0, (qid, unit)
            assert e["grade"] in d["meta"]["grade_words"]
            shares = [a["share"] for a in e["cmhc_areas"]]
            assert shares and all(0 < s <= 1 for s in shares)
            pct = e["coverage_pct"]
            assert pct is None or 80 <= pct < 100
    assert d["meta"]["room"]["estimate"] % step == 0
    assert any(n["kind"] == "unconfirmed_link" for n in d["meta"]["crosswalk_notes"])


REAL = [
    *config.CMHC_RENT_CSV.values(),
    *config.CMHC_UNIVERSE_CSV.values(),
    config.STATCAN_RENT_ZIP,
    config.STATCAN_GAF_ZIP,
    config.QUARTIERS_GEOJSON,
    config.LOGEMENTS_CSV,
]


@committed
@pytest.mark.skipif(not all(p.exists() for p in REAL), reason="raw files absent")
def test_committed_rent_json_is_up_to_date(tmp_path):
    fresh, _ = rent_export.run(tmp_path / "rent.json")
    committed_ = json.loads(rent_export.RENT_JSON.read_text(encoding="utf-8"))
    assert fresh["results"] == committed_["results"]
    drop = {"generated_at"}
    assert {k: v for k, v in fresh["meta"].items() if k not in drop} == {
        k: v for k, v in committed_["meta"].items() if k not in drop
    }
