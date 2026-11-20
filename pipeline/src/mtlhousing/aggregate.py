"""Per-quartier commute statistics from per-home travel times.

1. Apply calibrated access penalties per destination (config.ACCESS_PENALTY_MIN).
2. Per home, campus time = fastest of the campus's destinations ("fastest building").
3. Per quartier, for the campus time and for each destination's time: dwelling-weighted
   median, p10 and p90, plus counts, unreachable share and reliability flags.

Unreachable (no result within config.MAX_TRIP_MIN) is treated as +inf: it ranks above
every real time, so it pushes quantiles up and can make them "more than MAX_TRIP_MIN".
It is never dropped and never 0. Quantiles use the weighted inverse CDF (no interpolation):
the smallest time t such that at least q of the dwellings have a time <= t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mtlhousing import config

FASTEST = "fastest"
STAT_COLUMNS = [
    "quartier_id",
    "campus_id",
    "target",  # "fastest" or a destination id
    "median",
    "p10",
    "p90",
    "n_points",
    "n_unreachable",
    "unreachable_share",  # dwelling-weighted
    "fastest_share",  # dwelling-weighted share of homes for which this destination is fastest
    "flags",
]


def weighted_quantile(values, weights, q: float) -> float:
    """Weighted inverse-CDF quantile; values may contain +inf (unreachable)."""
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    if v.size == 0 or w.sum() <= 0:
        return float("nan")
    return float(np.quantile(v, q, weights=w, method="inverted_cdf"))


def apply_access_penalties(times: pd.DataFrame, penalties: dict[str, float]) -> pd.DataFrame:
    """Add a fixed number of minutes to every trip ending at a penalised destination.
    Unreachable (NaN) stays NaN. Keeps the router's value in travel_time_raw_min."""
    out = times.copy()
    out["travel_time_raw_min"] = out["travel_time_min"]
    extra = out["destination_id"].map(penalties).fillna(0.0)
    out["travel_time_min"] = out["travel_time_min"] + extra
    return out


def per_home(times: pd.DataFrame, destination_ids: list[str]) -> pd.DataFrame:
    """Wide table: one row per home, one column per destination plus 'fastest' and the
    id of the fastest destination. Unreachable -> +inf. Ties go to the first destination
    in config order."""
    wide = (
        times.pivot(index="point_id", columns="destination_id", values="travel_time_min")
        .reindex(columns=destination_ids)
        .fillna(np.inf)
    )
    wide[FASTEST] = wide[destination_ids].min(axis=1)
    reachable = np.isfinite(wide[FASTEST])
    wide["fastest_destination"] = wide[destination_ids].idxmin(axis=1).where(reachable)
    return wide


def _flags(n_points: int, unreachable_share: float) -> list[str]:
    flags = []
    if n_points < config.MIN_POINTS_PER_QUARTIER:
        flags.append("low_sample")
    if unreachable_share > config.UNREACHABLE_FLAG_SHARE:
        flags.append("many_unreachable")
    return flags


def quartier_stats(
    times: pd.DataFrame,
    sample: pd.DataFrame,
    campus_id: str,
    penalties: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Long table (STAT_COLUMNS): one row per quartier x target, for one campus."""
    destination_ids = [d.id for d in config.CAMPUSES[campus_id].destinations]
    penalties = config.ACCESS_PENALTY_MIN if penalties is None else penalties
    times = times[times["destination_id"].isin(destination_ids)]
    adjusted = apply_access_penalties(times, penalties)

    homes = sample.loc[sample["in_scope"].astype(bool), ["point_id", "quartier_id", "weight"]]
    wide = per_home(adjusted, destination_ids).join(homes.set_index("point_id"), how="inner")

    rows = []
    for qid, g in wide.groupby("quartier_id", sort=True):
        w = g["weight"].to_numpy(dtype=float)
        total = w.sum()
        for target in [FASTEST, *destination_ids]:
            t = g[target].to_numpy(dtype=float)
            unreachable = ~np.isfinite(t)
            share_unreachable = float(w[unreachable].sum() / total)
            fastest_share = (
                float(w[(g["fastest_destination"] == target).to_numpy()].sum() / total)
                if target != FASTEST
                else float("nan")
            )
            rows.append(
                {
                    "quartier_id": qid,
                    "campus_id": campus_id,
                    "target": target,
                    "median": weighted_quantile(t, w, 0.5),
                    "p10": weighted_quantile(t, w, 0.1),
                    "p90": weighted_quantile(t, w, 0.9),
                    "n_points": len(g),
                    "n_unreachable": int(unreachable.sum()),
                    "unreachable_share": share_unreachable,
                    "fastest_share": fastest_share,
                    "flags": _flags(len(g), share_unreachable),
                }
            )
    return pd.DataFrame(rows, columns=STAT_COLUMNS)


def run_campus(campus_id: str) -> pd.DataFrame:
    import geopandas as gpd

    times = pd.read_parquet(config.travel_times_parquet(campus_id))
    sample = gpd.read_parquet(config.SAMPLE_POINTS_PARQUET)
    stats = quartier_stats(times, sample, campus_id)
    path = config.INTERIM_DIR / f"commute_{campus_id}_by_quartier"
    stats.to_parquet(path.with_suffix(".parquet"), index=False)
    flat = stats.assign(flags=stats["flags"].map(";".join))
    flat.to_csv(path.with_suffix(".csv"), index=False)
    return stats
