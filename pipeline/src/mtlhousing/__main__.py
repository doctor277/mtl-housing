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
    print(f"{campus}: {fastest.shape[0]} quartiers, adjustments {config.ACCESS_ADJUSTMENT_MIN}")
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


def step_export() -> None:
    from mtlhousing import export

    campuses, missing = export.available_campuses()
    if missing:
        print(f"NOTE: no aggregated results yet for {missing}; they are left out of commute.json")
    out = export.run(campuses)
    results = out["commute"]["results"]
    for path in (export.COMMUTE_JSON, export.NEIGHBOURHOODS_GEOJSON, *out["maps"]):
        print(f"{path.stat().st_size / 1e3:7.0f} kB  {path}")
    for campus in campuses:
        n = sum(1 for r in results.values() if campus in r)
        over = [q for q, r in results.items() if campus in r and r[campus]["over_max"]]
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


def step_access_check(campus: str) -> None:
    import pandas as pd

    from mtlhousing import validation

    res = validation.access_check(campus)
    with pd.option_context("display.width", 200, "display.max_colwidth", 80):
        print(res.to_string(index=False))


def step_statcan_rent() -> None:
    from mtlhousing import config, statcan_rent

    rents = statcan_rent.load_montreal_rents(config.STATCAN_RENT_ZIP)
    latest = rents["ref_date"].max()
    for ref in sorted({config.STATCAN_RENT_QUARTER, latest}):
        tag = " (configured)" if ref == config.STATCAN_RENT_QUARTER else " (latest)"
        q = rents[rents["ref_date"] == ref].pivot(
            index="unit", columns="estimate", values=["value", "status"]
        )
        print(f"Montréal CMA, {statcan_rent.quarter_label(ref)}{tag}")
        print(q.to_string())
        print()


def step_cmhc_rent() -> None:
    from mtlhousing import cmhc_rent, config

    tables = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    for level in cmhc_rent.LEVELS:
        print(f"{level}: {tables[level]['area'].nunique()} areas")
    print("\nareas per reliability grade (** = suppressed, never used; d = last resort)")
    print(cmhc_rent.summary(tables).to_string())
    print(f"\nMontréal CMA, {config.CMHC_RMS_PERIOD}")
    print(tables["cma"].set_index("unit")[["rent", "grade"]].T.to_string())


def step_crosswalk_check() -> None:
    from mtlhousing import (
        boundaries,
        cmhc_rent,
        cmhc_universe,
        config,
        crosswalk,
        export,
        sample_points,
    )

    qm = crosswalk.load_quartier_map(config.QUARTIER_TO_CMHC_CSV)
    zm = crosswalk.load_zone_map(config.CMHC_NBHD_TO_ZONE_CSV)
    tm = crosswalk.load_tract_map(config.TRACT_TO_CMHC_CSV)
    cmhc = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    universe = cmhc_universe.load(config.CMHC_UNIVERSE_CSV, config.CMHC_RMS_PERIOD)
    quartiers = boundaries.load_quartiers()
    gaf = sample_points.extract_gaf()
    homes = crosswalk.tract_homes(sample_points.da_points(gaf), quartiers)
    census_tracts = set(gaf["ct_name"].dropna())

    crosswalk.check(qm, zm, crosswalk.quartier_table(export.NEIGHBOURHOODS_GEOJSON), cmhc)
    report = crosswalk.verify(qm, zm, tm, universe, homes, census_tracts)
    q = report["quartiers"]
    q.to_csv(config.CROSSWALK_CHECK_CSV, index=False, encoding="utf-8", lineterminator="\n")
    for name, key, col in (
        ("neighbourhood_sums", "neighbourhood", "cmhc_neighbourhood"),
        ("zone_sums", "zone", "cmhc_zone"),
    ):
        s = report[name]
        ok = crosswalk.confirmed(s, col)
        counts = s["status"].value_counts().to_dict()
        print(
            f"{key} = sum of its parts, per (area, bedroom type): {counts}; "
            f"confirmed {len(ok)}/{s[col].nunique()}"
        )
    bounds = crosswalk.zone_bounds(zm, cmhc)
    inside = int(bounds["inside"].sum())
    print(f"zone rent inside its neighbourhoods' range: {inside}/{len(bounds)}")
    conf = q["confidence"].value_counts().to_dict()
    n_q = q["quartier_id"].nunique()
    print(f"quartier rows: {conf} ({n_q} quartiers) -> {config.CROSSWALK_CHECK_CSV}")
    for _, r in report["folded"].iterrows():
        print(
            f"folded: quartier {r['quartier_id']}, {r['raw_share']:.1%} of its rental units "
            f"in {r['cmhc_neighbourhood']}"
        )
    un = report["unallocated"]
    print(
        f"rental units in tracts with no 2021 census home (given to no quartier): "
        f"{int(un['units'].sum())} = {report['unallocated_share']:.3%} {un['ct_name'].tolist()}"
    )
    print(
        "homes in tracts with no CMHC rental units: "
        f"{report['homes_without_units_share']:.1%} of homes in quartiers"
    )
    bad = crosswalk.problems(report)
    for _, r in bounds[~bounds["inside"]].iterrows():
        bad.append(f"zone {r['cmhc_zone']}, {r['unit']}: rent outside its neighbourhoods' range")
    if bad:
        raise SystemExit("crosswalk problems:\n  " + "\n  ".join(bad))
    print("OK: every 'verified' row is confirmed by the unit counts")


