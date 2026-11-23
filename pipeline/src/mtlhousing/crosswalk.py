"""Crosswalk: city quartier -> CMHC neighbourhood(s) -> CMHC zone (Phase 2).

CMHC neighbourhoods and zones are groupings of census tracts, but the HMIP rent exports
carry names only. The crosswalk was first drawn by hand from names and boroughs, then
checked against CMHC's rental universe counts (units by zone, neighbourhood and census
tract, October 2025): a zone's count must equal the sum of its neighbourhoods', and a
neighbourhood's the sum of its tracts'. Two committed CSVs in pipeline/crosswalk/:

quartier_to_cmhc_neighbourhood.csv
    quartier_id, quartier_name, cmhc_neighbourhood, share, [home_share,] confidence, note.
    One row per (quartier, neighbourhood); a quartier spanning several neighbourhoods has
    several rows whose `share` (share of the quartier's CMHC rental units) sums to 1.
    `home_share` (share of its census homes) is informative only.
cmhc_neighbourhood_to_zone.csv
    cmhc_neighbourhood, cmhc_zone, confidence, note. Used for the zone fallback.

confidence: verified = matches CMHC's published counts exactly; high = names or borough
match one-to-one; medium = inferred from geography or from the published numbers;
low = a guess that needs review.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CONFIDENCE = {"verified", "high", "medium", "low"}
SHARE_TOLERANCE = 1e-9


def load_quartier_map(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"quartier_id": str}, encoding="utf-8")
    bad = sorted(set(df["confidence"]) - CONFIDENCE)
    if bad:
        raise ValueError(f"{path.name}: unknown confidence {bad}")
    if df.duplicated(["quartier_id", "cmhc_neighbourhood"]).any():
        raise ValueError(f"{path.name}: duplicate (quartier, neighbourhood) rows")
    if not ((df["share"] > 0) & (df["share"] <= 1)).all():
        raise ValueError(f"{path.name}: shares must be in (0, 1]")
    for col in ("share", "home_share"):
        if col not in df:
            continue
        sums = df.groupby("quartier_id")[col].sum()
        off = sums[(sums - 1).abs() > SHARE_TOLERANCE]
        if not off.empty:
            raise ValueError(f"{path.name}: {col}s do not sum to 1 for {off.to_dict()}")
    if (df.groupby("quartier_id")["quartier_name"].nunique() != 1).any():
        raise ValueError(f"{path.name}: a quartier has two different names")
    return df


def load_zone_map(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    bad = sorted(set(df["confidence"]) - CONFIDENCE)
    if bad:
        raise ValueError(f"{path.name}: unknown confidence {bad}")
    if df["cmhc_neighbourhood"].duplicated().any():
        raise ValueError(f"{path.name}: a neighbourhood is listed twice")
    return df


def check(
    quartier_map: pd.DataFrame,
    zone_map: pd.DataFrame,
    quartiers: pd.DataFrame,
    cmhc: dict[str, pd.DataFrame],
) -> None:
    """Cross-check the two maps against the quartiers (id, name, no_residents) and the
    CMHC tables (cmhc_rent.load). Raises on the first problem."""
    residents = quartiers[~quartiers["no_residents"].astype(bool)]
    missing = sorted(set(residents["id"]) - set(quartier_map["quartier_id"]))
    extra = sorted(set(quartier_map["quartier_id"]) - set(residents["id"]))
    if missing or extra:
        raise ValueError(f"quartiers not mapped: {missing}; unknown or no residents: {extra}")
    names = residents.set_index("id")["name"]
    wrong = quartier_map[quartier_map["quartier_name"] != quartier_map["quartier_id"].map(names)]
    if not wrong.empty:
        raise ValueError(
            f"quartier names differ from the boundaries: {wrong['quartier_id'].tolist()}"
        )

    nbhds = set(cmhc["neighbourhood"]["area"])
    zones = set(cmhc["zone"]["area"])
    for col, known, frame in (
        ("cmhc_neighbourhood", nbhds, quartier_map),
        ("cmhc_neighbourhood", nbhds, zone_map),
        ("cmhc_zone", zones, zone_map),
    ):
        unknown = sorted(set(frame[col]) - known)
        if unknown:
            raise ValueError(f"{col} not in the CMHC export: {unknown}")
    used = set(quartier_map["cmhc_neighbourhood"])
    if used != set(zone_map["cmhc_neighbourhood"]):
        raise ValueError(
            "neighbourhoods used by quartiers and neighbourhoods with a zone differ: "
            f"{sorted(used ^ set(zone_map['cmhc_neighbourhood']))}"
        )


def zone_bounds(zone_map: pd.DataFrame, cmhc: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Plausibility check of zone membership. A zone's average rent is a unit-weighted
    average of its neighbourhoods', so when every member has a published rent the zone
    rent must lie between the members' min and max. Returns one row per (zone, unit)
    with members all published, and `inside`."""
    n = cmhc["neighbourhood"].merge(
        zone_map[["cmhc_neighbourhood", "cmhc_zone"]],
        left_on="area",
        right_on="cmhc_neighbourhood",
    )
    g = n.groupby(["cmhc_zone", "unit"])["rent"]
    b = pd.DataFrame({"lo": g.min(), "hi": g.max(), "all_published": g.count() == g.size()})
    z = cmhc["zone"].set_index(["area", "unit"])["rent"].rename_axis(["cmhc_zone", "unit"])
    b = b.join(z.rename("zone_rent"), how="left")
    b = b[b["all_published"] & b["zone_rent"].notna()]
    b["inside"] = (b["zone_rent"] >= b["lo"]) & (b["zone_rent"] <= b["hi"])
    return b.drop(columns="all_published").reset_index()
