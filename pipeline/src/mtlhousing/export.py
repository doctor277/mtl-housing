"""Export the web data files (step 1.8).

web/public/data/neighbourhoods.geojson
    One feature per quartier: id, name, borough, municipality, dwellings. Geometry is
    simplified as a coverage (shared edges stay shared, no gaps or slivers) and rounded
    to 5 decimals (~1 m). Polygon parts where nobody lives (config.NO_RESIDENT_AREAS)
    are cut out of their quartier and written as separate features with
    no_residents=true, part_of=<quartier id>; they have no commute results.

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
from shapely.geometry import MultiPolygon, Point

from mtlhousing import aggregate, config, i18n

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
        "name": i18n.text(campus.name, campus.name_fr),
        "rule": "fastest_destination",
        "rule_note": (
            "Per home, the campus time is the fastest of the campus buildings below "
            "(optimistic: assumes you go to whichever building is quickest for you). "
            "Each building's own time is in by_destination."
        ),
        "destinations": [
            {
                "id": d.id,
                "name": i18n.text(d.name, d.name_fr),
                "lat": d.lat,
                "lon": d.lon,
                "osm_ref": d.osm_ref,
                "access_adjustment_min": config.ACCESS_ADJUSTMENT_MIN.get(d.id, 0.0),
            }
            for d in campus.destinations
        ],
        "n_sample_points": routing_meta["n_origins"],
        "computed_at": routing_meta["computed_at"],
        "relocated_origins": routing_meta.get("relocated_origins", []),
        "excluded_out_of_scope": routing_meta.get("excluded_out_of_scope", []),
    }


# Credits in both languages (DATA_SOURCES.md, "Attribution text to show on the site"). French
# from each publisher's French page (owner's M5 decision 6):
# - OpenStreetMap: "© les contributeurs d’OpenStreetMap" (owner, M5.3a; OSM's French pages give
#   no fixed French credit line).
# - Ville de Montréal: its suggested credit for digital products ("Avec les données ... tirées
#   du site web des données ouvertes de la Ville de Montréal"),
#   donnees.montreal.ca/licence-d-utilisation. The city publishes it in French only; the
#   English is a faithful translation naming the same dataset (owner, M5.3a).
# - Statistics Canada: "Adapté de Statistique Canada, nom du produit, date de référence. Cela ne
#   constitue pas une approbation de ce produit par Statistique Canada.",
#   statcan.gc.ca/fr/reference/licence; product title "Fichier des attributs géographiques",
#   StatCan's French catalogue (92-151-G).
OSM_CREDIT = i18n.text(
    "© OpenStreetMap contributors (ODbL)", "© les contributeurs d’OpenStreetMap (ODbL)"
)
TRANSIT_CREDIT = i18n.text(
    "Transit schedules: Société de transport de Montréal, Réseau express métropolitain and exo, "
    "licensed under CC BY 4.0. Travel times are derived from these schedules.",
    "Horaires du transport collectif : Société de transport de Montréal, Réseau express "
    "métropolitain et exo, sous licence CC BY 4.0. Les temps de trajet sont calculés à partir "
    "de ces horaires.",
)
VILLE_CREDIT = i18n.text(
    "With data from Quartiers de référence en habitation taken from the Ville de Montréal open "
    "data website, licensed under CC BY 4.0.",
    "Avec les données Quartiers de référence en habitation tirées du site web des données "
    "ouvertes de la Ville de Montréal, sous licence CC BY 4.0.",
)
CENSUS_CREDIT = i18n.text(
    "Adapted from Statistics Canada, 2021 Census Geographic Attribute File (92-151-X). "
    "This does not constitute an endorsement by Statistics Canada of this product.",
    "Adapté de Statistique Canada, Fichier des attributs géographiques, Recensement de 2021 "
    "(92-151-X). Cela ne constitue pas une approbation de ce produit par Statistique Canada.",
)


def commute_sources() -> list[dict[str, str]]:
    return [OSM_CREDIT, TRANSIT_CREDIT, VILLE_CREDIT, CENSUS_CREDIT]


def check_same_routing(routing_meta_by_campus: dict[str, dict]) -> None:
    """commute.json has one analysis date and one feed list for every campus, so every campus
    must have been routed on config.ANALYSIS_DATE with the same feeds. Since M5.5, a `refresh`
    that stops partway leaves some campuses on the old date; export refuses that."""
    day = config.ANALYSIS_DATE.isoformat()
    feeds = next(iter(routing_meta_by_campus.values()))["gtfs_feeds"]
    bad = [
        f"{c}: routed on {m['departure'][:10]}"
        for c, m in routing_meta_by_campus.items()
        if m["departure"][:10] != day
    ] + [
        f"{c}: other GTFS feeds"
        for c, m in routing_meta_by_campus.items()
        if m["gtfs_feeds"] != feeds
    ]
    if bad:
        raise SystemExit(
            f"Campuses don't share the analysis date {day} and feeds; re-run travel-times "
            "and aggregate for: " + "; ".join(bad)
        )


def build_commute(
    stats_by_campus: dict[str, pd.DataFrame],
    routing_meta_by_campus: dict[str, dict],
    quartier_ids: list[str],
) -> dict:
    """Assemble commute.json. Every quartier id gets an entry (possibly empty)."""
    check_same_routing(routing_meta_by_campus)
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
        "out_of_scope": [
            {"area": k, "reason": i18n.text(v, config.OUT_OF_SCOPE_CSDS_FR[k])}
            for k, v in config.OUT_OF_SCOPE_CSDS.items()
        ],
        "sources": commute_sources(),
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


def split_no_resident_areas(
    gdf: gpd.GeoDataFrame,
    homes: gpd.GeoDataFrame,
    areas=config.NO_RESIDENT_AREAS,
) -> gpd.GeoDataFrame:
    """Cut each no-resident area's polygon parts out of its quartier (EPSG:4326) and
    append them as separate features. Raises if a part can't be found, would leave the
    quartier empty, or contains a home (in-scope sample point)."""
    gdf = gdf.assign(no_residents=False, part_of=None).reset_index(drop=True)
    extra = []
    for a in areas:
        i = gdf.index[gdf["id"] == a.quartier_id]
        if len(i) != 1:
            raise ValueError(f"{a.id}: quartier {a.quartier_id} not found")
        i = i[0]
        parts = list(getattr(gdf.at[i, "geometry"], "geoms", [gdf.at[i, "geometry"]]))
        picks = [Point(lon, lat) for lat, lon in a.points]
        out = [k for k, p in enumerate(parts) if any(p.contains(pt) for pt in picks)]
        if len(out) != len(picks) or len(out) == len(parts):
            raise ValueError(f"{a.id}: expected {len(picks)} separate parts, found {len(out)}")
        removed = MultiPolygon([parts[k] for k in out])
        inside = homes[homes.within(removed)]
        if not inside.empty:
            raise ValueError(f"{a.id}: census homes inside: {inside['point_id'].tolist()}")
        keep = [p for k, p in enumerate(parts) if k not in out]
        gdf.at[i, "geometry"] = keep[0] if len(keep) == 1 else MultiPolygon(keep)
        q = gdf.loc[i]
        extra.append(
            {
                "id": a.id, "name": a.name, "borough": q["borough"],
                "municipality": q["municipality"], "dwellings": 0, "no_residents": True,
                "part_of": a.quartier_id, "geometry": removed,
            }
        )  # fmt: skip
    if extra:
        gdf = pd.concat([gdf, gpd.GeoDataFrame(extra, crs=gdf.crs)], ignore_index=True)
    return gdf


def write_neighbourhoods(
    quartiers: gpd.GeoDataFrame,
    path: Path,
    homes: gpd.GeoDataFrame | None = None,
    areas=config.NO_RESIDENT_AREAS,
) -> Path:
    gdf = simplify_quartiers(quartiers)[
        ["id", "name", "borough", "municipality", "dwellings", "geometry"]
    ]
    if homes is not None:
        gdf = split_no_resident_areas(gdf, homes, areas)
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


def stats_parquet(campus_id: str, interim_dir: Path = config.INTERIM_DIR) -> Path:
    return interim_dir / f"commute_{campus_id}_by_quartier.parquet"


def available_campuses(interim_dir: Path = config.INTERIM_DIR) -> tuple[list[str], list[str]]:
    """(campuses with aggregated stats and routing meta, configured campuses without), in
    config order. commute.json is always written for every available campus, so exporting
    after one campus's run never drops the others."""
    have, missing = [], []
    for c in config.CAMPUSES:
        ok = (
            stats_parquet(c, interim_dir).exists()
            and (interim_dir / config.travel_times_meta(c).name).exists()
        )
        (have if ok else missing).append(c)
    return have, missing


