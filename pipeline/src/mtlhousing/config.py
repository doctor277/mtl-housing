"""Single place for paths and analysis parameters.

Values that are not decided yet (campus points, analysis date) are added in the step
that decides them (1.1 and 1.5), so nothing here is a placeholder guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

# --- Paths -------------------------------------------------------------------
# config.py -> mtlhousing -> src -> pipeline -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
WEB_DATA_DIR = REPO_ROOT / "web" / "public" / "data"

QUARTIERS_GEOJSON = RAW_DIR / "boundaries" / "quartierreferencehabitation.geojson"
LOGEMENTS_CSV = RAW_DIR / "boundaries" / "nombrelogementsquartiersreference.csv"
STATCAN_GAF_ZIP = RAW_DIR / "statcan" / "2021_92-151_X.zip"
OSM_PBF = RAW_DIR / "osm" / "quebec-261119.osm.pbf"
GTFS_DIR = RAW_DIR / "gtfs"

QUARTIERS_PARQUET = INTERIM_DIR / "quartiers.parquet"

# --- Coordinate reference systems -------------------------------------------
CRS_WGS84 = "EPSG:4326"  # storage / web output
CRS_METRIC = "EPSG:32188"  # NAD83 / MTM zone 8: metric work in Montréal

# --- Study area ----------------------------------------------------------------
# Island of Montréal plus a buffer so routes through Laval and the South Shore
# (e.g. yellow line to Longueuil) stay in the network. (min_lon, min_lat, max_lon, max_lat)
BBOX = (-74.10, 45.35, -73.35, 45.80)

# --- Campuses ------------------------------------------------------------------
# A campus has one or more destination BUILDINGS. r5py routes to each building and
# picks the station itself; the campus value for a home is the fastest of its
# destinations ("fastest building"), and each destination's time is kept too.
# Coordinates come from OpenStreetMap (extract of 2026-11-19, see data/manifest.csv),
# preferring the node tagged entrance=main so the trip ends at a real door.


@dataclass(frozen=True)
class Destination:
    id: str  # unique across all campuses, prefixed with the campus id
    name: str
    lat: float
    lon: float
    osm_ref: str  # where the point comes from, for traceability
    note: str


@dataclass(frozen=True)
class Campus:
    id: str
    name: str
    destinations: tuple[Destination, ...]


CAMPUSES: dict[str, Campus] = {
    c.id: c
    for c in (
        Campus(
            id="udem",
            name="Université de Montréal (campus principal)",
            destinations=(
                Destination(
                    id="udem_roger_gaudry",
                    name="Pavillon Roger-Gaudry",
                    lat=45.5027705,
                    lon=-73.6150484,
                    osm_ref="node/2573744215",
                    note="Main entrance L-4 (entrance=main), 2900 boul. Édouard-Montpetit. "
                    "Nearest metro: Université-de-Montréal via the Tunnel de la Montagne.",
                ),
                Destination(
                    id="udem_jean_brillant",
                    name="Pavillon Jean-Brillant",
                    lat=45.4986715,
                    lon=-73.6181739,
                    osm_ref="node/6783857247",
                    note="3200 rue Jean-Brillant; the only entrance mapped on the building "
                    "(entrance=yes, way/27334101). Nearest metro: Côte-des-Neiges.",
                ),
            ),
        ),
        Campus(
            id="mcgill",
            name="McGill University (downtown campus)",
            destinations=(
                Destination(
                    id="mcgill_roddick_gates",
                    name="Roddick Gates",
                    lat=45.503849,
                    lon=-73.574925,
                    osm_ref="way/143798969",
                    note="Rue Sherbrooke Ouest at avenue McGill College.",
                ),
            ),
        ),
        Campus(
            id="concordia_sgw",
            name="Concordia University (Sir George Williams campus)",
            destinations=(
                Destination(
                    id="concordia_sgw_hall",
                    name="Henry F. Hall Building",
                    lat=45.4970373,
                    lon=-73.5786245,
                    osm_ref="node/4035248248",
                    note="Main entrance (entrance=main), 1455 boul. De Maisonneuve Ouest.",
                ),
            ),
        ),
    )
}


def all_destinations() -> list[tuple[str, Destination]]:
    """(campus_id, destination) for every destination, in config order."""
    return [(c.id, d) for c in CAMPUSES.values() for d in c.destinations]


# --- Routing (r5py) ------------------------------------------------------------
JVM_MAX_MEMORY = "6G"  # machine has 16 GB
WALK_SPEED_KMH = 4.8  # close to Google Maps so step 1.9 compares like with like (r5py default 3.6)
DEPARTURE_START_HHMM = (7, 30)
DEPARTURE_WINDOW = timedelta(minutes=60)  # 7:30-8:30, approximates "arrive around 8:30"
