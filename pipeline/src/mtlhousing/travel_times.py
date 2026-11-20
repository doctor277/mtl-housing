"""Transit travel times from residential sample points to campus buildings (r5py / R5).

For every sample point and every destination building of a campus, R5 computes the
door-to-door transit + walk time for each departure minute in the window
(config.DEPARTURE_WINDOW from config.analysis_departure()), and we keep the median
(50th percentile). Unreachable within R5's max trip time -> NaN, never 0.

r5py is imported lazily via mtlhousing.r5py_setup so the JVM memory cap applies and
the pure helpers here can be tested without starting Java.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiLineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge

from mtlhousing import config

RESULT_COLUMNS = ["point_id", "destination_id", "travel_time_min"]
# Highway types pedestrians may not use, and access values that block them.
NOT_WALKABLE = {"motorway", "motorway_link", "trunk", "trunk_link", "construction", "proposed"}
BLOCKED = {"private", "no"}
RELOCATE_RADIUS_M = 300


def destinations_gdf(campus_id: str) -> gpd.GeoDataFrame:
    campus = config.CAMPUSES[campus_id]
    return gpd.GeoDataFrame(
        {"id": [d.id for d in campus.destinations], "campus_id": campus_id},
        geometry=[Point(d.lon, d.lat) for d in campus.destinations],
        crs=config.CRS_WGS84,
    )


def origins_gdf(sample_points: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Routing origins: in-scope sample points only (see config.OUT_OF_SCOPE_CSDS)."""
    if not sample_points["point_id"].is_unique:
        raise ValueError("sample point ids must be unique")
    if "in_scope" in sample_points:
        sample_points = sample_points[sample_points["in_scope"].astype(bool)]
    return gpd.GeoDataFrame(
        {"id": sample_points["point_id"].values},
        geometry=sample_points.geometry.values,
        crs=config.CRS_WGS84,
    )


def complete_matrix(ttm: pd.DataFrame, origin_ids, destination_ids) -> pd.DataFrame:
    """One row per (origin, destination). Pairs r5py dropped (e.g. unsnappable
    origins) come back as NaN so they are counted as unreachable, not lost."""
    full = pd.MultiIndex.from_product(
        [list(origin_ids), list(destination_ids)], names=["point_id", "destination_id"]
    )
    times = (
        ttm.rename(columns={"from_id": "point_id", "to_id": "destination_id"})
        .set_index(["point_id", "destination_id"])["travel_time"]
        .astype(float)
    )
    if times.index.duplicated().any():
        raise ValueError("duplicate (origin, destination) pairs in r5py output")
    return times.reindex(full).rename("travel_time_min").reset_index()[RESULT_COLUMNS]


def build_network(r5py):
    """Street network (clipped OSM) + all GTFS feeds. r5py caches the built network."""
    gtfs = [str(p) for p in config.GTFS_FEEDS.values()]
    return r5py.TransportNetwork(str(config.OSM_CLIPPED_PBF), gtfs)


def routing_kwargs(r5py) -> dict:
    """The R5 settings of the main run. Shared with validation so both route alike."""
    return {
        "departure": config.analysis_departure(),
        "departure_time_window": config.DEPARTURE_WINDOW,
        "transport_modes": [r5py.TransportMode.TRANSIT, r5py.TransportMode.WALK],
        "speed_walking": config.WALK_SPEED_KMH,
        "snap_to_network": True,
    }


def compute_travel_times(network, r5py, origins, destinations) -> pd.DataFrame:
    ttm = r5py.TravelTimeMatrix(
        network,
        origins=origins,
        destinations=destinations,
        percentiles=[50],
        **routing_kwargs(r5py),
    )
    return complete_matrix(pd.DataFrame(ttm), origins["id"], destinations["id"])


