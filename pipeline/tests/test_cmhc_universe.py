import pytest

from mtlhousing import cmhc_universe, config

PERIOD = "October 2025"
HEAD = ",Studio,1 Bedroom,2 Bedroom,3 Bedroom +,Total,"
NOTES = ["", "Notes", "** — Data suppressed", "Source,CMHC Rental Market Survey"]
CMA = 'Montréal,"50,806","176,672","363,004","78,352","668,834",'


def _write(path, level="Census Tract", period=PERIOD, rows=None, cma=CMA):
    rows = rows or ["0012.01,22,104,386,169,681,", "0014.02,6,3,18,**,27,"]
    lines = [
        f"Montréal — Universe by Bedroom Type by {level}",
        f"{period} Row / Apartment",
        HEAD,
        *rows,
        *([cma] if cma else []),
        *NOTES,
    ]
    path.write_bytes("\r\n".join(lines).encode("cp1252"))
    return path


def test_parses_counts_thousands_and_suppression(tmp_path):
    areas, cma = cmhc_universe.read_universe_table(_write(tmp_path / "t.csv"), "tract", PERIOD)
    a = areas.set_index(["area", "unit"])["units"]
    assert a[("0012.01", "2br")] == 386
    assert a[("0012.01", "total")] == 681
    assert a.isna().sum() == 1 and a.isna()[("0014.02", "3br_plus")]
    assert areas["area"].unique().tolist() == ["0012.01", "0014.02"]  # tract names stay text
    assert cma.set_index("unit").loc["total", "units"] == 668834


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"level": "Zone"}, "title is"),
        ({"period": "October 2024"}, "period line"),
        ({"cma": None}, "CMA total"),
        ({"rows": ["X,1,2,3,4,n/a,"]}, "not a number"),
        ({"rows": ["X,1,2,3,4,10,", "X,1,2,3,4,10,"]}, "duplicate"),
        ({"rows": ["X,1,2,3,4,10"]}, "fields"),
        ({"cma": "Montréal,1,2,3,4,**,"}, "suppressed"),
    ],
)
def test_refuses_unexpected_files(tmp_path, kwargs, match):
    with pytest.raises(ValueError, match=match):
        cmhc_universe.read_universe_table(_write(tmp_path / "t.csv", **kwargs), "tract", PERIOD)


def test_load_checks_the_three_levels_share_the_cma_total(tmp_path):
    paths = {
        "zone": _write(tmp_path / "z.csv", level="Zone"),
        "neighbourhood": _write(tmp_path / "n.csv", level="Neighbourhood"),
        "tract": _write(tmp_path / "t.csv"),
    }
    assert set(cmhc_universe.load(paths, PERIOD)) == {"zone", "neighbourhood", "tract", "cma"}
    paths["tract"] = _write(tmp_path / "t2.csv", cma='Montréal,1,2,3,4,"668,835",')
    with pytest.raises(ValueError, match="different CMA totals"):
        cmhc_universe.load(paths, PERIOD)


@pytest.mark.skipif(
    not all(p.exists() for p in config.CMHC_UNIVERSE_CSV.values()),
    reason="raw CMHC universe exports absent",
)
def test_real_universe_exports():
    u = cmhc_universe.load(config.CMHC_UNIVERSE_CSV, config.CMHC_RMS_PERIOD)
    assert {k: u[k]["area"].nunique() for k in ("zone", "neighbourhood", "tract")} == {
        "zone": 39,
        "neighbourhood": 110,
        "tract": 946,
    }
    assert u["cma"].set_index("unit").loc["total", "units"] == 668834
    # Zones and neighbourhoods partition the CMA: their totals add up to it.
    for level in ("zone", "neighbourhood"):
        total = u[level][u[level]["unit"] == "total"]["units"]
        assert total.notna().all() and total.sum() == 668834
