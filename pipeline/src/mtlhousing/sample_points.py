"""Residential sample points per quartier, from the 2021 Census Geographic Attribute File.

The GAF has one row per dissemination block (DB) with dwelling counts, but representative
points only at the dissemination-area (DA) level. So each sample point is a DA's
StatCan representative point, weighted by the dwellings occupied by usual residents
summed over the DA's blocks. Montréal has ~3,200 such DAs, ~35 per quartier.

Steps:
1. extract_gaf(): filter the Canada-wide CSV to one census division once, cache as parquet
   (rebuilt only when the source zip's SHA-256 changes).
2. da_points(): one weighted point per DA.
3. build_sample_points(): assign points to quartiers, add a fallback point for empty
   quartiers, and report per quartier (point count, low_sample, dwelling cross-check).
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from mtlhousing import config

# GAF column -> short name. The CSV is Windows-1252 encoded.
GAF_COLUMNS = {
    "CDUID_DRIDU": "cduid",
    "CSDUID_SDRIDU": "csduid",
    "CSDNAME_SDRNOM": "csd_name",
    "DAUID_ADIDU": "dauid",
    "DARPLAT_ADLAT": "da_lat",
    "DARPLONG_ADLONG": "da_lon",
    "DBUID_IDIDU": "dbuid",
    "DBPOP2021_IDPOP2021": "population",
    "DBTDWELL2021_IDTLOG2021": "total_dwellings",
    "DBURDWELL2021_IDRHLOG2021": "occupied_dwellings",
}
GAF_ENCODING = "cp1252"
NUMERIC = ["da_lat", "da_lon", "population", "total_dwellings", "occupied_dwellings"]

POINT_COLUMNS = [
    "point_id",
    "quartier_id",
    "source",
    "weight",
    "total_dwellings",
    "csd_name",
    "in_scope",
    "scope_note",
    "geometry",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def extract_gaf(
    zip_path: Path = config.STATCAN_GAF_ZIP,
    out_path: Path = config.GAF_MONTREAL_PARQUET,
    cduid: str = config.MONTREAL_CDUID,
) -> pd.DataFrame:
    """Rows of the GAF for one census division. Cached; rebuilt when the zip changes."""
    stamp = out_path.with_name(out_path.name + ".source-sha256")
    digest = sha256(zip_path)
    if out_path.exists() and stamp.exists() and stamp.read_text().strip() == f"{digest} {cduid}":
        return pd.read_parquet(out_path)

    with zipfile.ZipFile(zip_path) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"expected one CSV in {zip_path.name}, found {csv_names}")
        with z.open(csv_names[0]) as f:
            chunks = pd.read_csv(
                f,
                usecols=list(GAF_COLUMNS),
                dtype=str,
                encoding=GAF_ENCODING,
                chunksize=200_000,
            )
            rows = pd.concat((c[c["CDUID_DRIDU"] == cduid] for c in chunks), ignore_index=True)

    rows = rows.rename(columns=GAF_COLUMNS)
    for col in NUMERIC:
        rows[col] = pd.to_numeric(rows[col], errors="raise")
    if rows.empty:
        raise ValueError(f"no GAF rows for census division {cduid}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows.to_parquet(out_path, index=False)
    stamp.write_text(f"{digest} {cduid}\n")
    return rows


def da_points(gaf: pd.DataFrame) -> gpd.GeoDataFrame:
    """One point per DA at StatCan's representative point; drops DAs with no residents."""
    grouped = gaf.groupby("dauid", sort=True)
    if (grouped["da_lat"].nunique() > 1).any() or (grouped["da_lon"].nunique() > 1).any():
        raise ValueError("a DA has more than one representative point")
    da = grouped.agg(
        lat=("da_lat", "first"),
        lon=("da_lon", "first"),
        occupied_dwellings=("occupied_dwellings", "sum"),
        total_dwellings=("total_dwellings", "sum"),
        **({"csd_name": ("csd_name", "first")} if "csd_name" in gaf else {}),
    ).reset_index()
    da = da[da["occupied_dwellings"] > 0]
    return gpd.GeoDataFrame(
        {
            "point_id": "da:" + da["dauid"],
            "source": "statcan_da",
            "weight": da["occupied_dwellings"].astype(float),
            "total_dwellings": da["total_dwellings"],
            "csd_name": da["csd_name"] if "csd_name" in da else None,
        },
        geometry=gpd.points_from_xy(da["lon"], da["lat"]),
        crs=config.CRS_WGS84,
    ).reset_index(drop=True)


