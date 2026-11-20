"""Manual validation (step 1.9): R5 against Google Maps for hand-picked routes.

Input:  pipeline/validation/<campus>_routes.csv  (origins + Google "Arrive by 8:30"
        times, first suggested trip, entered by hand).
Output: pipeline/validation/<campus>_results.csv

Each transit origin is routed with exactly the main run's R5 settings
(travel_times.routing_kwargs) to every building of the campus, and the calibrated
access penalties are added (config.ACCESS_PENALTY_MIN), as in the published numbers.

Pass rule (plan): |R5 median - Google| <= max(5 min, 15% of Google).
Google's trip time starts when you leave home for a well-timed trip (no initial
wait); R5's median is over departure minutes 7:30-8:30 and includes waiting at the
first stop, so R5 is expected to be a few minutes higher. The R5 p10 is reported
as a "well-timed departure" reference, but the verdict uses the median.

A "walk" row checks the access walk from the metro platform stops to a building
(R5 walk-only time + that building's access penalty).
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from mtlhousing import config

VALIDATION_DIR = config.REPO_ROOT / "pipeline" / "validation"
PASS_ABS_MIN = 5.0
PASS_REL = 0.15
ITINERARY_DEPARTURE = (7, 45)  # one sample departure, to describe R5's route

MODE_LABEL = {"SUBWAY": "metro", "BUS": "bus", "TRAM": "REM", "RAIL": "exo train"}


def routes_csv(campus_id: str) -> Path:
    return VALIDATION_DIR / f"{campus_id}_routes.csv"


def results_csv(campus_id: str) -> Path:
    return VALIDATION_DIR / f"{campus_id}_results.csv"


# --- pass rule ----------------------------------------------------------------------


def tolerance_min(google_min: float) -> float:
    return max(PASS_ABS_MIN, PASS_REL * google_min)


def verdict(r5_min: float | None, google_min: float | None) -> str:
    if google_min is None or pd.isna(google_min):
        return ""
    if r5_min is None or pd.isna(r5_min):
        return "no_result"
    return "pass" if abs(r5_min - google_min) <= tolerance_min(google_min) else "fail"


# --- inputs ---------------------------------------------------------------------------


def load_routes(path: Path) -> pd.DataFrame:
    routes = pd.read_csv(path, dtype={"route": str, "gtfs_stop_ids": str})
    known = {d.id for _, d in config.all_destinations()}
    bad = set(routes["destination_id"]) - known
    if bad:
        raise ValueError(f"unknown destination ids in {path.name}: {sorted(bad)}")
    return routes


def gtfs_names() -> dict[str, tuple[dict, dict]]:
    """feed -> (route_id -> short name, stop_id -> (name, lat, lon))."""
    out = {}
    for feed, path in config.GTFS_FEEDS.items():
        with zipfile.ZipFile(path) as z:
            r = pd.read_csv(io.BytesIO(z.read("routes.txt")), dtype=str)
            s = pd.read_csv(io.BytesIO(z.read("stops.txt")), dtype=str)
        short = r["route_short_name"].fillna(r["route_long_name"])
        stops = {
            sid: (name, float(lat), float(lon))
            for sid, name, lat, lon in zip(
                s["stop_id"], s["stop_name"], s["stop_lat"], s["stop_lon"], strict=True
            )
        }
        out[feed] = (dict(zip(r["route_id"], short, strict=True)), stops)
    return out


def _bare(stop_or_route_id) -> str:
    """r5py may prefix GTFS ids with the feed; keep the GTFS id."""
    return str(stop_or_route_id).split(":", 1)[-1]


def describe_itinerary(legs: pd.DataFrame, names: dict) -> str:
    """One line per itinerary: 'walk 9 ; metro 2 Laurier -> Jean-Talon (wait 1) ; ...'."""
    parts = []
    for leg in legs.sort_values("segment").itertuples():
        mode = str(leg.transport_mode).split(".")[-1]
        minutes = leg.travel_time.total_seconds() / 60
        if mode == "WALK":
            parts.append(f"walk {minutes:.0f}")
            continue
        routes, stops = names.get(str(leg.feed), ({}, {}))
        line = routes.get(_bare(leg.route_id), _bare(leg.route_id))
        a = stops.get(_bare(leg.start_stop_id), (_bare(leg.start_stop_id),))[0]
        b = stops.get(_bare(leg.end_stop_id), (_bare(leg.end_stop_id),))[0]
        wait = leg.wait_time.total_seconds() / 60
        parts.append(f"{MODE_LABEL.get(mode, mode)} {line} {a} -> {b} (wait {wait:.0f})")
    return " ; ".join(parts)


# --- routing ------------------------------------------------------------------------


def _points(rows: pd.DataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"id": [f"route{r}" for r in rows["route"]]},
        geometry=[Point(lon, lat) for lat, lon in zip(rows["lat"], rows["lon"], strict=True)],
        crs=config.CRS_WGS84,
    )


def route_transit(network, r5py, origins: gpd.GeoDataFrame, campus_id: str) -> pd.DataFrame:
    """Median and p10 (minutes, penalties added) for each origin x campus building."""
    from mtlhousing import travel_times

    dests = travel_times.destinations_gdf(campus_id)
    ttm = pd.DataFrame(
        r5py.TravelTimeMatrix(
            network,
            origins=origins,
            destinations=dests,
            percentiles=[10, 50],
            **travel_times.routing_kwargs(r5py),
        )
    ).rename(columns={"from_id": "origin_id", "to_id": "destination_id"})
    penalty = ttm["destination_id"].map(config.ACCESS_PENALTY_MIN).fillna(0.0)
    return pd.DataFrame(
        {
            "origin_id": ttm["origin_id"],
            "destination_id": ttm["destination_id"],
            "r5_raw_median_min": ttm["travel_time_p50"].astype(float),
            "r5_median_min": ttm["travel_time_p50"].astype(float) + penalty,
            "r5_p10_min": ttm["travel_time_p10"].astype(float) + penalty,
            "penalty_min": penalty,
        }
    )


def itineraries(network, r5py, origins: gpd.GeoDataFrame, dest_ids: list[str], names) -> list:
    """R5's best itinerary at one sample departure, origin i -> dest_ids[i]."""
    dests = {d.id: d for _, d in config.all_destinations()}
    d = gpd.GeoDataFrame(
        {"id": [f"d{i}" for i in range(len(dest_ids))]},
        geometry=[Point(dests[x].lon, dests[x].lat) for x in dest_ids],
        crs=config.CRS_WGS84,
    )
    o = origins.assign(id=[f"o{i}" for i in range(len(origins))])
    kw = travel_times_kwargs_single(r5py)
    it = pd.DataFrame(r5py.DetailedItineraries(network, origins=o, destinations=d, **kw))
    it["total"] = it["travel_time"] + it["wait_time"].fillna(pd.Timedelta(0))
    out = []
    for i in range(len(o)):
        x = it[it["from_id"] == f"o{i}"]
        if x.empty:
            out.append("")
            continue
        best = x.groupby("option")["total"].sum().idxmin()
        out.append(describe_itinerary(x[x["option"] == best], names))
    return out


