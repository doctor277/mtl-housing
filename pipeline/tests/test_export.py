import json
import math

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import MultiPolygon, Point, box

from mtlhousing import aggregate, config, export

INF = math.inf
RG, JB = "udem_roger_gaudry", "udem_jean_brillant"


def test_time_value_maps_inf_and_nan_to_none():
    assert export.time_value(32.24) == 32.2
    assert export.time_value(INF) is None
    assert export.time_value(float("nan")) is None


def test_time_block_lists_over_max_stats_only():
    b = export.time_block(pd.Series({"median": 40.0, "p10": 30.0, "p90": INF}))
    assert b == {"median": 40.0, "p10": 30.0, "p90": None, "over_max": ["p90"]}
    # NaN = no data: null but NOT over max
    b = export.time_block(pd.Series({"median": float("nan"), "p10": 1.0, "p90": 2.0}))
    assert b["median"] is None and b["over_max"] == []


def _stats(qid, fastest, rg, jb, flags=()):
    def row(target, med, p10, p90, n_unr=0, share=float("nan")):
        return {
            "quartier_id": qid, "campus_id": "udem", "target": target,
            "median": med, "p10": p10, "p90": p90, "n_points": 10, "n_unreachable": n_unr,
            "unreachable_share": n_unr / 10, "fastest_share": share, "flags": list(flags),
        }  # fmt: skip

    return pd.DataFrame(
        [row("fastest", *fastest), row(RG, *rg, share=0.7), row(JB, *jb, share=0.3)],
        columns=aggregate.STAT_COLUMNS,
    )


ROUTING_META = {
    "n_origins": 2,
    "computed_at": "2026-11-20T01:56:11",
    "percentile": 50,
    "speed_walking_kmh": config.WALK_SPEED_KMH,
    "transport_modes": ["TRANSIT", "WALK"],
    "gtfs_feeds": [{"name": "stm", "version": "x", "start": "2026-08-24", "end": "2027-01-03"}],
    "osm_timestamp": "2026-11-19T21:22:20Z",
    "r5py_version": "1.1.7",
}


def _commute():
    stats = pd.concat(
        [
            _stats("01", (20.0, 15.0, 30.0), (22.2, 17.2, 32.2), (25.0, 18.0, 40.0)),
            _stats(
                "02", (90.0, 60.0, INF), (92.2, 62.2, INF), (95.0, 61.0, INF), ["many_unreachable"]
            ),
        ]
    )
    return export.build_commute({"udem": stats}, {"udem": ROUTING_META}, ["01", "02", "03"])


def test_build_commute_shape_and_values():
    c = _commute()
    r = c["results"]
    assert set(r) == {"01", "02", "03"}
    assert r["03"] == {}  # quartier without results still present, explicitly empty
    u = r["01"]["udem"]
    assert u["median"] == 20.0 and u["rule"] == "fastest_destination"
    assert set(u["by_destination"]) == {RG, JB}
    assert u["by_destination"][RG]["median"] == 22.2
    assert u["by_destination"][JB]["fastest_share"] == 0.3
    far = r["02"]["udem"]
    assert far["p90"] is None and far["over_max"] == ["p90"]
    assert far["flags"] == ["many_unreachable"]
    assert far["by_destination"][JB]["over_max"] == ["p90"]


def test_meta_records_method_and_adjustments():
    m = _commute()["meta"]
    assert m["analysis_date"] == config.ANALYSIS_DATE.isoformat()
    assert m["departure_window"] == {"start": "07:30", "minutes": 60}
    assert m["max_trip_min"] == config.MAX_TRIP_MIN
    dests = {d["id"]: d for d in m["campuses"]["udem"]["destinations"]}
    assert dests[RG]["access_adjustment_min"] == config.ACCESS_ADJUSTMENT_MIN[RG]
    assert dests[JB]["access_adjustment_min"] == config.ACCESS_ADJUSTMENT_MIN[JB]
    assert m["walk_speed_kmh"] == config.WALK_SPEED_KMH
    assert m["out_of_scope"][0]["area"] == "L'Île-Dorval"


def test_available_campuses_needs_stats_and_routing_meta(tmp_path):
    # Exporting after one campus's run must keep every other campus that has results.
    for c in ("udem", "mcgill"):
        export.stats_parquet(c, tmp_path).write_bytes(b"x")
    (tmp_path / config.travel_times_meta("udem").name).write_text("{}")
    have, missing = export.available_campuses(tmp_path)
    assert have == ["udem"]  # mcgill has stats but no routing meta
    assert missing == [c for c in config.CAMPUSES if c != "udem"]
    (tmp_path / config.travel_times_meta("mcgill").name).write_text("{}")
    assert export.available_campuses(tmp_path)[0] == ["udem", "mcgill"]


def test_run_refuses_when_no_campus_has_results():
    with pytest.raises(ValueError, match="no campus"):
        export.run([])


