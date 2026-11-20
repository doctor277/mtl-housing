"""Pipeline entry point: `python -m mtlhousing <step>`."""

from __future__ import annotations

import argparse
from datetime import timedelta


def step_boundaries() -> None:
    from mtlhousing import boundaries, config

    q = boundaries.load_quartiers()
    path = boundaries.write_quartiers(q, config.QUARTIERS_PARQUET)
    print(
        f"{len(q)} quartiers, {q['municipality'].nunique()} municipalities, "
        f"{q['dwellings'].sum():,} dwellings -> {path}"
    )


def step_sample_points() -> None:
    from mtlhousing import boundaries, sample_points

    gaf = sample_points.extract_gaf()
    pts = sample_points.da_points(gaf)
    sample, summary = sample_points.build_sample_points(pts, boundaries.load_quartiers())
    sample_points.write_outputs(sample, summary)
    r = summary["dwelling_ratio"]
    print(
        f"{len(gaf):,} census blocks -> {len(pts):,} DA points -> {len(sample):,} sample points "
        f"({summary.attrs['points_outside_quartiers']} outside quartiers, "
        f"{int(summary['fallback'].sum())} fallback)\n"
        f"points per quartier: min {summary['n_points'].min()}, "
        f"median {summary['n_points'].median():.0f}, max {summary['n_points'].max()}\n"
        f"low_sample: {summary.loc[summary['low_sample'], 'name'].tolist()}\n"
        f"out of scope (kept, not routed): "
        f"{sample.loc[~sample['in_scope'], ['point_id', 'csd_name']].values.tolist()}\n"
        f"StatCan 2021 / city dwellings: median {r.median():.3f}, "
        f"range {r.min():.3f}-{r.max():.3f}"
    )


def step_osm_clip() -> None:
    from mtlhousing import config, osm_clip

    meta = osm_clip.clip_osm()
    src_mb = config.OSM_PBF.stat().st_size / 1e6
    print(
        f"{meta['source']} ({src_mb:,.0f} MB) -> {meta['output']} "
        f"({meta['output_bytes'] / 1e6:,.0f} MB), bbox {meta['bbox']}, "
        f"OSM data as of {meta['osm_timestamp']}"
    )


def step_gtfs_check() -> None:
    from mtlhousing import config, gtfs_check

    feeds = [gtfs_check.load_feed(p, name) for name, p in config.GTFS_FEEDS.items()]
    for f in feeds:
        start, end = gtfs_check.service_range(f)
        version = (f.feed_info or {}).get("feed_version") or "-"
        print(f"{f.name:11} service {start} .. {end}  feed_version {version}")
    report = gtfs_check.candidate_report(feeds)
    upcoming = report[report["date"] >= config.ANALYSIS_DATE - timedelta(days=14)]
    print("\nTue/Wed in all feeds (trips per day):")
    print(upcoming.to_string(index=False))
    problems = gtfs_check.check_date(feeds, config.ANALYSIS_DATE)
    verdict = "OK" if not problems else "NOT OK: " + "; ".join(problems)
    print(f"\nconfig.ANALYSIS_DATE = {config.ANALYSIS_DATE} ({config.ANALYSIS_DATE:%A}): {verdict}")
    if problems:
        raise SystemExit(1)


def step_tunnel_check() -> None:
    from mtlhousing import config, travel_times
    from mtlhousing.r5py_setup import import_r5py

    r5py = import_r5py()
    network = travel_times.build_network(r5py)
    rg = config.CAMPUSES["udem"].destinations[0]
    res = travel_times.walk_check(network, r5py, config.UDEM_METRO_ENTRANCE, (rg.lat, rg.lon))
    lat, lon = config.TUNNEL_ESCALATOR_MIDPOINT
    via_tunnel = travel_times.passes_near(res["route"], lat, lon, metres=15)
    out = config.INTERIM_DIR / "tunnel_check_route.geojson"
    travel_times.write_route_geojson(res["route"], out)
    print(
        f"Walk Université-de-Montréal metro -> {rg.name}: {res['minutes']:.1f} min, "
        f"{res['metres']:.0f} m at {config.WALK_SPEED_KMH} km/h; "
        f"uses Tunnel de la Montagne escalator: {via_tunnel}\nroute -> {out}"
    )


