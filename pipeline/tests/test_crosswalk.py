import pandas as pd
import pytest

from mtlhousing import cmhc_rent, config, crosswalk

Q_HEAD = "quartier_id,quartier_name,cmhc_neighbourhood,share,confidence,note\n"
Z_HEAD = "cmhc_neighbourhood,cmhc_zone,confidence,note\n"


def _csv(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _cmhc(rents):
    """rents: {level: {area: rent for 1br}}"""
    out = {}
    for level, areas in rents.items():
        out[level] = pd.DataFrame(
            [{"area": a, "unit": "1br", "rent": r, "usable": True} for a, r in areas.items()]
        )
    return out


QUARTIERS = pd.DataFrame(
    {"id": ["01", "02", "02-park"], "name": ["A", "B", "Park"], "no_residents": [0, 0, 1]}
)
CMHC = _cmhc({"neighbourhood": {"N1": 1000.0, "N2": 1200.0}, "zone": {"Z": 1100.0}})


@pytest.fixture
def maps(tmp_path):
    q = _csv(tmp_path, "q.csv", Q_HEAD + "01,A,N1,1,high,\n02,B,N1,0.25,low,\n02,B,N2,0.75,low,\n")
    z = _csv(tmp_path, "z.csv", Z_HEAD + "N1,Z,high,\nN2,Z,medium,\n")
    return crosswalk.load_quartier_map(q), crosswalk.load_zone_map(z)


def test_valid_maps_pass(maps):
    qm, zm = maps
    assert qm["quartier_id"].tolist() == ["01", "02", "02"]  # ids stay strings
    crosswalk.check(qm, zm, QUARTIERS, CMHC)


@pytest.mark.parametrize(
    "rows, match",
    [
        ("01,A,N1,0.6,high,\n01,A,N2,0.6,high,\n", "do not sum to 1"),
        ("01,A,N1,1,sure,\n", "unknown confidence"),
        ("01,A,N1,0.5,high,\n01,A,N1,0.5,high,\n", "duplicate"),
        ("01,A,N1,0,high,\n01,A,N2,1,high,\n", r"in \(0, 1\]"),
    ],
)
def test_quartier_map_refuses(tmp_path, rows, match):
    with pytest.raises(ValueError, match=match):
        crosswalk.load_quartier_map(_csv(tmp_path, "q.csv", Q_HEAD + rows))


def test_check_refuses_missing_quartier_unknown_name_and_unzoned(maps, tmp_path):
    qm, zm = maps
    with pytest.raises(ValueError, match=r"not mapped: \['02'\]"):
        crosswalk.check(qm[qm["quartier_id"] == "01"], zm, QUARTIERS, CMHC)
    with pytest.raises(ValueError, match="not in the CMHC export"):
        crosswalk.check(qm.replace({"N2": "N9"}), zm, QUARTIERS, CMHC)
    with pytest.raises(ValueError, match="differ"):
        crosswalk.check(qm, zm[zm["cmhc_neighbourhood"] == "N1"], QUARTIERS, CMHC)
    with pytest.raises(ValueError, match="names differ"):
        crosswalk.check(qm.replace({"quartier_name": {"A": "X"}}), zm, QUARTIERS, CMHC)


def test_zone_bounds(maps):
    _, zm = maps
    b = crosswalk.zone_bounds(zm, CMHC)
    assert b["inside"].tolist() == [True]
    out = crosswalk.zone_bounds(zm, _cmhc({"neighbourhood": {"N1": 1000.0, "N2": 1200.0},
                                           "zone": {"Z": 1300.0}}))  # fmt: skip
    assert out["inside"].tolist() == [False]


# --- verification against unit counts (synthetic) ----------------------------------
#
# Tracts 0001.00 + 0002.00 -> N1, 0003.00 -> N2; both in zone Z.
# Quartier 01: all of tract 1, a quarter of tract 2's homes, and a tract with no rental
# units (0009.00, absent from the export). Quartier 02: the rest of tract 2, all of tract 3.
# Quartier 03: homes only in 0009.00 -> no rental units, can't be checked.


def _units(rows):
    """rows: {area: {unit: count or None}} -> universe long format."""
    return pd.DataFrame(
        [{"area": a, "unit": u, "units": n} for a, c in rows.items() for u, n in c.items()]
    ).astype({"units": "Int64"})


UNIVERSE = {
    "tract": _units(
        {
            "0001.00": {"studio": 10, "total": 100},
            "0002.00": {"studio": None, "total": 80},
            "0003.00": {"studio": 5, "total": 40},
        }
    ),
    "neighbourhood": _units({"N1": {"studio": 12, "total": 180}, "N2": {"studio": 5, "total": 40}}),
    "zone": _units({"Z": {"studio": 17, "total": 220}}),
}
TRACT_MAP = pd.DataFrame(
    {"ct_name": ["0001.00", "0002.00", "0003.00"], "cmhc_neighbourhood": ["N1", "N1", "N2"]}
)
HOMES = pd.DataFrame(
    [
        ("01", "0001.00", 300),
        ("01", "0002.00", 50),
        ("01", "0009.00", 70),
        ("02", "0002.00", 150),
        ("02", "0003.00", 100),
        ("03", "0009.00", 40),
    ],
    columns=["quartier_id", "ct_name", "homes"],
)
# 01: N1 = 100 + 80/4 = 120 -> 1. 02: N1 = 60, N2 = 40 -> 0.6 / 0.4.
GOOD_Q = "01,A,N1,1,verified,\n02,B,N1,0.6,verified,\n02,B,N2,0.4,verified,\n03,C,N1,1,high,\n"
GOOD_Z = "N1,Z,verified,\nN2,Z,verified,\n"


CENSUS_TRACTS = {"0001.00", "0002.00", "0003.00", "0009.00"}


def _verify(tmp_path, q=GOOD_Q, z=GOOD_Z, universe=UNIVERSE, homes=HOMES, **kw):
    qm = crosswalk.load_quartier_map(_csv(tmp_path, "q.csv", Q_HEAD + q))
    zm = crosswalk.load_zone_map(_csv(tmp_path, "z.csv", Z_HEAD + z))
    return crosswalk.verify(qm, zm, TRACT_MAP, universe, homes, CENSUS_TRACTS, **kw)


def test_sum_check_statuses():
    children = pd.DataFrame(
        {"p": ["A", "A", "B", "C", "C"], "unit": "total", "units": [1, 2, 5, 4, None]}
    ).astype({"units": "Int64"})
    parents = _units({"A": {"total": 3}, "B": {"total": 6}, "C": {"total": 3}})
    s = crosswalk.sum_check(children, parents, "p").set_index("p")["status"]
    # C: a suppressed child, and the published ones already exceed the parent
    assert s.to_dict() == {"A": "match", "B": "mismatch", "C": "mismatch"}
    parents = _units({"A": {"total": 3}, "B": {"total": 5}, "C": {"total": 9}})
    s = crosswalk.sum_check(children, parents, "p").set_index("p")["status"]
    assert s.to_dict() == {"A": "match", "B": "match", "C": "unchecked"}
    with pytest.raises(ValueError, match="not in the universe export"):
        crosswalk.sum_check(children, parents[parents["area"] != "C"], "p")
    # A suppressed parent count can't be checked either way.
    parents = _units({"A": {"total": None}, "B": {"total": 5}, "C": {"total": 9}})
    s = crosswalk.sum_check(children, parents, "p").set_index("p")["status"]
    assert s["A"] == "unchecked"


def test_confirmed_needs_a_matching_total_and_no_contradiction():
    s = pd.DataFrame(
        {
            "k": ["A", "A", "B", "B", "C"],
            "unit": ["total", "studio", "total", "studio", "studio"],
            "status": ["match", "unchecked", "match", "mismatch", "match"],
        }
    )
    assert crosswalk.confirmed(s, "k") == {"A"}


def test_derive_shares_splits_edge_tracts_by_homes():
    d = crosswalk.derive_shares(HOMES, TRACT_MAP, UNIVERSE["tract"]).set_index(
        ["quartier_id", "cmhc_neighbourhood"]
    )
    assert d.loc[("01", "N1"), "units"] == pytest.approx(120)
    assert d.loc[("02", "N1"), "share"] == pytest.approx(0.6)
    assert d.loc[("02", "N2"), "share"] == pytest.approx(0.4)
    assert d.loc[("01", "N1"), "n_tracts"] == 2  # the no-units tract doesn't count
    assert "03" not in d.index.get_level_values(0)  # no rental units at all


def test_derive_shares_folds_small_parts():
    d = crosswalk.derive_shares(HOMES, TRACT_MAP, UNIVERSE["tract"], fold_below=0.45)
    d = d.set_index(["quartier_id", "cmhc_neighbourhood"])
    assert bool(d.loc[("02", "N2"), "folded"]) and pd.isna(d.loc[("02", "N2"), "share"])
    assert d.loc[("02", "N2"), "raw_share"] == pytest.approx(0.4)
    assert d.loc[("02", "N1"), "share"] == pytest.approx(1)


def test_derive_shares_refuses_unmapped_or_suppressed_tracts():
    with pytest.raises(ValueError, match="no CMHC neighbourhood"):
        crosswalk.derive_shares(HOMES, TRACT_MAP.iloc[:2], UNIVERSE["tract"])
    t = UNIVERSE["tract"].copy()
    t.loc[(t["area"] == "0003.00") & (t["unit"] == "total"), "units"] = pd.NA
    with pytest.raises(ValueError, match="suppressed unit total"):
        crosswalk.derive_shares(HOMES, TRACT_MAP, t)


def test_verify_accepts_a_map_the_counts_confirm(tmp_path):
    r = _verify(tmp_path)
    assert crosswalk.problems(r) == []
    q = r["quartiers"].set_index(["quartier_id", "cmhc_neighbourhood"])
    assert q["derived_verified"].to_dict() == {
        ("01", "N1"): True,
        ("02", "N1"): True,
        ("02", "N2"): True,
        ("03", "N1"): False,  # no rental units: stays "high"
    }
    assert r["zones"]["derived_verified"].all()


@pytest.mark.parametrize(
    "q, z, match",
    [
        # share off by more than rounding
        (GOOD_Q.replace("0.6,", "0.7,").replace("0.4,", "0.3,"), GOOD_Z, "share differs"),
        # a part of quartier 02 left out
        ("01,A,N1,1,verified,\n02,B,N1,1,verified,\n03,C,N1,1,high,\n", GOOD_Z, "part missing"),
        # a part where the quartier has no rental units
        (GOOD_Q.replace("01,A,N1,1,", "01,A,N1,0.5,") + "01,A,N2,0.5,high,\n", GOOD_Z,
         "no rental units there"),
        # claims verified without units to check
        (GOOD_Q.replace("03,C,N1,1,high", "03,C,N1,1,verified"), GOOD_Z, "don't confirm"),
    ],
)  # fmt: skip
def test_verify_flags_rows_the_counts_dont_support(tmp_path, q, z, match):
    bad = crosswalk.problems(_verify(tmp_path, q, z))
    assert any(match in b for b in bad), bad


def test_verify_flags_tract_and_zone_sums_that_disagree(tmp_path):
    u = dict(UNIVERSE)
    u["neighbourhood"] = _units(
        {"N1": {"studio": 12, "total": 181}, "N2": {"studio": 5, "total": 40}}
    )
    bad = crosswalk.problems(_verify(tmp_path, universe=u))
    # N1 no longer confirmed -> every N1 row that says verified is flagged; the zone too
    assert "quartier 01 -> N1: says verified, the counts don't confirm it" in bad
    assert "N1 -> zone Z: says verified, the counts don't confirm it" in bad


def test_verify_refuses_a_tract_the_census_doesnt_know(tmp_path):
    qm = crosswalk.load_quartier_map(_csv(tmp_path, "q.csv", Q_HEAD + GOOD_Q))
    zm = crosswalk.load_zone_map(_csv(tmp_path, "z.csv", Z_HEAD + GOOD_Z))
    with pytest.raises(ValueError, match=r"not in the census file: \['0003.00'\]"):
        crosswalk.verify(qm, zm, TRACT_MAP, UNIVERSE, HOMES, CENSUS_TRACTS - {"0003.00"})


def test_verify_reports_units_no_quartier_gets(tmp_path):
    r = _verify(tmp_path)
    assert r["unallocated"].empty and r["unallocated_share"] == 0
    # homes in 0009.00 (absent from the export) out of all homes in quartiers
    assert r["homes_without_units_share"] == pytest.approx(110 / 710)

    # Tract 0003.00 loses its homes (e.g. built after the census): its 40 units go nowhere.
    homes = HOMES[HOMES["ct_name"] != "0003.00"]
    q = "01,A,N1,1,verified,\n02,B,N1,1,verified,\n03,C,N1,1,high,\n"
    r = _verify(tmp_path, q=q, homes=homes)
    assert r["unallocated"]["ct_name"].tolist() == ["0003.00"]
    assert r["unallocated_share"] == pytest.approx(40 / 220)
    assert crosswalk.problems(r, max_unallocated=0.5) == []
    bad = crosswalk.problems(r, max_unallocated=0.1)
    assert len(bad) == 1 and "no census home" in bad[0]


def test_load_tract_map_refuses(tmp_path):
    with pytest.raises(ValueError, match="not like"):
        crosswalk.load_tract_map(_csv(tmp_path, "t.csv", "ct_name,cmhc_neighbourhood\n12.01,N\n"))
    dup = "ct_name,cmhc_neighbourhood\n0001.00,N\n0001.00,M\n"
    with pytest.raises(ValueError, match="twice"):
        crosswalk.load_tract_map(_csv(tmp_path, "t.csv", dup))
    t = crosswalk.load_tract_map(_csv(tmp_path, "t.csv", "ct_name,cmhc_neighbourhood\n0001.00,N\n"))
    assert t["ct_name"].tolist() == ["0001.00"]  # stays text


# --- the committed crosswalk against the real files ---------------------------------

REAL_INPUTS = [
    *config.CMHC_RENT_CSV.values(),
    *config.CMHC_UNIVERSE_CSV.values(),
    config.STATCAN_GAF_ZIP,
    config.QUARTIERS_GEOJSON,
    config.LOGEMENTS_CSV,
]


@pytest.mark.skipif(
    not all(p.exists() for p in REAL_INPUTS), reason="raw CMHC / StatCan / city files absent"
)
def test_committed_crosswalk_is_confirmed_by_the_unit_counts():
    from mtlhousing import boundaries, cmhc_universe, export, sample_points

    cmhc = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    universe = cmhc_universe.load(config.CMHC_UNIVERSE_CSV, config.CMHC_RMS_PERIOD)
    qm = crosswalk.load_quartier_map(config.QUARTIER_TO_CMHC_CSV)
    zm = crosswalk.load_zone_map(config.CMHC_NBHD_TO_ZONE_CSV)
    tm = crosswalk.load_tract_map(config.TRACT_TO_CMHC_CSV)
    crosswalk.check(qm, zm, crosswalk.quartier_table(export.NEIGHBOURHOODS_GEOJSON), cmhc)
    assert crosswalk.zone_bounds(zm, cmhc)["inside"].all()

    gaf = sample_points.extract_gaf()
    homes = crosswalk.tract_homes(sample_points.da_points(gaf), boundaries.load_quartiers())
    report = crosswalk.verify(qm, zm, tm, universe, homes, set(gaf["ct_name"].dropna()))
    assert crosswalk.problems(report) == []  # includes the unallocated-units limit
    # Every neighbourhood and zone used is confirmed, not just consistent.
    nb = crosswalk.confirmed(report["neighbourhood_sums"], "cmhc_neighbourhood")
    assert nb == set(tm["cmhc_neighbourhood"]) == set(zm["cmhc_neighbourhood"])
    assert crosswalk.confirmed(report["zone_sums"], "cmhc_zone") == set(zm["cmhc_zone"])
    # The one row the counts can't check is the owner-reviewed name match.
    unchecked = report["quartiers"][~report["quartiers"]["derived_verified"]]
    assert unchecked[["quartier_id", "confidence"]].values.tolist() == [["88", "high"]]
