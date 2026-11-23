"""Crosswalk: city quartier -> CMHC neighbourhood(s) -> CMHC zone (Phase 2).

CMHC neighbourhoods and zones are groupings of census tracts, but the HMIP rent exports
carry names only. Three hand-made CSVs in pipeline/crosswalk/ link them:

census_tract_to_cmhc_neighbourhood.csv
    ct_name, cmhc_neighbourhood. Every census tract of Montréal island that has CMHC rental
    units, with the CMHC neighbourhood it belongs to.
quartier_to_cmhc_neighbourhood.csv
    quartier_id, quartier_name, cmhc_neighbourhood, share, confidence, note. One row per
    (quartier, neighbourhood); a quartier spanning several neighbourhoods has several rows
    whose `share` (share of the quartier's CMHC rental units, 3 decimals) sums to 1.
cmhc_neighbourhood_to_zone.csv
    cmhc_neighbourhood, cmhc_zone, confidence, note. Used for the zone fallback.

confidence: verified = `verify` confirms it from CMHC's published unit counts (below);
high = names or borough match one-to-one; medium = inferred from geography or from the
published numbers; low = a guess that needs review.

How `verify` checks the maps against the rental universe (unit counts, October 2025):

1. Tract map. For each neighbourhood and bedroom type, the sum of its tracts' counts
   must equal the neighbourhood's published count. A sum that includes a suppressed (**)
   tract can't be checked, except that it must not exceed the published count. A
   neighbourhood is confirmed when its total matches and no bedroom type contradicts it.
2. Zone map. The same test, one level up: a zone's count = the sum of its neighbourhoods'.
3. Quartier map. A tract's units are split between quartiers by the homes in each
   (StatCan 2021 dissemination-area points, occupied dwellings). A quartier's share in a
   neighbourhood is its units there over its units in all neighbourhoods. A part below
   CROSSWALK_FOLD_BELOW is folded into the rest. The committed shares must match these to
   3 decimals, and a row is verified when its neighbourhood is confirmed. A quartier with
   no tract with rental units can't be checked this way and must not say "verified".
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from mtlhousing import config

CONFIDENCE = {"verified", "high", "medium", "low"}
SHARE_TOLERANCE = 1e-9
SHARE_DECIMALS = 3
TRACT_NAME = r"^\d{4}\.\d{2}$"


def load_quartier_map(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"quartier_id": str}, encoding="utf-8")
    bad = sorted(set(df["confidence"]) - CONFIDENCE)
    if bad:
        raise ValueError(f"{path.name}: unknown confidence {bad}")
    if df.duplicated(["quartier_id", "cmhc_neighbourhood"]).any():
        raise ValueError(f"{path.name}: duplicate (quartier, neighbourhood) rows")
    if not ((df["share"] > 0) & (df["share"] <= 1)).all():
        raise ValueError(f"{path.name}: shares must be in (0, 1]")
    sums = df.groupby("quartier_id")["share"].sum()
    off = sums[(sums - 1).abs() > SHARE_TOLERANCE]
    if not off.empty:
        raise ValueError(f"{path.name}: shares do not sum to 1 for {off.to_dict()}")
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


def load_tract_map(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, encoding="utf-8")
    if list(df.columns) != ["ct_name", "cmhc_neighbourhood"]:
        raise ValueError(f"{path.name}: columns are {list(df.columns)}")
    bad = df.loc[~df["ct_name"].str.match(TRACT_NAME), "ct_name"].tolist()
    if bad:
        raise ValueError(f"{path.name}: tract names not like 0012.01: {bad}")
    if df["ct_name"].duplicated().any():
        raise ValueError(f"{path.name}: a tract is listed twice")
    return df


def quartier_table(geojson: Path) -> pd.DataFrame:
    """id, name, no_residents (and the other properties) of the published quartiers."""
    gj = json.loads(geojson.read_text(encoding="utf-8"))
    return pd.DataFrame([f["properties"] for f in gj["features"]])


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


# --- verification against the rental universe (unit counts) ---------------------------


def sum_check(children: pd.DataFrame, parents: pd.DataFrame, key: str) -> pd.DataFrame:
    """children: one row per (child, unit) with its parent in column `key` and its count
    in `units` (<NA> = suppressed). parents: area, unit, units. Returns one row per
    (parent, unit): children_sum (published children only), n_suppressed, published,
    status = match | mismatch | unchecked."""
    g = children.groupby([key, "unit"])["units"]
    s = pd.DataFrame({"children_sum": g.sum(), "n_suppressed": g.size() - g.count()})
    pub = parents.set_index(["area", "unit"])["units"].rename_axis([key, "unit"])
    unknown = sorted(set(s.index.get_level_values(0)) - set(pub.index.get_level_values(0)))
    if unknown:
        raise ValueError(f"{key} not in the universe export: {unknown}")
    s = s.join(pub.rename("published"))
    complete = (s["n_suppressed"] == 0) & s["published"].notna()
    over = s["published"].notna() & (s["children_sum"] > s["published"])
    s["status"] = "unchecked"
    s.loc[complete & (s["children_sum"] == s["published"]), "status"] = "match"
    s.loc[(complete & (s["children_sum"] != s["published"])) | over, "status"] = "mismatch"
    return s.reset_index()


def confirmed(status: pd.DataFrame, key: str) -> set[str]:
    """Parents whose total matches and whose bedroom types never contradict it."""
    total_ok = status[(status["unit"] == "total") & (status["status"] == "match")][key]
    bad = status[status["status"] == "mismatch"][key]
    return set(total_ok) - set(bad)


def tract_homes(points: gpd.GeoDataFrame, quartiers: gpd.GeoDataFrame) -> pd.DataFrame:
    """Homes per (quartier, census tract) from DA points (sample_points.da_points, with
    ct_name and weight = occupied dwellings). Points outside every quartier are dropped."""
    j = gpd.sjoin(
        points[["ct_name", "weight", "geometry"]],
        quartiers[["id", "geometry"]],
        how="inner",
        predicate="within",
    )
    return (
        j.groupby(["id", "ct_name"])["weight"]
        .sum()
        .rename("homes")
        .rename_axis(["quartier_id", "ct_name"])
        .reset_index()
    )


def derive_shares(
    homes: pd.DataFrame,
    tract_map: pd.DataFrame,
    tract_units: pd.DataFrame,
    fold_below: float = config.CROSSWALK_FOLD_BELOW,
) -> pd.DataFrame:
    """Each quartier's CMHC rental units per neighbourhood, from tract counts split by
    homes. homes: quartier_id, ct_name, homes. tract_units: the universe's tract table.
    Returns quartier_id, cmhc_neighbourhood, n_tracts, units, raw_share, folded, share
    (share after folding parts below `fold_below`; NaN on folded rows)."""
    total = tract_units[tract_units["unit"] == "total"].set_index("area")["units"]
    h = homes[homes["homes"] > 0].copy()
    suppressed = sorted(set(h["ct_name"]) & set(total.index[total.isna()]))
    if suppressed:
        raise ValueError(f"tracts with homes but a suppressed unit total: {suppressed}")
    h["tract_units"] = h["ct_name"].map(total).astype(float).fillna(0.0)  # absent = no units
    nbhd = tract_map.set_index("ct_name")["cmhc_neighbourhood"]
    unmapped = sorted(set(h.loc[h["tract_units"] > 0, "ct_name"]) - set(nbhd.index))
    if unmapped:
        raise ValueError(f"tracts with rental units but no CMHC neighbourhood: {unmapped}")

    h = h[h["tract_units"] > 0].copy()
    h["units"] = h["tract_units"] * h["homes"] / h.groupby("ct_name")["homes"].transform("sum")
    h["cmhc_neighbourhood"] = h["ct_name"].map(nbhd)
    r = (
        h.groupby(["quartier_id", "cmhc_neighbourhood"])
        .agg(n_tracts=("ct_name", "nunique"), units=("units", "sum"))
        .reset_index()
    )
    r["raw_share"] = r["units"] / r.groupby("quartier_id")["units"].transform("sum")
    r["folded"] = r["raw_share"] < fold_below
    kept = r["units"].where(~r["folded"])
    r["share"] = kept / kept.groupby(r["quartier_id"]).transform("sum")
    return r


def verify(
    quartier_map: pd.DataFrame,
    zone_map: pd.DataFrame,
    tract_map: pd.DataFrame,
    universe: dict[str, pd.DataFrame],
    homes: pd.DataFrame,
    fold_below: float = config.CROSSWALK_FOLD_BELOW,
) -> dict[str, pd.DataFrame]:
    """Check the three maps against the unit counts (module docstring). Returns
    {"quartiers", "zones", "neighbourhood_sums", "zone_sums", "folded"}; the first two
    carry a `problem` column (None when the row is fine). See `problems`."""
    t = universe["tract"]
    missing = sorted(set(tract_map["ct_name"]) - set(t["area"]))
    if missing:
        raise ValueError(f"mapped tracts not in the universe export: {missing}")
    tracts = t.merge(tract_map, left_on="area", right_on="ct_name")
    nb_sums = sum_check(tracts, universe["neighbourhood"], "cmhc_neighbourhood")
    nb_ok = confirmed(nb_sums, "cmhc_neighbourhood")
    nz = universe["neighbourhood"].merge(
        zone_map[["cmhc_neighbourhood", "cmhc_zone"]], left_on="area", right_on="cmhc_neighbourhood"
    )
    z_sums = sum_check(nz, universe["zone"], "cmhc_zone")
    z_ok = confirmed(z_sums, "cmhc_zone")

    derived = derive_shares(homes, tract_map, t, fold_below)
    kept = derived[~derived["folded"]][["quartier_id", "cmhc_neighbourhood", "share", "n_tracts"]]
    q = quartier_map.merge(
        kept.rename(columns={"share": "derived_share"}),
        on=["quartier_id", "cmhc_neighbourhood"],
        how="outer",
        indicator=True,
    )
    has_units = q["quartier_id"].isin(derived["quartier_id"])
    q["derived_verified"] = (q["_merge"] == "both") & q["cmhc_neighbourhood"].isin(nb_ok)
    tol = 0.5 * 10**-SHARE_DECIMALS + SHARE_TOLERANCE
    claims = q["confidence"] == "verified"
    q["problem"] = None
    q.loc[claims & ~q["derived_verified"], "problem"] = "says verified, the counts don't confirm it"
    q.loc[(q["_merge"] == "both") & ((q["share"] - q["derived_share"]).abs() > tol), "problem"] = (
        "share differs from the unit counts"
    )
    q.loc[(q["_merge"] == "left_only") & has_units, "problem"] = "no rental units there"
    q.loc[q["_merge"] == "right_only", "problem"] = "part missing from the map"
    q = q.drop(columns="_merge")

    z = zone_map.copy()
    z["derived_verified"] = z["cmhc_zone"].isin(z_ok)
    z["problem"] = None
    z.loc[(z["confidence"] == "verified") & ~z["derived_verified"], "problem"] = (
        "says verified, the counts don't confirm it"
    )
    return {
        "quartiers": q,
        "zones": z,
        "neighbourhood_sums": nb_sums,
        "zone_sums": z_sums,
        "folded": derived[derived["folded"]].reset_index(drop=True),
    }


def problems(report: dict[str, pd.DataFrame]) -> list[str]:
    out = []
    for _, r in report["quartiers"].dropna(subset=["problem"]).iterrows():
        out.append(f"quartier {r['quartier_id']} -> {r['cmhc_neighbourhood']}: {r['problem']}")
    for _, r in report["zones"].dropna(subset=["problem"]).iterrows():
        out.append(f"{r['cmhc_neighbourhood']} -> zone {r['cmhc_zone']}: {r['problem']}")
    return out
