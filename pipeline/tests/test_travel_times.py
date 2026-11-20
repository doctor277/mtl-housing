import json

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from mtlhousing import config, travel_times


def test_destinations_for_udem_are_both_buildings():
    d = travel_times.destinations_gdf("udem")
    assert d["id"].tolist() == ["udem_roger_gaudry", "udem_jean_brillant"]
    assert (d["campus_id"] == "udem").all() and d.crs.equals(config.CRS_WGS84)


def test_origins_require_unique_ids():
    pts = gpd.GeoDataFrame(
        {"point_id": ["da:1", "da:1"]}, geometry=[Point(0, 0), Point(1, 1)], crs=4326
    )
    with pytest.raises(ValueError, match="unique"):
        travel_times.origins_gdf(pts)


def test_origins_exclude_out_of_scope_points():
    pts = gpd.GeoDataFrame(
        {"point_id": ["da:1", "da:2"], "in_scope": [True, False]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs=4326,
    )
    assert travel_times.origins_gdf(pts)["id"].tolist() == ["da:1"]


def test_complete_matrix_fills_dropped_pairs_with_nan():
    ttm = pd.DataFrame(
        {"from_id": ["a", "a", "b"], "to_id": ["x", "y", "x"], "travel_time": [10, np.nan, 20]}
    )
    out = travel_times.complete_matrix(ttm, ["a", "b", "c"], ["x", "y"])
    assert list(out.columns) == travel_times.RESULT_COLUMNS
    assert len(out) == 6
    t = out.set_index(["point_id", "destination_id"])["travel_time_min"]
    assert t[("a", "x")] == 10 and t[("b", "x")] == 20
    assert np.isnan(t[("a", "y")])  # unreachable stays NaN
    assert np.isnan(t[("c", "x")]) and np.isnan(t[("c", "y")])  # dropped origin -> NaN


def test_complete_matrix_rejects_duplicates():
    ttm = pd.DataFrame({"from_id": ["a", "a"], "to_id": ["x", "x"], "travel_time": [1, 2]})
    with pytest.raises(ValueError, match="duplicate"):
        travel_times.complete_matrix(ttm, ["a"], ["x"])


def test_passes_near_uses_metres():
    # ~111 m per 0.001 degree of latitude
    route = LineString([(-73.6, 45.500), (-73.6, 45.510)])
    assert travel_times.passes_near(route, 45.505, -73.6001, metres=15)  # ~8 m away
    assert not travel_times.passes_near(route, 45.505, -73.599, metres=15)  # ~78 m away


# --- Repair helpers -------------------------------------------------------------------


def test_osm_tag_parses_gdal_other_tags():
    tags = '"access"=>"private","foot"=>"use_sidepath","name"=>"Rue \'X\'"'
    assert travel_times.osm_tag(tags, "access") == "private"
    assert travel_times.osm_tag(tags, "foot") == "use_sidepath"
    assert travel_times.osm_tag(tags, "bicycle") is None
    assert travel_times.osm_tag(None, "access") is None


def _lines(rows):
    return gpd.GeoDataFrame(
        {"highway": [r[0] for r in rows], "other_tags": [r[1] for r in rows]},
        geometry=[r[2] for r in rows],
        crs=config.CRS_WGS84,
    )


def test_public_walkable_drops_private_and_motorways():
    seg = LineString([(-73.6, 45.5), (-73.6, 45.501)])
    lines = _lines(
        [
            ("footway", '"access"=>"private"', seg),
            ("footway", '"foot"=>"no"', seg),
            ("motorway", None, seg),
            ("residential", '"foot"=>"use_sidepath"', seg),
            (None, None, seg),  # not a highway (e.g. a fence)
            ("footway", None, seg),
        ]
    )
    kept = travel_times.public_walkable(lines)
    assert kept["highway"].tolist() == ["residential", "footway"]


def test_nearest_point_on_returns_projection_and_metres():
    lines = _lines([("footway", None, LineString([(-73.6, 45.500), (-73.6, 45.510)]))])
    pt, metres = travel_times.nearest_point_on(lines, Point(-73.599, 45.505))
    assert pt.x == pytest.approx(-73.6, abs=1e-6) and pt.y == pytest.approx(45.505, abs=1e-5)
    assert 70 < metres < 85  # 0.001 deg of longitude at 45.5 N is ~78 m
    assert travel_times.nearest_point_on(lines.iloc[0:0], Point(0, 0)) is None


def test_stuck_origins_only_those_reaching_nothing_and_not_yet_moved():
    times = pd.DataFrame(
        {
            "point_id": ["a", "a", "b", "b", "c", "c"],
            "destination_id": ["x", "y"] * 3,
            "travel_time_min": [np.nan, np.nan, np.nan, 30, np.nan, np.nan],
            "origin_moved_m": [np.nan, np.nan, np.nan, np.nan, 12.0, 12.0],
        }
    )
    # a: reaches nothing -> stuck; b: reaches y -> fine; c: already relocated -> skip
    assert travel_times.stuck_origins(times) == ["a"]


# --- Output of the real run (skipped until `travel-times --campus udem` has run) -----

out_path = config.travel_times_parquet("udem")
real = pytest.mark.skipif(not out_path.exists(), reason="run `travel-times --campus udem` first")


@real
def test_real_udem_output_is_complete_and_plausible():
    times = pd.read_parquet(out_path)
    meta = json.loads(config.travel_times_meta("udem").read_text(encoding="utf-8"))
    sample = gpd.read_parquet(config.SAMPLE_POINTS_PARQUET)

    in_scope = sample[sample["in_scope"]]
    assert len(times) == len(in_scope) * 2 == meta["n_pairs"]
    assert set(times["point_id"]) == set(in_scope["point_id"])
    assert [e["point_id"] for e in meta["excluded_out_of_scope"]] == ["da:24663396"]
    assert set(times["destination_id"]) == {"udem_roger_gaudry", "udem_jean_brillant"}
    t = times["travel_time_min"]
    assert t.isna().mean() < 0.02  # almost every home on the island reaches UdeM in 2 h
    assert (t.dropna() > 0).all() and t.max() <= 120
    assert meta["departure"] == config.analysis_departure().isoformat()
    # The Île-des-Soeurs condo DA (private footways) is repaired and reachable.
    ids = times[times["point_id"] == "da:24663254"]
    assert ids["travel_time_min"].notna().all() and (ids["origin_moved_m"] < 300).all()