def step_travel_times(campus: str, repair_only: bool = False) -> None:
    from mtlhousing import travel_times

    times, meta = travel_times.run_campus(campus, repair_only=repair_only)
    t = times["travel_time_min"]
    print(
        f"{campus}: {meta['n_origins']:,} points x {len(meta['destinations'])} destinations, "
        f"network {meta['seconds_network']} s, routing {meta['seconds_routing']} s\n"
        f"relocated origins: {meta['relocated_origins']}\n"
        f"unreachable pairs: {meta['n_unreachable_pairs']}\n"
        + times.groupby("destination_id")["travel_time_min"]
        .describe(percentiles=[0.1, 0.5, 0.9])
        .round(1)
        .to_string()
        + f"\nall: min {t.min():.0f}, median {t.median():.0f}, max {t.max():.0f} min"
    )


def step_aggregate(campus: str) -> None:
    import numpy as np

    from mtlhousing import aggregate, boundaries, config

    stats = aggregate.run_campus(campus)
    names = boundaries.load_quartiers().set_index("id")["name"]
    fastest = stats[stats["target"] == aggregate.FASTEST].set_index("quartier_id")
    fastest = fastest.join(names)
    print(f"{campus}: {fastest.shape[0]} quartiers, penalties {config.ACCESS_PENALTY_MIN}")
    print(f"median of quartier medians: {fastest['median'].median():.1f} min")
    print("flagged:", {q: f for q, f in zip(fastest["name"], fastest["flags"], strict=True) if f})
    over = fastest[~np.isfinite(fastest["p90"])]["name"].tolist()
    print(f"p90 over {config.MAX_TRIP_MIN} min: {over}")
    shares = stats[stats["target"] != aggregate.FASTEST].groupby("target")["fastest_share"]
    print("mean share of homes per fastest building (unweighted across quartiers):")
    print(shares.mean().round(3).to_string())
    cols = ["name", "median", "p10", "p90", "n_points", "flags"]
    print("\nnearest 5:\n" + fastest.nsmallest(5, "median")[cols].to_string())
    print("\nfarthest 5:\n" + fastest.nlargest(5, "median")[cols].to_string())


def step_export(campus: str) -> None:
    from mtlhousing import export

    out = export.run([campus])
    results = out["commute"]["results"]
    n = sum(1 for r in results.values() if campus in r)
    over = [q for q, r in results.items() if campus in r and r[campus]["over_max"]]
    for path in (export.COMMUTE_JSON, export.NEIGHBOURHOODS_GEOJSON, *out["maps"]):
        print(f"{path.stat().st_size / 1e3:7.0f} kB  {path}")
    print(f"{campus}: {n}/{len(results)} quartiers with results; stats over max: {over}")


def step_validate(campus: str) -> None:
    import pandas as pd

    from mtlhousing import validation

    res = validation.run(campus)
    cols = [
        "route",
        "destination_id",
        "google_min",
        "r5_median_min",
        "r5_p10_min",
        "diff_min",
        "tolerance_min",
        "verdict",
        "google_alt_min",
        "alt_verdict",
    ]
    with pd.option_context("display.width", 200):
        print(res[cols].to_string(index=False))
    n_pass = (res["verdict"] == "pass").sum()
    print(f"\n{n_pass}/{len(res)} pass -> {validation.results_csv(campus)}")


STEPS = {
    "boundaries": step_boundaries,
    "sample-points": step_sample_points,
    "osm-clip": step_osm_clip,
    "gtfs-check": step_gtfs_check,
    "tunnel-check": step_tunnel_check,
    "travel-times": step_travel_times,
    "aggregate": step_aggregate,
    "export": step_export,
    "validate": step_validate,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mtlhousing")
    parser.add_argument("step", choices=sorted(STEPS))
    parser.add_argument(
        "--campus", default="udem", help="campus id (travel-times, aggregate, export)"
    )
    parser.add_argument(
        "--repair-only",
        action="store_true",
        help="travel-times: reuse saved results, only re-route origins that reached nothing",
    )
    args = parser.parse_args()
    if args.step == "travel-times":
        STEPS[args.step](args.campus, args.repair_only)
    elif args.step in ("aggregate", "export", "validate"):
        STEPS[args.step](args.campus)
    else:
        STEPS[args.step]()


if __name__ == "__main__":
    main()
