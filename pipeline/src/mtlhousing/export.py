"""Export the web data files (step 1.8).

web/public/data/neighbourhoods.geojson
    One feature per quartier: id, name, borough, municipality, dwellings. Geometry is
    simplified as a coverage (shared edges stay shared, no gaps or slivers) and rounded
    to 5 decimals (~1 m).

web/public/data/commute.json
    {"meta": {...how, when, from what...}, "results": {quartier_id: {campus_id: {...}}}}

Missing values are JSON null, never NaN. A time that is "more than MAX_TRIP_MIN" (the
router found no trip within the limit) is also null, and its stat name is listed in
"over_max" so the site can say "more than 2 h" instead of "no data".
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd

from mtlhousing import aggregate, config

METHOD_VERSION = "1.0"
SIMPLIFY_TOLERANCE_M = 5.0
COORD_DECIMALS = 5
TIME_DECIMALS = 1
SHARE_DECIMALS = 3
TIME_STATS = ("median", "p10", "p90")

NEIGHBOURHOODS_GEOJSON = config.WEB_DATA_DIR / "neighbourhoods.geojson"
COMMUTE_JSON = config.WEB_DATA_DIR / "commute.json"


def explore_html(campus_id: str) -> Path:
    return config.INTERIM_DIR / f"commute_{campus_id}_map.html"


# --- values ------------------------------------------------------------------------


def time_value(x: float) -> float | None:
    """Minutes rounded for the web; +inf (over max) and NaN (no data) both become None."""
    if x is None or not math.isfinite(x):
        return None
    return round(float(x), TIME_DECIMALS)


def share_value(x: float) -> float | None:
    if x is None or not math.isfinite(x):
        return None
    return round(float(x), SHARE_DECIMALS)


def time_block(row: pd.Series) -> dict:
    """median/p10/p90 as numbers or null, plus which of them are over MAX_TRIP_MIN."""
    out = {s: time_value(row[s]) for s in TIME_STATS}
    out["over_max"] = [s for s in TIME_STATS if row[s] == math.inf]
    return out


# --- commute.json ---------------------------------------------------------------------


def campus_result(stats: pd.DataFrame, destination_ids: list[str]) -> dict:
    """One quartier x one campus, from the long aggregate table (one row per target)."""
    by_target = stats.set_index("target")
    f = by_target.loc[aggregate.FASTEST]
    result = {
        **time_block(f),
        "n_points": int(f["n_points"]),
        "n_unreachable": int(f["n_unreachable"]),
        "unreachable_share": share_value(f["unreachable_share"]),
        "flags": list(f["flags"]),
        "rule": "fastest_destination",
        "by_destination": {},
    }
    for d in destination_ids:
        r = by_target.loc[d]
        result["by_destination"][d] = {
            **time_block(r),
            "n_unreachable": int(r["n_unreachable"]),
            "fastest_share": share_value(r["fastest_share"]),
        }
    return result


def campus_meta(campus_id: str, routing_meta: dict) -> dict:
    campus = config.CAMPUSES[campus_id]
    return {
        "name": campus.name,
        "rule": "fastest_destination",
        "rule_note": (
            "Per home, the campus time is the fastest of the campus buildings below "
            "(optimistic: assumes you go to whichever building is quickest for you). "
            "Each building's own time is in by_destination."
        ),
        "destinations": [
            {
                "id": d.id,
                "name": d.name,
                "lat": d.lat,
                "lon": d.lon,
                "osm_ref": d.osm_ref,
                "access_penalty_min": config.ACCESS_PENALTY_MIN.get(d.id, 0.0),
            }
            for d in campus.destinations
        ],
        "n_sample_points": routing_meta["n_origins"],
        "computed_at": routing_meta["computed_at"],
        "relocated_origins": routing_meta.get("relocated_origins", []),
        "excluded_out_of_scope": routing_meta.get("excluded_out_of_scope", []),
    }


def build_commute(
    stats_by_campus: dict[str, pd.DataFrame],
    routing_meta_by_campus: dict[str, dict],
    quartier_ids: list[str],
) -> dict:
    """Assemble commute.json. Every quartier id gets an entry (possibly empty)."""
    any_meta = next(iter(routing_meta_by_campus.values()))
    hh, mm = config.DEPARTURE_START_HHMM
    meta = {
        "method_version": METHOD_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "analysis_date": config.ANALYSIS_DATE.isoformat(),
        "departure_window": {
            "start": f"{hh:02d}:{mm:02d}",
            "minutes": int(config.DEPARTURE_WINDOW.total_seconds() // 60),
        },
        "percentile_over_window": any_meta["percentile"],
        "walk_speed_kmh": any_meta["speed_walking_kmh"],
        "transport_modes": any_meta["transport_modes"],
        "max_trip_min": config.MAX_TRIP_MIN,
        "units": "minutes",
        "quantiles": (
            "median, p10 and p90 over the quartier's homes (2021 Census dissemination-area "
            "points), weighted by occupied dwellings, inverse CDF without interpolation"
        ),
        "null_meaning": (
            "A null time listed in over_max means more than max_trip_min (no trip found "
            "within the limit). Any other null means no data."
        ),
        "gtfs_feeds": any_meta["gtfs_feeds"],
        "osm_date": any_meta["osm_timestamp"],
        "router": f"r5py {any_meta['r5py_version']}",
        "out_of_scope": [{"area": k, "reason": v} for k, v in config.OUT_OF_SCOPE_CSDS.items()],
        "sources": [
            "© OpenStreetMap contributors (ODbL)",
            "Transit schedules: Société de transport de Montréal, Réseau express "
            "métropolitain and exo, CC BY 4.0. Travel times are derived from these schedules.",
            "Contains data from the Ville de Montréal open data portal, CC BY 4.0.",
            "Adapted from Statistics Canada, 2021 Census Geographic Attribute File "
            "(92-151-X). This does not constitute an endorsement by Statistics Canada "
            "of this product.",
        ],
        "campuses": {c: campus_meta(c, m) for c, m in routing_meta_by_campus.items()},
    }
    results: dict[str, dict] = {qid: {} for qid in quartier_ids}
    for campus_id, stats in stats_by_campus.items():
        destination_ids = [d.id for d in config.CAMPUSES[campus_id].destinations]
        for qid, g in stats.groupby("quartier_id", sort=True):
            results[qid][campus_id] = campus_result(g, destination_ids)
    return {"meta": meta, "results": results}


def write_json(obj: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # allow_nan=False: fail loudly rather than write NaN/Infinity (invalid JSON).
    text = json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=1)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    return path


# --- neighbourhoods.geojson ---------------------------------------------------------


def simplify_quartiers(quartiers: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Coverage simplification in metres, back to WGS84."""
    metric = quartiers.to_crs(config.CRS_METRIC)
    metric = metric.set_geometry(metric.geometry.simplify_coverage(SIMPLIFY_TOLERANCE_M))
    return metric.to_crs(config.CRS_WGS84)


