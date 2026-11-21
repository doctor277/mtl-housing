import pandas as pd
import pytest

from mtlhousing import cmhc_rent, config

PERIOD = "October 2025"
HEAD = ",Studio,,1 Bedroom,,2 Bedroom,,3 Bedroom +,,Total,,"
NOTES = [
    "",
    "Notes",
    '"The following letter codes are used ... a — Excellent, b — Very good"',
    "Source,CMHC Rental Market Survey",
]
CMA = 'Montréal,"1,005",a ,"1,131",a ,"1,346",a ,"1,625",a ,"1,291",a ,'


def _write(path, level="Neighbourhood", period=PERIOD, rows=None, cma=CMA):
    rows = rows or [
        'Côte-des-Neiges,960,b ,"1,123",b ,"1,349",b ,"1,872",d ,"1,227",b ,',
        'Outremont,**,,"1,563",d ,**,,**,,**,,',
    ]
    lines = [
        f"Montréal — Average Rent by Bedroom Type by {level}",
        f"{period} Row / Apartment",
        HEAD,
        *rows,
        *([cma] if cma else []),
        *NOTES,
    ]
    path.write_bytes("\r\n".join(lines).encode("cp1252"))
    return path


def test_parses_rents_grades_and_suppression(tmp_path):
    areas, cma = cmhc_rent.read_hmip_table(_write(tmp_path / "n.csv"), "neighbourhood", PERIOD)
    a = areas.set_index(["area", "unit"])
    assert a.loc[("Côte-des-Neiges", "1br"), "rent"] == 1123
    assert a.loc[("Côte-des-Neiges", "1br"), "grade"] == "b"
    assert bool(a.loc[("Côte-des-Neiges", "1br"), "usable"])
    # grade d is kept but not usable
    assert a.loc[("Côte-des-Neiges", "3br_plus"), "grade"] == "d"
    assert not bool(a.loc[("Côte-des-Neiges", "3br_plus"), "usable"])
    # ** -> no rent, no grade, not usable
    o = a.loc[("Outremont", "studio")]
    assert pd.isna(o["rent"]) and pd.isna(o["grade"]) and not bool(o["usable"])
    assert set(areas["area"]) == {"Côte-des-Neiges", "Outremont"}
    assert cma.set_index("unit").loc["2br", "rent"] == 1346


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"level": "Zone"}, "title is"),
        ({"period": "October 2024"}, "period line"),
        ({"cma": None}, "CMA total"),
        ({"rows": ['X,900,,"1,000",a ,1,a ,1,a ,1,a ,']}, "grade ''"),
        ({"rows": ['X,**,a ,"1,000",a ,1,a ,1,a ,1,a ,']}, "suppressed value with grade"),
        ({"rows": ["X,1,a ,1,a ,1,a ,1,a ,1,a ,", "X,1,a ,1,a ,1,a ,1,a ,1,a ,"]}, "duplicate"),
        ({"cma": 'Montréal,**,,"1,131",a ,"1,346",a ,"1,625",a ,"1,291",a ,'}, "not usable"),
    ],
)
def test_refuses_unexpected_files(tmp_path, kwargs, match):
    with pytest.raises(ValueError, match=match):
        cmhc_rent.read_hmip_table(_write(tmp_path / "n.csv", **kwargs), "neighbourhood", PERIOD)


def test_load_checks_both_levels_share_the_cma_total(tmp_path):
    paths = {
        "neighbourhood": _write(tmp_path / "n.csv"),
        "zone": _write(tmp_path / "z.csv", level="Zone"),
    }
    tables = cmhc_rent.load(paths, PERIOD)
    assert set(tables) == {"neighbourhood", "zone", "cma"}
    paths["zone"] = _write(
        tmp_path / "z2.csv",
        level="Zone",
        cma='Montréal,"1,006",a ,"1,131",a ,"1,346",a ,"1,625",a ,"1,291",a ,',
    )
    with pytest.raises(ValueError, match="different CMA totals"):
        cmhc_rent.load(paths, PERIOD)


@pytest.mark.skipif(
    not all(p.exists() for p in config.CMHC_RENT_CSV.values()), reason="raw CMHC exports absent"
)
def test_real_exports():
    t = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    n, z = t["neighbourhood"], t["zone"]
    assert n["area"].nunique() > 100 and z["area"].nunique() > 30
    assert {"Côte-des-Neiges", "Westmount", "Plateau-Mont-Royal"} <= set(n["area"])
    assert t["cma"].set_index("unit").loc["1br", "rent"] == 1131
