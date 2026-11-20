"""Pipeline entry point: `python -m mtlhousing <step>`."""

from __future__ import annotations

import argparse


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


STEPS = {
    "boundaries": step_boundaries,
    "sample-points": step_sample_points,
    "osm-clip": step_osm_clip,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mtlhousing")
    parser.add_argument("step", choices=sorted(STEPS))
    STEPS[parser.parse_args().step]()


if __name__ == "__main__":
    main()
