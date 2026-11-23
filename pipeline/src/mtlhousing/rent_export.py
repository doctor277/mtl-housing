"""Write web/public/data/rent.json: the rent estimate per quartier for the site (M2.5).

See docs/methodology.md, Rent. Every estimate is rounded half up to the nearest
RENT_ROUND_STEP dollars here, so the site, its budget filter and the shortlist all use
the value the user sees. "Not enough data" is null, never a number.

Labels are keys, not text: the site holds the wording (English, then French in M5).

    neighbourhood      CMHC area value, rated excellent / very good / good
    zone               wider CMHC zone value, rated excellent / very good / good
    neighbourhood_low  CMHC area value rated "use with caution" (grade d)
    zone_low           wider CMHC zone value rated "use with caution" (grade d)
    none               not enough data
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

from mtlhousing import config, rent

RENT_JSON = config.WEB_DATA_DIR / "rent.json"
METHOD_VERSION = "1.0"
SHARE_DECIMALS = 3
SHOWN_UNITS = ("studio", "1br", "2br")  # the site's three sizes; 3br_plus is exported too

LABEL_KEYS = {
    ("neighbourhood", "ok"): "neighbourhood",
    ("zone", "ok"): "zone",
    ("neighbourhood", "low"): "neighbourhood_low",
    ("zone", "low"): "zone_low",
}
NONE_KEY = "none"
LABEL_MEANINGS = {
    "neighbourhood": "CMHC area value, rated excellent, very good or good by CMHC",
    "zone": "wider CMHC zone value, rated excellent, very good or good by CMHC",
    "neighbourhood_low": "CMHC area value, rated 'use with caution' by CMHC (grade d)",
    "zone_low": "wider CMHC zone value, rated 'use with caution' by CMHC (grade d)",
    NONE_KEY: "not enough data: estimate is null",
}
# CMHC's reliability legend. The site uses the words, never the letter.
GRADE_WORDS = {"a": "excellent", "b": "very good", "c": "good", "d": "use with caution"}
BEDROOM_NAMES = {
    "studio": "studio (1½–2½)",
    "1br": "1 bedroom (3½)",
    "2br": "2 bedrooms (4½)",
    "3br_plus": "3+ bedrooms (5½ and up)",
}


def round_rent(x: float, step: int = config.RENT_ROUND_STEP) -> int | None:
    """Round half up to the nearest `step` dollars; None for NaN (not enough data)."""
    if x is None or pd.isna(x):
        return None
    if not x > 0:
        raise ValueError(f"rent must be positive, got {x}")
    q = (Decimal(repr(float(x))) / step).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(q) * step


def label_key(level: str | None, reliability: str | None) -> str:
    if level is None or pd.isna(level):  # None becomes NaN in a DataFrame
        return NONE_KEY
    return LABEL_KEYS[(level, reliability)]


def result_entry(row: pd.Series) -> dict:
    key = label_key(row["level"], row["reliability"])
    kind = "area" if row["level"] == "neighbourhood" else "zone"
    return {
        "estimate": round_rent(row["estimate"]),
        "label": key,
        "grade": row["grade"] if key != NONE_KEY else None,
        "coverage_pct": None if pd.isna(row["coverage_pct"]) else int(row["coverage_pct"]),
        "cmhc_areas": [
            {
                "type": kind,
                "name": u["name"],
                "share": round(float(u["share"]), SHARE_DECIMALS),
                "grade": u["grade"],
            }
            for u in (row["cmhc_used"] if key != NONE_KEY else [])
        ],
    }


def crosswalk_notes(quartier_map: pd.DataFrame, report: dict) -> list[dict]:
    """Short notes on the crosswalk for the sources & limitations page (M5): links the
    unit counts can't confirm, folded slivers, and two island-wide facts."""
    notes = []
    # Quartiers whose census tracts hold no CMHC rental units: why the counts can't help.
    checked = set(report["quartiers"].dropna(subset=["n_tracts"])["quartier_id"])
    for r in quartier_map[quartier_map["confidence"] != "verified"].itertuples():
        text = (
            f"Linked to CMHC area {r.cmhc_neighbourhood} by name. CMHC's unit counts "
            "can't confirm this link"
        )
        if r.quartier_id not in checked:
            text += ": none of its census tracts has CMHC rental units"
        notes.append(
            {
                "quartier_id": r.quartier_id,
                "quartier_name": r.quartier_name,
                "kind": "unconfirmed_link",
                "cmhc_area": r.cmhc_neighbourhood,
                "confidence": r.confidence,
                "text": text + ".",
            }
        )
    names = quartier_map.drop_duplicates("quartier_id").set_index("quartier_id")
    # Folded units are re-weighted over every kept part (crosswalk.derive_shares).
    kept = quartier_map.groupby("quartier_id")["cmhc_neighbourhood"].agg(list)
    for r in report["folded"].itertuples():
        parts = kept[r.quartier_id]
        into = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
        notes.append(
            {
                "quartier_id": r.quartier_id,
                "quartier_name": names.loc[r.quartier_id, "quartier_name"],
                "kind": "folded",
                "cmhc_area": r.cmhc_neighbourhood,
                "share": round(float(r.raw_share), SHARE_DECIMALS),
                "counted_with": parts,
                "text": (
                    f"{r.raw_share:.1%} of its rental units are in CMHC area "
                    f"{r.cmhc_neighbourhood}; they are counted with {into} instead."
                ),
            }
        )
    notes.append(
        {
            "quartier_id": None,
            "kind": "homes_without_units",
            "share": round(report["homes_without_units_share"], SHARE_DECIMALS),
            "text": (
                f"{report['homes_without_units_share']:.1%} of the island's homes are in "
                "census tracts with no CMHC rental units (CMHC lists no such tract); they "
                "don't affect any estimate."
            ),
        }
    )
    un = report["unallocated"]
    notes.append(
        {
            "quartier_id": None,
            "kind": "unallocated_units",
            "share": round(report["unallocated_share"], 5),
            "text": (
                f"{int(un['units'].sum())} CMHC rental units "
                f"({report['unallocated_share']:.2%}) are in census tracts with no home "
                "in the 2021 census, so no neighbourhood gets them."
            ),
        }
    )
    return notes