def travel_times_kwargs_single(r5py) -> dict:
    from mtlhousing import travel_times

    kw = travel_times.routing_kwargs(r5py)
    kw.pop("departure_time_window")
    h, m = ITINERARY_DEPARTURE
    kw["departure"] = datetime.combine(config.ANALYSIS_DATE, datetime.min.time()).replace(
        hour=h, minute=m
    )
    return kw


def platform_walk(network, r5py, stop_ids: str, names, destination_id: str) -> dict:
    """Mean R5 walk time from the given GTFS stops to a destination, plus its penalty."""
    from mtlhousing import travel_times

    dest = {d.id: d for _, d in config.all_destinations()}[destination_id]
    walks = []
    for ref in stop_ids.split("|"):
        feed, sid = ref.split(":", 1)
        _, lat, lon = names[feed][1][sid]
        walks.append(travel_times.walk_check(network, r5py, (lat, lon), (dest.lat, dest.lon)))
    raw = sum(w["minutes"] for w in walks) / len(walks)
    penalty = config.ACCESS_PENALTY_MIN.get(destination_id, 0.0)
    detail = ", ".join(
        f"{ref}: {w['minutes']:.1f} min / {w['metres']:.0f} m"
        for ref, w in zip(stop_ids.split("|"), walks, strict=True)
    )
    return {"raw": raw, "median": raw + penalty, "penalty": penalty, "detail": detail}


