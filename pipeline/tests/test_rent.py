import math

import pandas as pd
import pytest

from mtlhousing import cmhc_rent, config, rent
from mtlhousing.rent import CmhcRent, Part, choose_source, coverage_pct, estimate_quartier

NAN = math.nan
SUPPRESSED = CmhcRent(NAN, None)


def r(rent, grade):
    return CmhcRent(float(rent), grade)


SOURCE_CASES = [
    # a/b/c at the neighbourhood wins, even over a better zone grade
    (r(1000, "c"), r(1100, "a"), "neighbourhood", 1000, "ok"),
    # neighbourhood d or ** -> zone a/b/c beats any grade d
    (r(1000, "d"), r(1100, "b"), "zone", 1100, "ok"),
    (SUPPRESSED, r(1100, "a"), "zone", 1100, "ok"),
    # no a/b/c anywhere -> grade d, neighbourhood first
    (r(1000, "d"), r(1100, "d"), "neighbourhood", 1000, "low"),
    (r(1000, "d"), SUPPRESSED, "neighbourhood", 1000, "low"),
    (SUPPRESSED, r(1100, "d"), "zone", 1100, "low"),
    # ** at both levels -> not enough data
    (SUPPRESSED, SUPPRESSED, None, NAN, None),
]


@pytest.mark.parametrize("nbhd, zone, level, rent, reliability", SOURCE_CASES)
def test_source_order(nbhd, zone, level, rent, reliability):
    s = choose_source(nbhd, zone)
    assert s.level == level and s.reliability == reliability
    assert (math.isnan(s.rent) and math.isnan(rent)) or s.rent == rent


def test_suppressed_is_never_used_even_with_a_stray_value():
    # a rent without a grade (or a grade without a rent) is treated as suppressed
    assert choose_source(CmhcRent(999.0, None), SUPPRESSED).level is None
    assert choose_source(CmhcRent(NAN, "a"), SUPPRESSED).level is None
    # pandas gives NaN, not None, for a missing grade
    assert choose_source(CmhcRent(NAN, NAN), r(1100, "d")).level == "zone"


# --- one estimate per quartier -----------------------------------------------------------

CMA_RENT = 1000.0


def part(nbhd, share, n_value, z_value, zone="Z"):
    return Part(nbhd, zone, share, {"neighbourhood": n_value, "zone": z_value})


@pytest.mark.parametrize("nbhd, zone, level, value, reliability", SOURCE_CASES)
def test_one_neighbourhood_quartier_follows_choose_source(nbhd, zone, level, value, reliability):
    e = estimate_quartier([part("N", 1.0, nbhd, zone)], CMA_RENT)
    assert (e.level, e.reliability) == (level, reliability)
    if level is None:
        assert math.isnan(e.ratio) and e.label == "not enough data" and e.coverage == 0
    else:
        assert e.ratio == pytest.approx(value / CMA_RENT) and e.coverage == 1
        assert "covers" not in e.label


def test_split_averages_ratios_by_share_and_keeps_the_worst_grade():
    e = estimate_quartier(
        [part("N1", 0.53, r(900, "a"), r(1, "a")), part("N2", 0.47, r(1200, "c"), r(1, "a"))],
        CMA_RENT,
    )
    assert e.level == "neighbourhood" and e.grade == "c"
    assert e.ratio == pytest.approx(0.53 * 0.9 + 0.47 * 1.2)
    assert e.label == "estimate (CMHC neighbourhood)"  # 0.53 + 0.47 covers it all
    assert e.areas == "N1 0.530 (a) + N2 0.470 (c)"


def test_parts_covering_80_percent_are_reweighted_and_labelled():
    e = estimate_quartier(
        [part("N1", 0.866, r(1100, "b"), r(1, "a")), part("N2", 0.134, SUPPRESSED, r(1, "a"))],
        CMA_RENT,
    )
    assert e.level == "neighbourhood" and e.ratio == pytest.approx(1.1)  # re-weighted
    assert e.coverage == pytest.approx(0.866)
    assert e.label == "estimate (CMHC neighbourhood), covers 86% of rental units"
    assert e.areas == "N1 0.866 (b)"