def run_campus(campus_id: str, repair_only: bool = False) -> tuple[pd.DataFrame, dict]:
    """Compute (or, with repair_only, reload) travel times for one campus, then repair
    origins that reach no destination. Writes parquet + JSON metadata."""
    from mtlhousing.r5py_setup import import_r5py

    r5py = import_r5py()
    sample = gpd.read_parquet(config.SAMPLE_POINTS_PARQUET)
    origins, destinations = origins_gdf(sample), destinations_gdf(campus_id)

    t0 = time.time()
    network = build_network(r5py)
    t_net = time.time() - t0
    if repair_only:
        times = pd.read_parquet(config.travel_times_parquet(campus_id))
        meta = json.loads(config.travel_times_meta(campus_id).read_text(encoding="utf-8"))
        # Drop origins that are no longer routed (e.g. newly marked out of scope).
        times = times[times["point_id"].isin(origins["id"])].reset_index(drop=True)
        meta["n_origins"] = len(origins)
    else:
        times = compute_travel_times(network, r5py, origins, destinations)
        times["origin_moved_m"] = float("nan")
        meta = _base_meta(campus_id, r5py, origins, destinations)
        meta["seconds_network"] = round(t_net)
        meta["seconds_routing"] = round(time.time() - t0 - t_net)

    times, repaired = repair_unreachable(times, origins, destinations, network, r5py)
    meta["relocated_origins"] = [
        r
        for r in meta.get("relocated_origins", []) + repaired
        if r["point_id"] in set(origins["id"])
    ]
    out = sample[~sample["point_id"].isin(origins["id"])]
    meta["excluded_out_of_scope"] = [
        {"point_id": r.point_id, "reason": r.scope_note} for r in out.itertuples()
    ]
    meta["n_pairs"] = len(times)
    meta["n_unreachable_pairs"] = int(times["travel_time_min"].isna().sum())

    times.to_parquet(config.travel_times_parquet(campus_id), index=False)
    config.travel_times_meta(campus_id).write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return times, meta


def _base_meta(campus_id, r5py, origins, destinations) -> dict:
    from mtlhousing import gtfs_check

    feeds = []
    for name, path in config.GTFS_FEEDS.items():
        f = gtfs_check.load_feed(path, name)
        start, end = gtfs_check.service_range(f)
        version = (f.feed_info or {}).get("feed_version")
        feeds.append({"name": name, "version": version, "start": str(start), "end": str(end)})
    osm_meta = json.loads(config.OSM_CLIPPED_META.read_text(encoding="utf-8"))
    return {
        "campus_id": campus_id,
        "destinations": destinations["id"].tolist(),
        "n_origins": len(origins),
        "departure": config.analysis_departure().isoformat(),
        "departure_window_min": config.DEPARTURE_WINDOW.total_seconds() / 60,
        "percentile": 50,
        "speed_walking_kmh": config.WALK_SPEED_KMH,
        "transport_modes": ["TRANSIT", "WALK"],
        "gtfs_feeds": feeds,
        "osm_timestamp": osm_meta.get("osm_timestamp"),
        "r5py_version": r5py.__version__,
        "computed_at": datetime.now().isoformat(timespec="seconds"),
    }


# --- Repair: origins stuck on private paths -----------------------------------------
# Some census points sit inside private complexes (e.g. condo grounds on Île-des-Soeurs
# mapped as access=private footways). R5 snaps them onto the private path and then
# cannot walk out, so every destination is "unreachable". For those origins only, we
# move the start to the nearest PUBLIC walkable OSM way within RELOCATE_RADIUS_M and
# route again, recording how far the point moved.


def osm_tag(other_tags: str | None, key: str) -> str | None:
    """Value of `key` in GDAL's hstore-style other_tags string."""
    if not isinstance(other_tags, str):
        return None
    m = re.search(rf'"{re.escape(key)}"=>"([^"]*)"', other_tags)
    return m.group(1) if m else None