def step_rent() -> None:
    from mtlhousing import cmhc_rent, config, crosswalk, export, rent, statcan_rent

    qm = crosswalk.load_quartier_map(config.QUARTIER_TO_CMHC_CSV)
    zm = crosswalk.load_zone_map(config.CMHC_NBHD_TO_ZONE_CSV)
    cmhc = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    crosswalk.check(qm, zm, crosswalk.quartier_table(export.NEIGHBOURHOODS_GEOJSON), cmhc)
    rents = statcan_rent.load_montreal_rents(config.STATCAN_RENT_ZIP)
    latest = rents["ref_date"].max()
    if latest != config.STATCAN_RENT_QUARTER:
        print(
            f"NOTE: StatCan has a newer quarter ({statcan_rent.quarter_label(latest)}); "
            f"using the configured {statcan_rent.quarter_label(config.STATCAN_RENT_QUARTER)}"
        )
    asking = statcan_rent.asking_rents(rents, config.STATCAN_RENT_QUARTER)

    est = rent.estimate_all(qm, zm, cmhc, asking)
    est.drop(columns="cmhc_used").to_csv(
        config.RENT_BY_QUARTIER_CSV, index=False, encoding="utf-8", lineterminator="\n"
    )
    print(
        f"{est['quartier_id'].nunique()} quartiers x {len(rent.UNITS)} bedroom types -> "
        f"{config.RENT_BY_QUARTIER_CSV}\n"
        f"CMHC {config.CMHC_RMS_PERIOD} ratios x StatCan "
        f"{statcan_rent.quarter_label(config.STATCAN_RENT_QUARTER)} asking rents\n"
    )
    counts = est.pivot_table(index="label", columns="unit", values="quartier_id", aggfunc="count")
    print(counts.reindex(columns=list(rent.UNITS)).fillna(0).astype(int).to_string())
    split = est[est["n_parts"] > 1]
    print("\nsplit quartiers:")
    cols = ["quartier_name", "unit", "estimate", "label", "cmhc_areas"]
    print(split[cols].to_string(index=False, float_format=lambda x: f"{x:,.0f}"))


def step_rent_export() -> None:
    from collections import Counter

    from mtlhousing import config, rent_export, statcan_rent

    out, latest = rent_export.run()
    if latest != config.STATCAN_RENT_QUARTER:
        print(f"NOTE: StatCan has a newer quarter ({statcan_rent.quarter_label(latest)})")
    m = out["meta"]
    print(
        f"{len(out['results'])} quartiers -> {rent_export.RENT_JSON} "
        f"({rent_export.RENT_JSON.stat().st_size / 1e3:.0f} kB)\n"
        f"CMHC {m['cmhc']['period']} x StatCan {m['statcan']['quarter']}, "
        f"rounded to ${m['rounding']['step']}; room: ${m['room']['estimate']}"
    )
    for unit in m["bedroom_types"]:
        c = Counter(r[unit]["label"] for r in out["results"].values())
        print(f"  {unit:9s} {dict(sorted(c.items()))}")
    print("crosswalk notes:")
    for n in m["crosswalk_notes"]:
        print(f"  [{n['kind']}] {n.get('quartier_name') or 'island'}: {n['text']}")


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
    "access-check": step_access_check,
    "statcan-rent": step_statcan_rent,
    "cmhc-rent": step_cmhc_rent,
    "crosswalk-check": step_crosswalk_check,
    "rent": step_rent,
    "rent-export": step_rent_export,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mtlhousing")
    parser.add_argument("step", choices=sorted(STEPS))
    parser.add_argument(
        "--campus",
        default="udem",
        help="campus id (travel-times, aggregate, validate, access-check); export always "
        "writes every campus that has results",
    )
    parser.add_argument(
        "--repair-only",
        action="store_true",
        help="travel-times: reuse saved results, only re-route origins that reached nothing",
    )
    args = parser.parse_args()
    if args.step == "travel-times":
        STEPS[args.step](args.campus, args.repair_only)
    elif args.step in ("aggregate", "validate", "access-check"):
        STEPS[args.step](args.campus)
    else:
        STEPS[args.step]()


if __name__ == "__main__":
    main()