@pytest.mark.parametrize("share, level", [(0.80, "neighbourhood"), (0.799, "zone")])
def test_coverage_threshold_is_inclusive(share, level):
    parts = [
        part("N1", share, r(1100, "b"), r(1300, "b")),
        part("N2", round(1 - share, 3), SUPPRESSED, r(1300, "b")),
    ]
    assert estimate_quartier(parts, CMA_RENT).level == level


def test_below_80_percent_falls_back_to_the_zone_even_with_a_neighbourhood_value():
    # Shape of Gabriel-Sagard, studio: one part graded c (53%), the other ** -> the zone
    # covers both halves. Values are fake.
    parts = [
        part("N1", 0.53, r(906, "c"), r(950, "b")),
        part("N2", 0.47, SUPPRESSED, r(950, "b")),
    ]
    e = estimate_quartier(parts, CMA_RENT)
    assert (e.level, e.grade, e.ratio) == ("zone", "b", pytest.approx(0.95))
    assert e.areas == "Z (b)" and e.label == "zone estimate (CMHC zone)"


def test_coverage_rule_applies_at_grade_d_steps_with_a_combined_label():
    parts = [
        part("N1", 0.9, r(1200, "d"), SUPPRESSED),
        part("N2", 0.1, SUPPRESSED, SUPPRESSED),
    ]
    e = estimate_quartier(parts, CMA_RENT)
    assert (e.level, e.reliability, e.grade) == ("neighbourhood", "low", "d")
    assert e.label == "low reliability (CMHC grade d), covers 90% of rental units"
    # zone level, grade d, parts in two zones
    parts = [
        part("N1", 0.85, SUPPRESSED, r(1200, "d"), zone="Z1"),
        part("N2", 0.15, SUPPRESSED, SUPPRESSED, zone="Z2"),
    ]
    e = estimate_quartier(parts, CMA_RENT)
    assert e.label == "low reliability (CMHC grade d), zone level, covers 85% of rental units"
    assert e.areas == "Z1 0.850 (d)"


def test_grade_d_steps_count_c_parts_too():
    # Nouveau-Bordeaux, 3+ bedrooms pattern: one part c under 80%, the other d, zone not
    # a/b/c. Step 3 counts both (d or better): neighbourhood level, 100% covered, grade d.
    parts = [
        part("N1", 0.619, r(1400, "c"), r(1450, "d")),
        part("N2", 0.381, r(1950, "d"), r(1450, "d")),
    ]
    e = estimate_quartier(parts, CMA_RENT)
    assert (e.level, e.reliability, e.grade) == ("neighbourhood", "low", "d")
    assert e.coverage == 1 and e.ratio == pytest.approx(0.619 * 1.4 + 0.381 * 1.95)
    assert e.label == "low reliability (CMHC grade d)"
    assert e.areas == "N1 0.619 (c) + N2 0.381 (d)"


def test_grade_d_never_beats_a_qualifying_abc_step():
    # neighbourhood a/b/c covers only 62% -> zone a/b/c wins over neighbourhood d at 100%
    parts = [
        part("N1", 0.62, r(1300, "c"), r(1250, "c")),
        part("N2", 0.38, r(1900, "d"), r(1250, "c")),
    ]
    assert estimate_quartier(parts, CMA_RENT).level == "zone"


@pytest.mark.parametrize(
    "coverage, pct", [(1.0, None), (0.53 + 0.47, None), (0.866, 86), (0.999, 99), (0.8, 80)]
)
def test_coverage_pct_rounds_down(coverage, pct):
    assert coverage_pct(coverage) == pct


def test_estimate_quartier_refuses_bad_input():
    with pytest.raises(ValueError, match="do not sum to 1"):
        estimate_quartier([part("N", 0.5, r(1, "a"), r(1, "a"))], CMA_RENT)
    with pytest.raises(ValueError, match="positive"):
        estimate_quartier([part("N", 1.0, r(1, "a"), r(1, "a"))], NAN)


# --- all quartiers (synthetic tables) ----------------------------------------------------


def _table(values):
    """values: {area: (rent, grade)} -> cmhc_rent long format, same value for every unit."""
    rows = [
        {"area": a, "unit": u, "rent": float(v), "grade": g}
        for a, (v, g) in values.items()
        for u in cmhc_rent.UNITS
    ]
    df = pd.DataFrame(rows)
    df["usable"] = df["grade"].isin(cmhc_rent.USABLE_GRADES)
    return df