def public_walkable(lines: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """OSM lines a pedestrian may use: a highway, not motorway-like, not private/no."""
    tags = lines["other_tags"] if "other_tags" in lines else pd.Series(None, index=lines.index)
    ok = lines["highway"].notna() & ~lines["highway"].isin(NOT_WALKABLE)
    ok &= ~tags.map(lambda t: osm_tag(t, "access")).isin(BLOCKED)
    ok &= ~tags.map(lambda t: osm_tag(t, "foot")).isin(BLOCKED)
    return lines[ok]


def nearest_point_on(lines: gpd.GeoDataFrame, point: Point) -> tuple[Point, float] | None:
    """Closest point on `lines` to `point`, and the distance in metres (EPSG:4326 in/out)."""
    if lines.empty:
        return None
    metric = lines.to_crs(config.CRS_METRIC)
    p = gpd.GeoSeries([point], crs=config.CRS_WGS84).to_crs(config.CRS_METRIC).iloc[0]
    dist = metric.distance(p)
    line = metric.geometry.loc[dist.idxmin()]
    on = line.interpolate(line.project(p))
    on_wgs = gpd.GeoSeries([on], crs=config.CRS_METRIC).to_crs(config.CRS_WGS84).iloc[0]
    return on_wgs, float(dist.min())


def relocate_to_public_way(point: Point, radius_m: float = RELOCATE_RADIUS_M):
    """Read OSM lines around `point`; return (point on nearest public way, metres) or None."""
    dlat = radius_m / 111_000
    dlon = radius_m / 78_000  # ~ cos(45.5 deg) * 111 km
    bbox = (point.x - dlon, point.y - dlat, point.x + dlon, point.y + dlat)
    lines = gpd.read_file(config.OSM_CLIPPED_PBF, layer="lines", bbox=bbox)
    found = nearest_point_on(public_walkable(lines), point)
    return found if found and found[1] <= radius_m else None


def stuck_origins(times: pd.DataFrame) -> list[str]:
    """Origins that reach no destination and have not been relocated yet."""
    g = times.groupby("point_id")
    unreachable = g["travel_time_min"].apply(lambda s: s.isna().all())
    not_moved = g["origin_moved_m"].apply(lambda s: s.isna().all())
    return sorted(unreachable[unreachable & not_moved].index)


def repair_unreachable(times, origins, destinations, network, r5py):
    """Re-route origins that reach no destination from the nearest public way."""
    if "origin_moved_m" not in times:
        times = times.assign(origin_moved_m=float("nan"))
    report = []
    for pid in stuck_origins(times):
        point = origins.loc[origins["id"] == pid].geometry.iloc[0]
        found = relocate_to_public_way(point)
        entry = {"point_id": pid, "moved_m": None, "reachable_after": False}
        if found is not None:
            new_point, moved = found
            moved_origin = gpd.GeoDataFrame({"id": [pid]}, geometry=[new_point], crs=4326)
            redo = compute_travel_times(network, r5py, moved_origin, destinations)
            redo = redo.set_index("destination_id")["travel_time_min"]
            mask = times["point_id"] == pid
            times.loc[mask, "travel_time_min"] = times.loc[mask, "destination_id"].map(redo)
            times.loc[mask, "origin_moved_m"] = round(moved, 1)
            entry = {
                "point_id": pid,
                "moved_m": round(moved, 1),
                "reachable_after": bool(redo.notna().any()),
            }
        report.append(entry)
    return times, report


# --- Tunnel check ----------------------------------------------------------------


def passes_near(route: BaseGeometry, lat: float, lon: float, metres: float) -> bool:
    """Does `route` (EPSG:4326) pass within `metres` of the point?"""
    s = gpd.GeoSeries([route, Point(lon, lat)], crs=config.CRS_WGS84).to_crs(config.CRS_METRIC)
    return bool(s.iloc[0].distance(s.iloc[1]) <= metres)


def walk_check(network, r5py, start: tuple[float, float], end: tuple[float, float]) -> dict:
    """Walk-only itinerary between two (lat, lon) points: time, distance, geometry."""
    o = gpd.GeoDataFrame({"id": ["start"]}, geometry=[Point(start[1], start[0])], crs=4326)
    d = gpd.GeoDataFrame({"id": ["end"]}, geometry=[Point(end[1], end[0])], crs=4326)
    it = r5py.DetailedItineraries(
        network,
        origins=o,
        destinations=d,
        departure=config.analysis_departure(),
        transport_modes=[r5py.TransportMode.WALK],
        speed_walking=config.WALK_SPEED_KMH,
        snap_to_network=True,
    )
    it = pd.DataFrame(it)
    best = it.loc[it.groupby("option")["travel_time"].transform("sum").idxmin(), "option"]
    legs = it[it["option"] == best]
    # A leg can be a LineString or a MultiLineString; merge all parts into one route.
    parts = [p for g in legs["geometry"] if g is not None for p in getattr(g, "geoms", [g])]
    return {
        "minutes": legs["travel_time"].sum().total_seconds() / 60,
        "metres": float(legs["distance"].sum()),
        "route": linemerge(MultiLineString(parts)),
    }


def write_route_geojson(route: BaseGeometry, path: Path) -> None:
    gpd.GeoDataFrame(geometry=[route], crs=config.CRS_WGS84).to_file(path, driver="GeoJSON")
