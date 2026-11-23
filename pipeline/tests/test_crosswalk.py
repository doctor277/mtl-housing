import json

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


# --- the committed crosswalk against the real files ---------------------------------


@pytest.mark.skipif(
    not all(p.exists() for p in config.CMHC_RENT_CSV.values()), reason="raw CMHC exports absent"
)
def test_committed_crosswalk_is_consistent():
    cmhc = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    qm = crosswalk.load_quartier_map(config.QUARTIER_TO_CMHC_CSV)
    zm = crosswalk.load_zone_map(config.CMHC_NBHD_TO_ZONE_CSV)
    gj = json.loads((config.WEB_DATA_DIR / "neighbourhoods.geojson").read_text(encoding="utf-8"))
    quartiers = pd.DataFrame([f["properties"] for f in gj["features"]])
    crosswalk.check(qm, zm, quartiers, cmhc)
    assert crosswalk.zone_bounds(zm, cmhc)["inside"].all()
