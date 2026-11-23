"""Single place for paths and analysis parameters.

Values that are not decided yet (campus points, analysis date) are added in the step
that decides them (1.1 and 1.5), so nothing here is a placeholder guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
# Table 46-10-0092-01, asking and paid rent, quarterly (Phase 2)
STATCAN_RENT_ZIP = RAW_DIR / "statcan" / "46100092-eng.zip"
# Quarter of the citywide asking rent (REF_DATE = first month of the quarter).
# Use the latest quarter: StatCan only sets the current citywide level, while every
# neighbourhood-to-city ratio comes from the CMHC October 2025 survey, so the ratios
# stay internally consistent. The site labels both dates and says StatCan's figures
# are experimental. To update: download the new table, add it to data/manifest.csv,
# set this to the new quarter, re-run the pipeline.
STATCAN_RENT_QUARTER = "2026-04"  # 2026 Q2
STATCAN_RENT_RELEASED = "2026-09-09"  # StatCan release date of that quarter (manifest)
# CMHC Rental Market Survey, HMIP exports (Phase 2): average rent by bedroom type,
# Row / Apartment, Montréal CMA. Only ratios to the CMA total are used.
CMHC_RMS_PERIOD = "October 2025"
CMHC_RENT_CSV = {
    "neighbourhood": RAW_DIR / "cmhc" / "cmhc_rms_2025-10_avg_rent_by_neighbourhood.csv",
    "zone": RAW_DIR / "cmhc" / "cmhc_rms_2025-10_avg_rent_by_zone.csv",
}
# Same survey, rental universe (number of units). Only used to check the crosswalk.
CMHC_UNIVERSE_CSV = {
    "zone": RAW_DIR / "cmhc" / "cmhc_universe_by_zone.csv",
    "neighbourhood": RAW_DIR / "cmhc" / "cmhc_universe_by_neighbourhood.csv",
    "tract": RAW_DIR / "cmhc" / "cmhc_universe_by_tract.csv",
}
# Crosswalk quartier -> CMHC neighbourhood -> zone (hand-made, committed, checked against
# the unit counts by `crosswalk-check`; see docs/methodology.md, Rent).
CROSSWALK_DIR = REPO_ROOT / "pipeline" / "crosswalk"
QUARTIER_TO_CMHC_CSV = CROSSWALK_DIR / "quartier_to_cmhc_neighbourhood.csv"
CMHC_NBHD_TO_ZONE_CSV = CROSSWALK_DIR / "cmhc_neighbourhood_to_zone.csv"
TRACT_TO_CMHC_CSV = CROSSWALK_DIR / "census_tract_to_cmhc_neighbourhood.csv"
# A quartier's part in a second neighbourhood holding less than this share of its rental
# units is folded into the rest instead of kept as a split.
CROSSWALK_FOLD_BELOW = 0.05
# Rental units in mapped tracts that had no occupied dwelling in the 2021 census (built
# since) can't be given to any quartier. Above this share of all mapped units, the
# crosswalk check fails instead of quietly dropping them.
CROSSWALK_MAX_UNALLOCATED = 0.001
# A quartier split between CMHC neighbourhoods gets a value at a step of the rent order
# when the parts with a qualifying value cover at least this share of its rental units
# (re-weighted over them, labelled "covers X% of rental units"). Applies at every step.
RENT_MIN_COVERAGE = 0.80
# Rents on the site are rounded half up to the nearest this many dollars, in the export.
RENT_ROUND_STEP = 25
OSM_PBF = RAW_DIR / "osm" / "quebec-261119.osm.pbf"
GTFS_DIR = RAW_DIR / "gtfs"

QUARTIERS_PARQUET = INTERIM_DIR / "quartiers.parquet"
GAF_MONTREAL_PARQUET = INTERIM_DIR / "gaf_montreal.parquet"  # cache of the 299 MB Canada CSV
SAMPLE_POINTS_PARQUET = INTERIM_DIR / "sample_points.parquet"
SAMPLE_POINTS_GEOJSON = INTERIM_DIR / "sample_points.geojson"  # debug / visual check
SAMPLE_POINTS_SUMMARY_CSV = INTERIM_DIR / "sample_points_by_quartier.csv"
CROSSWALK_CHECK_CSV = INTERIM_DIR / "crosswalk_check.csv"
RENT_BY_QUARTIER_CSV = INTERIM_DIR / "rent_by_quartier.csv"
GTFS_FEEDS = {
    "stm": GTFS_DIR / "stm.zip",
    "rem": GTFS_DIR / "rem.zip",
    "exo_trains": GTFS_DIR / "exo_trains.zip",
}
OSM_CLIPPED_PBF = INTERIM_DIR / "montreal.osm.pbf"
OSM_CLIPPED_META = INTERIM_DIR / "montreal.osm.json"  # source hash, bbox, OSM timestamp


def travel_times_parquet(campus_id: str) -> Path:
    return INTERIM_DIR / f"travel_times_{campus_id}.parquet"


def travel_times_meta(campus_id: str) -> Path:
    return INTERIM_DIR / f"travel_times_{campus_id}.json"


# Tunnel check (step 1.6): Université-de-Montréal metro entrance at 2810 boul.
# Édouard-Montpetit (OSM node/289402455), next to the "Tunnel de la Montagne" corridor
# (way/723259189) whose escalator (way/723260098) climbs toward Roger-Gaudry.
UDEM_METRO_ENTRANCE = (45.503511, -73.617252)  # (lat, lon)
TUNNEL_ESCALATOR_MIDPOINT = (45.503315, -73.61672)  # (lat, lon) of way/723260098

# Census division 2466 = Montréal = the island (the agglomeration's 16 municipalities).
MONTREAL_CDUID = "2466"
MIN_POINTS_PER_QUARTIER = 3  # fewer -> quartier flagged low_sample

# Census subdivisions whose homes are kept in the sample (for transparency) but excluded
# from commute statistics, with the reason shown in outputs and methodology.md.
OUT_OF_SCOPE_CSDS = {
    "L'Île-Dorval": (
        "L'Île-Dorval: island municipality with no bridge and only a seasonal ferry; "
        "not reachable by public transit, so excluded from Dorval's commute statistics."
    ),
}


@dataclass(frozen=True)
class NoResidentArea:
    """A polygon part of a quartier where nobody lives. The site shows it as "no
    residents" (no commute time) instead of painting it with the quartier's statistics.
    Each part is picked by a point inside it; export refuses if a census home lies in it."""

    id: str
    quartier_id: str
    name: str
    points: tuple[tuple[float, float], ...]  # (lat, lon), one inside each polygon part
    note: str


NO_RESIDENT_AREAS = (
    NoResidentArea(
        id="37-parc-jean-drapeau",
        quartier_id="37",  # Vieux-Montréal
        name="Parc Jean-Drapeau (Île Sainte-Hélène, Île Notre-Dame)",
        points=((45.5145, -73.5335), (45.5055, -73.5260)),
        note=(
            "Park islands with no permanent residents. The city's reference quartiers "
            "include them in Vieux-Montréal as two separate polygon parts; no census "
            "home in the sample lies on them."
        ),
    ),
)

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
# Walking speed for every walk leg (to the stop, transfers, to the door). r5py default 3.6.
# Set to 4.0 at step 1.9: Google Maps' walk legs on the validation routes imply 3.75-4.3 km/h
# (900 m / 14 min, 1.0 km / 16 min, 500-650 m / 7-9 min), the analysis date is in winter,
# and at 4.8 km/h R5 came out faster than Google on 5 of 7 routes. See VALIDATION.md.
WALK_SPEED_KMH = 4.0
DEPARTURE_START_HHMM = (7, 30)
DEPARTURE_WINDOW = timedelta(minutes=60)  # 7:30-8:30, approximates "arrive around 8:30"

MAX_TRIP_MIN = 120  # r5py default max_time; no result means "more than this"

# Calibrated access adjustments (minutes added to every trip ending at a destination;
# negative = R5's last walk is slower than reality). Both UdeM buildings are calibrated
# the same way: adjustment = real walk from the metro platform where R5's trips end, minus
# R5's walk-only time from that platform stop at WALK_SPEED_KMH. R5 times come from
# `python -m mtlhousing access-check` (validation walk routes 6 and 6b).
# - udem_roger_gaudry: target 7 min from the Universite-de-Montreal platform (STM stop 56):
#   the author (UdeM student) and Google Maps (~7 min / 400 m). R5 walks 332 m in
#   5.08 min at 4.0 km/h and misses the uphill climb: 7 - 5.08 = +1.9.
# - udem_jean_brillant: target 7 min from the Cote-des-Neiges platform (STM stop 55):
#   Google Maps (~7 min / 500 m). R5 walks 613 m in 9.40 min at 4.0 km/h (its path starts
#   at the platform coordinate, 459 m from the door in a straight line): 7 - 9.40 = -2.4.
# - concordia_sgw_hall (M3): target 4.5 min from the Guy-Concordia platform (STM stop 34).
#   Google Maps walk 3 min / 180 m, outdoors via De Maisonneuve, but from the station's
#   STREET entrance (Google's geocode): a lower bound. Platform to street adds ~1-2 min
#   (owner), so the real walk is 4-5 min; the midpoint 4.5 is used. R5 walks 184 m in
#   2.87 min at 4.0 km/h: 4.5 - 2.87 = +1.6. (Google times collected 2026-11-23 in the
#   owner's browser by Claude (chat) for the owner; validation route 6.)
# - mcgill_roddick_gates: no adjustment. Google 4 min / 250 m from the McGill station's
#   street entrance + 1-2 min = 5-6 min; R5 walks 357 m from STM stop 32 in 5.43 min,
#   inside that range.
# The adjustments depend on WALK_SPEED_KMH: re-run access-check after any speed change.
# See docs/methodology.md.
ACCESS_ADJUSTMENT_MIN = {
    "udem_roger_gaudry": 1.9,
    "udem_jean_brillant": -2.4,
    "concordia_sgw_hall": 1.6,
}


def check_routing_speed(routing_meta: dict, campus_id: str) -> None:
    """Saved travel times must have been routed at the current WALK_SPEED_KMH, because
    ACCESS_ADJUSTMENT_MIN is calibrated for that speed."""
    speed = routing_meta.get("speed_walking_kmh")
    if speed != WALK_SPEED_KMH:
        raise ValueError(
            f"{campus_id}: saved travel times were routed at {speed} km/h, but "
            f"WALK_SPEED_KMH is {WALK_SPEED_KMH}. Re-run "
            f"`python -m mtlhousing travel-times --campus {campus_id}` (not --repair-only)."
        )


# Commute reliability: flag a quartier when more than this share of its dwellings
# cannot reach the campus within MAX_TRIP_MIN.
UNREACHABLE_FLAG_SHARE = 0.10

# Analysis date (step 1.5, `python -m mtlhousing gtfs-check`): a Tuesday with normal
# weekday service in all three feeds (STM 26N to 2027-01-03, REM to 2026-12-31, exo to
# 2027-01-03), during the fall class term, before the STM change of 2027-01-05.
ANALYSIS_DATE = date(2026, 12, 1)


def analysis_departure() -> datetime:
    hour, minute = DEPARTURE_START_HHMM
    return datetime(ANALYSIS_DATE.year, ANALYSIS_DATE.month, ANALYSIS_DATE.day, hour, minute)
