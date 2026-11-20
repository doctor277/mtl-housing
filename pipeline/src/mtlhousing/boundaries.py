"""Load the Ville de Montréal "quartiers de référence en habitation" into a clean table.

Output columns: id, name, borough, municipality, dwellings, geometry (EPSG:4326).
- `borough` is the arrondissement for the Ville de Montréal, and the municipality name
  for the villes liées (which have no arrondissement).
- `dwellings` comes from the city's companion CSV (nombre de logements par quartier).
- Invalid geometries (a few self-intersections in the source) are repaired.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from mtlhousing import config

COLUMNS = ["id", "name", "borough", "municipality", "dwellings", "geometry"]


def polygonal(geom: BaseGeometry) -> MultiPolygon:
    """Repair a geometry and keep only its polygon parts, as a MultiPolygon."""
    fixed = shapely.make_valid(geom)
    parts = [g for g in getattr(fixed, "geoms", [fixed]) if isinstance(g, (Polygon, MultiPolygon))]
    polys = [p for part in parts for p in getattr(part, "geoms", [part])]
    if not polys:
        raise ValueError("geometry has no polygonal part after repair")
    return MultiPolygon(polys)


def normalise_quartiers(raw: gpd.GeoDataFrame, logements: pd.DataFrame) -> gpd.GeoDataFrame:
    """Pure transformation from the raw city files to the pipeline's quartier table."""
    if raw.crs is None or not raw.crs.equals(config.CRS_WGS84):
        raw = raw.to_crs(config.CRS_WGS84)

    ids = raw["no_qr"].astype(str)
    if not ids.is_unique:
        raise ValueError(f"duplicate quartier ids: {sorted(ids[ids.duplicated()])}")

    log = logements.assign(No_QR=logements["No_QR"].astype(str))
    missing = set(ids) ^ set(log["No_QR"])
    if missing:
        raise ValueError(
            f"quartier ids differ between GeoJSON and dwellings CSV: {sorted(missing)}"
        )
    dwellings = log.set_index("No_QR")["Nb_log"].astype(int)

    out = gpd.GeoDataFrame(
        {
            "id": ids.values,
            "name": raw["nom_qr"].astype(str).values,
            "borough": raw["nom_arr"].fillna(raw["nom_mun"]).astype(str).values,
            "municipality": raw["nom_mun"].astype(str).values,
            "dwellings": dwellings.loc[ids].values,
        },
        geometry=[polygonal(g) for g in raw.geometry],
        crs=config.CRS_WGS84,
    )
    return out[COLUMNS].sort_values("id", ignore_index=True)


def load_quartiers(
    geojson_path: Path = config.QUARTIERS_GEOJSON,
    logements_path: Path = config.LOGEMENTS_CSV,
) -> gpd.GeoDataFrame:
    raw = gpd.read_file(geojson_path)
    logements = pd.read_csv(logements_path, dtype={"No_QR": str}, encoding="utf-8-sig")
    return normalise_quartiers(raw, logements)


def find_overlaps(quartiers: gpd.GeoDataFrame, min_area_m2: float) -> list[tuple[str, str, float]]:
    """Pairs of quartiers whose intersection is larger than `min_area_m2` (in metres²)."""
    metric = quartiers.to_crs(config.CRS_METRIC)
    left, right = metric.sindex.query(metric.geometry, predicate="intersects")
    pairs = []
    for i, j in zip(left, right, strict=True):
        if i < j:
            area = metric.geometry.iloc[i].intersection(metric.geometry.iloc[j]).area
            if area > min_area_m2:
                pairs.append((metric["id"].iloc[i], metric["id"].iloc[j], area))
    return pairs


def write_quartiers(quartiers: gpd.GeoDataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    quartiers.to_parquet(path)
    return path