def build_sample_points(
    points: gpd.GeoDataFrame,
    quartiers: gpd.GeoDataFrame,
    min_points: int = config.MIN_POINTS_PER_QUARTIER,
    out_of_scope: dict[str, str] = config.OUT_OF_SCOPE_CSDS,
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Assign points to quartiers. Returns (sample points, per-quartier summary).

    - A point in an out-of-scope census subdivision is kept but marked in_scope=False
      with a scope_note; it is not routed and not counted in the quartier's statistics.
    - A point outside every quartier is dropped and counted in the summary's attrs.
    - A quartier with no point gets its polygon's representative point (source
      "polygon_fallback"), so every quartier can be routed; it is flagged.
    """
    joined = gpd.sjoin(
        points, quartiers[["id", "geometry"]], how="left", predicate="within"
    ).rename(columns={"id": "quartier_id"})
    outside = int(joined["quartier_id"].isna().sum())
    assigned = joined[joined["quartier_id"].notna()].copy()
    assigned["scope_note"] = assigned["csd_name"].map(out_of_scope)
    assigned["in_scope"] = assigned["scope_note"].isna()

    in_scope = assigned[assigned["in_scope"]]
    empty = quartiers[~quartiers["id"].isin(in_scope["quartier_id"])]
    fallback = gpd.GeoDataFrame(
        {
            "point_id": "fallback:" + empty["id"],
            "quartier_id": empty["id"],
            "source": "polygon_fallback",
            "weight": 1.0,
            "total_dwellings": 0,
            "csd_name": None,
            "in_scope": True,
            "scope_note": None,
        },
        geometry=empty.geometry.representative_point(),
        crs=config.CRS_WGS84,
    )
    sample = pd.concat([assigned[POINT_COLUMNS], fallback[POINT_COLUMNS]], ignore_index=True)
    sample = gpd.GeoDataFrame(sample, geometry="geometry", crs=config.CRS_WGS84)
    sample = sample.sort_values(["quartier_id", "point_id"], ignore_index=True)

    real = sample[(sample["source"] == "statcan_da") & sample["in_scope"]]
    excluded = sample[~sample["in_scope"]].groupby("quartier_id").size()
    summary = (
        quartiers.set_index("id")[["name", "dwellings"]]
        .rename(columns={"dwellings": "city_dwellings"})
        .join(
            real.groupby("quartier_id").agg(
                n_points=("point_id", "size"),
                statcan_total_dwellings=("total_dwellings", "sum"),
                statcan_occupied_dwellings=("weight", "sum"),
            )
        )
        .fillna({"n_points": 0, "statcan_total_dwellings": 0, "statcan_occupied_dwellings": 0})
    )
    summary["n_points"] = summary["n_points"].astype(int)
    summary["n_out_of_scope"] = excluded.reindex(summary.index).fillna(0).astype(int)
    summary["dwelling_ratio"] = summary["statcan_total_dwellings"] / summary["city_dwellings"]
    summary["fallback"] = summary.index.isin(empty["id"])
    summary["low_sample"] = summary["n_points"] < min_points
    summary.index.name = "quartier_id"
    summary.attrs["points_outside_quartiers"] = outside
    return sample, summary.reset_index()


def write_outputs(sample: gpd.GeoDataFrame, summary: pd.DataFrame) -> None:
    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    sample.to_parquet(config.SAMPLE_POINTS_PARQUET)
    sample.to_file(config.SAMPLE_POINTS_GEOJSON, driver="GeoJSON")
    summary.to_csv(config.SAMPLE_POINTS_SUMMARY_CSV, index=False)