def check_aggregated_with(campus_id: str, interim_dir: Path = config.INTERIM_DIR) -> None:
    """Refuse stats aggregated with access adjustments that differ from config's: their
    numbers would not match the access_adjustment_min that commute.json publishes."""
    path = aggregate.aggregated_with_path(campus_id, interim_dir)
    want = aggregate.campus_adjustments(campus_id)
    if not path.exists():
        raise ValueError(
            f"{campus_id}: no record of the adjustments its stats used ({path.name}); "
            f"re-run `python -m mtlhousing aggregate --campus {campus_id}`"
        )
    have = json.loads(path.read_text(encoding="utf-8"))["access_adjustment_min"]
    if have != want:
        raise ValueError(
            f"{campus_id}: stats were aggregated with adjustments {have}, config now has "
            f"{want}; re-run `python -m mtlhousing aggregate --campus {campus_id}`"
        )


def run(campus_ids: list[str] | None = None) -> dict:
    """Write commute.json for `campus_ids` (default: every available campus)."""
    from mtlhousing import boundaries

    if campus_ids is None:
        campus_ids, _ = available_campuses()
    if not campus_ids:
        raise ValueError("no campus has aggregated results; run travel-times and aggregate")

    quartiers = boundaries.load_quartiers()
    stats_by_campus, meta_by_campus = {}, {}
    for c in campus_ids:
        check_aggregated_with(c)
        stats_by_campus[c] = pd.read_parquet(stats_parquet(c))
        meta_by_campus[c] = json.loads(config.travel_times_meta(c).read_text(encoding="utf-8"))
        config.check_routing_speed(meta_by_campus[c], c)

    commute = build_commute(stats_by_campus, meta_by_campus, sorted(quartiers["id"]))
    write_json(commute, COMMUTE_JSON)
    sample = gpd.read_parquet(config.SAMPLE_POINTS_PARQUET)
    homes = sample[sample["in_scope"].astype(bool)].to_crs(config.CRS_WGS84)
    write_neighbourhoods(quartiers, NEIGHBOURHOODS_GEOJSON, homes)
    maps = [
        write_explore_map(quartiers, stats_by_campus[c], c, explore_html(c)) for c in campus_ids
    ]
    return {"commute": commute, "maps": maps}