def sources(statcan_quarter: str) -> list[str]:
    return [
        f"Adapted from Canada Mortgage and Housing Corporation, Rental Market Survey, "
        f"{config.CMHC_RMS_PERIOD}. This does not constitute an endorsement by CMHC.",
        "Adapted from Statistics Canada, Table 46-10-0092-01 Asking rent and paid rent "
        "prices, by rental unit type and number of bedrooms (experimental estimates), "
        f"{statcan_quarter}. This does not constitute an endorsement by Statistics Canada "
        "of this product.",
        "Adapted from Statistics Canada, 2021 Census Geographic Attribute File (92-151-X). "
        "This does not constitute an endorsement by Statistics Canada of this product.",
        # Exact wording from DATA_SOURCES.md, "Attribution text to show on the site".
        "Contains data from the Ville de Montréal open data portal, licensed under CC BY 4.0.",
    ]


def build_rent(
    est: pd.DataFrame,
    quartier_map: pd.DataFrame,
    report: dict,
    cmhc_cma: pd.DataFrame,
    asking: pd.DataFrame,
    statcan_quarter: str,
    statcan_released: str,
) -> dict:
    """est: rent.estimate_all. report: crosswalk.verify. cmhc_cma: cmhc_rent.load()["cma"].
    asking: statcan_rent.asking_rents for the configured quarter (must include room)."""
    room = asking.loc["room"] if "room" in asking.index else None
    if room is None or not bool(room["usable"]) or room["status"] not in rent.STATCAN_OK_STATUS:
        raise ValueError("StatCan Montréal room asking rent is missing, unusable or flagged")
    cma = cmhc_cma.set_index("unit")
    results: dict[str, dict] = {}
    for r in est.sort_values(["quartier_id", "unit"]).itertuples(index=False):
        row = pd.Series(r._asdict())
        results.setdefault(row["quartier_id"], {})[row["unit"]] = result_entry(row)
    for qid, units in results.items():
        if set(units) != set(rent.UNITS):
            raise ValueError(f"quartier {qid}: bedroom types {sorted(units)}")
        for unit, e in units.items():
            if (e["estimate"] is None) != (e["label"] == NONE_KEY):
                raise ValueError(f"quartier {qid}, {unit}: estimate and label disagree")
    meta = {
        "method_version": METHOD_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "currency": "CAD",
        "per": "month",
        "rounding": {"step": config.RENT_ROUND_STEP, "mode": "half_up"},
        "bedroom_types": list(rent.UNITS),
        "shown_bedroom_types": list(SHOWN_UNITS),
        "bedroom_names": BEDROOM_NAMES,
        "cmhc": {
            "product": "Rental Market Survey, average rent by bedroom type, Row / Apartment",
            "period": config.CMHC_RMS_PERIOD,
        },
        "statcan": {
            "table": "46-10-0092-01",
            "estimate": "average asking rent",
            "quarter": statcan_quarter,
            "released": statcan_released,
            "experimental": True,
        },
        "montreal": {
            unit: {
                "cmhc_average": float(cma.loc[unit, "rent"]),
                "statcan_asking": float(asking.loc[unit, "value"]),
            }
            for unit in rent.UNITS
        },
        "room": {
            "estimate": round_rent(float(room["value"])),
            "scope": "Montréal-wide average asking rent for a room, not per neighbourhood",
        },
        "min_coverage": config.RENT_MIN_COVERAGE,
        "label_keys": LABEL_MEANINGS,
        "grade_words": GRADE_WORDS,
        "null_meaning": "estimate is null when label is 'none': not enough data.",
        "crosswalk_notes": crosswalk_notes(quartier_map, report),
        "sources": sources(statcan_quarter),
    }
    return {"meta": meta, "results": results}