CMHC = {
    "neighbourhood": _table({"N1": (1100, "b"), "N2": (NAN, None)}),
    "zone": _table({"Z": (1050, "a")}),
    "cma": _table({"Montréal": (1000, "a")}),
}
QM = pd.DataFrame(
    {
        "quartier_id": ["01", "02", "02"],
        "quartier_name": ["A", "B", "B"],
        "cmhc_neighbourhood": ["N1", "N1", "N2"],
        "share": [1.0, 0.5, 0.5],
    }
)
ZM = pd.DataFrame({"cmhc_neighbourhood": ["N1", "N2"], "cmhc_zone": ["Z", "Z"]})


def _asking(status="", usable=True):
    index = pd.Index(rent.UNITS, name="unit")
    return pd.DataFrame({"value": 1500.0, "status": status, "usable": usable}, index=index)


def test_estimate_all_scales_ratios_to_the_statcan_level():
    est = rent.estimate_all(QM, ZM, CMHC, _asking()).set_index(["quartier_id", "unit"])
    assert len(est) == 2 * len(rent.UNITS)
    a = est.loc[("01", "2br")]
    assert a["estimate"] == pytest.approx(1.1 * 1500) and a["level"] == "neighbourhood"
    assert pd.isna(a["coverage_pct"])
    b = est.loc[("02", "2br")]  # N1 covers only 50% -> zone
    assert b["estimate"] == pytest.approx(1.05 * 1500) and b["level"] == "zone"
    assert b["cmhc_areas"] == "Z (a)" and b["n_parts"] == 2


@pytest.mark.parametrize(
    "asking, match",
    [(_asking(status="E"), "status 'E'"), (_asking(usable=False), "missing or unusable")],
)
def test_estimate_all_stops_on_a_flagged_statcan_level(asking, match):
    with pytest.raises(ValueError, match=match):
        rent.estimate_all(QM, ZM, CMHC, asking)


def test_estimate_all_stops_on_an_unusable_cmhc_average():
    cmhc = dict(CMHC, cma=_table({"Montréal": (NAN, None)}))
    with pytest.raises(ValueError, match="CMHC Montréal average"):
        rent.estimate_all(QM, ZM, cmhc, _asking())


# --- the real files -----------------------------------------------------------------------

REAL = [*config.CMHC_RENT_CSV.values(), config.STATCAN_RENT_ZIP]


@pytest.mark.skipif(not all(p.exists() for p in REAL), reason="raw CMHC / StatCan files absent")
def test_real_estimates():
    from mtlhousing import crosswalk, statcan_rent

    qm = crosswalk.load_quartier_map(config.QUARTIER_TO_CMHC_CSV)
    zm = crosswalk.load_zone_map(config.CMHC_NBHD_TO_ZONE_CSV)
    cmhc = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    rents = statcan_rent.load_montreal_rents(config.STATCAN_RENT_ZIP)
    asking = statcan_rent.asking_rents(rents, config.STATCAN_RENT_QUARTER)
    est = rent.estimate_all(qm, zm, cmhc, asking)

    assert len(est) == qm["quartier_id"].nunique() * len(rent.UNITS)
    has = est["level"].notna()
    assert (est.loc[has, "estimate"] > 0).all() and est.loc[~has, "estimate"].isna().all()
    assert (est.loc[~has, "label"] == "not enough data").all()
    e = est.set_index(["quartier_name", "unit"])
    # the cases docs/methodology.md describes
    for unit in rent.UNITS:
        assert e.loc[("Côte-Saint-Luc", unit), "label"] == (
            "estimate (CMHC neighbourhood), covers 86% of rental units"
        )
    assert e.loc[("Côte-Saint-Luc", "1br"), "estimate"] == pytest.approx(1226 / 1131 * 1480)
    assert e.loc[("Gabriel-Sagard", "studio"), "level"] == "zone"
    nb = e.loc[("Nouveau-Bordeaux", "3br_plus")]
    assert (nb["level"], nb["reliability"], nb["coverage"]) == ("neighbourhood", "low", 1)
    assert nb["label"] == "low reliability (CMHC grade d)"
    assert nb["cmhc_areas"] == "Ahuntsic 0.619 (c) + Cartierville 0.381 (d)"
    n_none = est[est["level"].isna()].groupby("unit").size().reindex(rent.UNITS).fillna(0)
    assert n_none.astype(int).tolist() == [0, 6, 6, 33]