def quartier_of(points: gpd.GeoDataFrame) -> pd.Series:
    from mtlhousing import boundaries

    q = boundaries.load_quartiers()[["name", "geometry"]]
    j = gpd.sjoin(points, q, how="left", predicate="within")
    return j.groupby(level=0)["name"].first()


# --- run --------------------------------------------------------------------------------


def run(campus_id: str) -> pd.DataFrame:
    from mtlhousing import travel_times
    from mtlhousing.r5py_setup import import_r5py

    routes = load_routes(routes_csv(campus_id))
    r5py = import_r5py()
    network = travel_times.build_network(r5py)
    names = gtfs_names()
    campus_dest_ids = [d.id for d in config.CAMPUSES[campus_id].destinations]

    transit = routes[routes["kind"] == "transit"]
    origins = _points(transit.drop_duplicates("route"))
    origins["quartier"] = quartier_of(origins).values
    times = route_transit(network, r5py, origins, campus_id).set_index(
        ["origin_id", "destination_id"]
    )
    routes_desc = itineraries(
        network, r5py, _points(transit), list(transit["destination_id"]), names
    )
    desc = dict(zip(transit.index, routes_desc, strict=True))

    rows = []
    for idx, r in routes.iterrows():
        out = {
            "route": r["route"],
            "kind": r["kind"],
            "origin": r["origin"],
            "destination_id": r["destination_id"],
            "google_min": r["google_min"],
        }
        if r["kind"] == "walk":
            w = platform_walk(network, r5py, r["gtfs_stop_ids"], names, r["destination_id"])
            out |= {
                "r5_median_min": round(w["median"], 1),
                "r5_raw_median_min": round(w["raw"], 1),
                "penalty_min": w["penalty"],
                "r5_route_0745": f"walk only; {w['detail']}",
            }
        else:
            oid = f"route{r['route']}"
            t = times.loc[(oid, r["destination_id"])]
            others = [d for d in campus_dest_ids if d != r["destination_id"]]
            out |= {
                "quartier": origins.set_index("id").loc[oid, "quartier"],
                "r5_median_min": t["r5_median_min"],
                "r5_raw_median_min": t["r5_raw_median_min"],
                "penalty_min": t["penalty_min"],
                "r5_p10_min": t["r5_p10_min"],
                "other_buildings": "; ".join(
                    f"{d}: {times.loc[(oid, d), 'r5_median_min']:.1f}" for d in others
                ),
                "r5_route_0745": desc[idx],
            }
        g = r["google_min"]
        out["diff_min"] = round(out["r5_median_min"] - g, 1)
        out["tolerance_min"] = round(tolerance_min(g), 1)
        out["verdict"] = verdict(out["r5_median_min"], g)
        if pd.notna(r.get("google_alt_min")):
            out["google_alt_min"] = r["google_alt_min"]
            out["google_alt_note"] = r["google_alt_note"]
            out["alt_diff_min"] = round(out["r5_median_min"] - r["google_alt_min"], 1)
            out["alt_verdict"] = verdict(out["r5_median_min"], r["google_alt_min"])
        rows.append(out)

    columns = [
        "route", "kind", "origin", "quartier", "destination_id", "google_min",
        "r5_median_min", "r5_raw_median_min", "penalty_min", "r5_p10_min", "diff_min",
        "tolerance_min", "verdict", "google_alt_min", "google_alt_note", "alt_diff_min",
        "alt_verdict", "other_buildings", "r5_route_0745",
    ]  # fmt: skip
    result = pd.DataFrame(rows).reindex(columns=columns)
    result.to_csv(results_csv(campus_id), index=False, lineterminator="\n")
    return result