def run(path: Path = RENT_JSON) -> tuple[dict, str]:
    """Load everything, check the crosswalk against the unit counts, estimate, write.
    Returns (rent.json content, latest quarter in the StatCan table)."""
    from mtlhousing import (
        boundaries,
        cmhc_rent,
        cmhc_universe,
        crosswalk,
        export,
        sample_points,
        statcan_rent,
    )

    qm = crosswalk.load_quartier_map(config.QUARTIER_TO_CMHC_CSV)
    zm = crosswalk.load_zone_map(config.CMHC_NBHD_TO_ZONE_CSV)
    tm = crosswalk.load_tract_map(config.TRACT_TO_CMHC_CSV)
    cmhc = cmhc_rent.load(config.CMHC_RENT_CSV, config.CMHC_RMS_PERIOD)
    quartiers = crosswalk.quartier_table(export.NEIGHBOURHOODS_GEOJSON)
    crosswalk.check(qm, zm, quartiers, cmhc)
    universe = cmhc_universe.load(config.CMHC_UNIVERSE_CSV, config.CMHC_RMS_PERIOD)
    gaf = sample_points.extract_gaf()
    homes = crosswalk.tract_homes(sample_points.da_points(gaf), boundaries.load_quartiers())
    report = crosswalk.verify(qm, zm, tm, universe, homes, set(gaf["ct_name"].dropna()))
    bad = crosswalk.problems(report)
    if bad:
        raise ValueError("crosswalk problems (run crosswalk-check):\n  " + "\n  ".join(bad))

    rents = statcan_rent.load_montreal_rents(config.STATCAN_RENT_ZIP)
    asking = statcan_rent.asking_rents(rents, config.STATCAN_RENT_QUARTER)
    est = rent.estimate_all(qm, zm, cmhc, asking)
    out = build_rent(
        est,
        qm,
        report,
        cmhc["cma"],
        asking,
        statcan_rent.quarter_label(config.STATCAN_RENT_QUARTER),
        config.STATCAN_RENT_RELEASED,
    )
    residents = set(quartiers.loc[~quartiers["no_residents"].astype(bool), "id"])
    if set(out["results"]) != residents:
        raise ValueError("rent.json quartiers differ from neighbourhoods.geojson")
    export.write_json(out, path)
    return out, rents["ref_date"].max()