def test_write_json_is_strict(tmp_path):
    p = export.write_json(_commute(), tmp_path / "c.json")
    text = p.read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text and "\r\n" not in text
    with pytest.raises(ValueError):
        export.write_json({"x": float("nan")}, tmp_path / "bad.json")


def test_neighbourhoods_geojson_keeps_shared_edges(tmp_path):
    # two adjacent squares (metric CRS) sharing an edge
    metric = gpd.GeoDataFrame(
        {
            "id": ["01", "02"],
            "name": ["A", "B"],
            "borough": ["X", "X"],
            "municipality": ["Montréal", "Montréal"],
            "dwellings": [10, 20],
        },
        geometry=[box(300000, 5040000, 301000, 5041000), box(301000, 5040000, 302000, 5041000)],
        crs=config.CRS_METRIC,
    )
    path = export.write_neighbourhoods(metric.to_crs(config.CRS_WGS84), tmp_path / "n.geojson")
    gj = json.loads(path.read_text(encoding="utf-8"))
    assert [f["properties"]["id"] for f in gj["features"]] == ["01", "02"]
    assert set(gj["features"][0]["properties"]) == {
        "id", "name", "borough", "municipality", "dwellings"
    }  # fmt: skip
    back = gpd.read_file(path).to_crs(config.CRS_METRIC)
    assert back.geometry.is_valid.all()
    # no gap or overlap introduced: union area ~ sum of areas
    assert back.union_all().area == pytest.approx(back.area.sum(), rel=1e-6)


def _islands():
    """Quartier '01' = mainland square + one island; '02' = adjacent square (WGS84)."""
    sq = box(-73.60, 45.50, -73.59, 45.51)
    island = box(-73.57, 45.50, -73.565, 45.505)
    return gpd.GeoDataFrame(
        {"id": ["01", "02"], "name": ["A", "B"], "borough": ["X", "X"],
         "municipality": ["M", "M"], "dwellings": [10, 20]},
        geometry=[MultiPolygon([sq, island]), box(-73.59, 45.50, -73.58, 45.51)],
        crs=config.CRS_WGS84,
    )  # fmt: skip


AREA = config.NoResidentArea(
    id="01-park", quartier_id="01", name="Park", points=((45.502, -73.567),), note=""
)


def _homes(*lonlat):
    return gpd.GeoDataFrame(
        {"point_id": [f"h{i}" for i in range(len(lonlat))]},
        geometry=[Point(x, y) for x, y in lonlat],
        crs=config.CRS_WGS84,
    )


def test_no_resident_part_is_cut_out_of_its_quartier():
    out = export.split_no_resident_areas(_islands(), _homes((-73.595, 45.505)), [AREA])
    by_id = out.set_index("id")
    assert list(out["id"]) == ["01", "02", "01-park"]
    assert by_id.loc["01", "geometry"].geom_type == "Polygon"
    park = by_id.loc["01-park"]
    assert bool(park["no_residents"]) and park["part_of"] == "01" and park["dwellings"] == 0
    assert park["geometry"].contains(Point(-73.567, 45.502))
    assert not bool(by_id.loc["01", "no_residents"])


def test_no_resident_part_refuses_homes_or_missing_part():
    with pytest.raises(ValueError, match="homes inside"):
        export.split_no_resident_areas(_islands(), _homes((-73.567, 45.502)), [AREA])
    lost = config.NoResidentArea(
        id="x", quartier_id="01", name="x", points=((45.0, -73.0),), note=""
    )
    with pytest.raises(ValueError, match="separate parts"):
        export.split_no_resident_areas(_islands(), _homes(), [lost])


# --- the real exported files ------------------------------------------------------------

real = pytest.mark.skipif(not export.COMMUTE_JSON.exists(), reason="run export first")


@real
def test_real_files_match_and_are_small():
    c = json.loads(export.COMMUTE_JSON.read_text(encoding="utf-8"))
    gj = json.loads(export.NEIGHBOURHOODS_GEOJSON.read_text(encoding="utf-8"))
    feats = gj["features"]
    ids = {f["properties"]["id"] for f in feats if not f["properties"]["no_residents"]}
    assert ids == set(c["results"]) and len(ids) == 91
    no_res = {
        f["properties"]["id"]: f["properties"] for f in feats if f["properties"]["no_residents"]
    }
    assert set(no_res) == {a.id for a in config.NO_RESIDENT_AREAS}
    assert all(p["dwellings"] == 0 and p["part_of"] in ids for p in no_res.values())
    assert export.NEIGHBOURHOODS_GEOJSON.stat().st_size < 1_000_000
    for qid, r in c["results"].items():
        u = r["udem"]
        assert set(u["by_destination"]) == {RG, JB}, qid
        for s in ("median", "p10", "p90"):
            assert u[s] is not None or s in u["over_max"], (qid, s)
        assert (
            u["median"] is None
            or u["median"] <= u["by_destination"][RG]["median"]
            or (u["by_destination"][RG]["median"] is None)
        )