def write_neighbourhoods(quartiers: gpd.GeoDataFrame, path: Path) -> Path:
    gdf = simplify_quartiers(quartiers)[
        ["id", "name", "borough", "municipality", "dwellings", "geometry"]
    ]
    gdf = gdf.assign(dwellings=gdf["dwellings"].astype(int)).sort_values("id")
    gj = json.loads(gdf.to_json(drop_id=True, to_wgs84=False))
    for feat in gj["features"]:
        feat["geometry"] = _round_coords(feat["geometry"])
    gj["attribution"] = "Quartiers de référence en habitation, Ville de Montréal, CC BY 4.0"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(gj, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    return path


def _round_coords(geom: dict) -> dict:
    def r(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], COORD_DECIMALS), round(c[1], COORD_DECIMALS)]
        return [r(x) for x in c]

    return {**geom, "coordinates": r(geom["coordinates"])}


# --- visual check -------------------------------------------------------------------


def write_explore_map(
    quartiers: gpd.GeoDataFrame, stats: pd.DataFrame, campus_id: str, path: Path
) -> Path:
    """Interactive HTML map (folium) for a quick look; not used by the site."""
    f = stats[stats["target"] == aggregate.FASTEST].set_index("quartier_id")
    wide = stats.pivot(index="quartier_id", columns="target", values="median")
    gdf = quartiers.set_index("id").join(f[["median", "p10", "p90", "n_points"]])
    gdf["flags"] = f["flags"].map(", ".join)
    for d in config.CAMPUSES[campus_id].destinations:
        gdf[f"median_{d.id}"] = wide[d.id]
    gdf = gdf.reset_index().drop(columns=["dwellings"])
    m = gdf.explore(
        column="median",
        cmap="viridis_r",
        scheme="UserDefined",
        classification_kwds={"bins": [20, 30, 45, 60, 90, config.MAX_TRIP_MIN]},
        legend=True,
        tooltip=["name", "median", "p10", "p90", "flags"],
        popup=True,
        style_kwds={"weight": 0.6, "color": "white", "fillOpacity": 0.7},
    )
    import folium

    for d in config.CAMPUSES[campus_id].destinations:
        folium.Marker([d.lat, d.lon], tooltip=d.name).add_to(m)
    m.save(str(path))
    return path


# --- run ------------------------------------------------------------------------------


def run(campus_ids: list[str]) -> dict:
    from mtlhousing import boundaries

    quartiers = boundaries.load_quartiers()
    stats_by_campus, meta_by_campus = {}, {}
    for c in campus_ids:
        stats_path = config.INTERIM_DIR / f"commute_{c}_by_quartier.parquet"
        stats_by_campus[c] = pd.read_parquet(stats_path)
        meta_by_campus[c] = json.loads(config.travel_times_meta(c).read_text(encoding="utf-8"))
        config.check_routing_speed(meta_by_campus[c], c)

    commute = build_commute(stats_by_campus, meta_by_campus, sorted(quartiers["id"]))
    write_json(commute, COMMUTE_JSON)
    write_neighbourhoods(quartiers, NEIGHBOURHOODS_GEOJSON)
    maps = [
        write_explore_map(quartiers, stats_by_campus[c], c, explore_html(c)) for c in campus_ids
    ]
    return {"commute": commute, "maps": maps}
