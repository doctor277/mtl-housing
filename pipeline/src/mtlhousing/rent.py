"""Rent estimates per quartier (Phase 2). See docs/methodology.md, Rent.

Source rule for one CMHC neighbourhood and bedroom type, in order:
1. the neighbourhood's rent, if CMHC grades it a, b or c;
2. else the zone's rent, if graded a, b or c;
3. else the neighbourhood's rent if graded d, labelled low reliability;
4. else the zone's rent if graded d, labelled low reliability;
5. else nothing: "not enough data".
Grade d is only used when no a/b/c value exists at either level. "**" (suppressed or
not statistically reliable) is never used.

A quartier split between neighbourhoods (crosswalk) goes through the same steps once,
for all its parts together (`estimate_quartier`). At each step, the parts with a value
that qualifies count with their share of the quartier's rental units. Steps 1-2 accept
a, b or c; steps 3-4 accept d *or better*, so a c part is never ignored there:
- they cover it all: share-weighted average of their ratios (rent / CMA rent);
- they cover at least RENT_MIN_COVERAGE: the same average, re-weighted over them,
  labelled "covers X% of rental units" (X rounded down);
- less: on to the next step.
The quartier is labelled with the worst grade among the parts used. A quartier with one
neighbourhood gets exactly `choose_source`.

Estimate = ratio x StatCan's Montréal asking rent for the same bedroom type.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from mtlhousing import config

GOOD_GRADES = ("a", "b", "c")
LOW_GRADE = "d"
LEVELS = ("neighbourhood", "zone")


@dataclass(frozen=True)
class CmhcRent:
    rent: float  # NaN when suppressed
    grade: str | None  # a-d, or None when suppressed


@dataclass(frozen=True)
class Source:
    level: str | None  # "neighbourhood", "zone", or None (not enough data)
    rent: float
    grade: str | None
    reliability: str | None  # "ok" (a/b/c), "low" (d), or None


NOT_ENOUGH_DATA = Source(level=None, rent=math.nan, grade=None, reliability=None)


def _grade(r: CmhcRent) -> str | None:
    """Grade, or None when the value can't be used (suppressed, or no rent)."""
    if r.grade is None or not isinstance(r.grade, str) or math.isnan(r.rent):
        return None
    return r.grade


# (grades that count at this step, level, reliability). The grade-d steps accept "d or
# better": a c value is never ignored at a step that accepts d. For one area this changes
# nothing (an a/b/c value is used at step 1 or 2); for a split quartier, a part graded c
# and a part graded d can together reach the coverage a step needs.
D_OR_BETTER = (*GOOD_GRADES, LOW_GRADE)
STEPS = (
    (GOOD_GRADES, "neighbourhood", "ok"),
    (GOOD_GRADES, "zone", "ok"),
    (D_OR_BETTER, "neighbourhood", "low"),
    (D_OR_BETTER, "zone", "low"),
)


def choose_source(neighbourhood: CmhcRent, zone: CmhcRent) -> Source:
    candidates = dict(zip(LEVELS, (neighbourhood, zone), strict=True))
    for grades, level, reliability in STEPS:
        r = candidates[level]
        if _grade(r) in grades:
            return Source(level, r.rent, r.grade, reliability)
    return NOT_ENOUGH_DATA


# --- one estimate per quartier ---------------------------------------------------------

UNITS = ("studio", "1br", "2br", "3br_plus")  # CMHC and StatCan both have these four
COVERAGE_EPS = 1e-9  # shares are rounded to 3 decimals; 0.53 + 0.47 may not be exactly 1
LABELS = {
    ("neighbourhood", "ok"): "estimate (CMHC neighbourhood)",
    ("zone", "ok"): "zone estimate (CMHC zone)",
    ("neighbourhood", "low"): "low reliability (CMHC grade d)",
    ("zone", "low"): "low reliability (CMHC grade d), zone level",
}
NOT_ENOUGH_DATA_LABEL = "not enough data"


@dataclass(frozen=True)
class Part:
    """One CMHC neighbourhood of a quartier, with its share of the quartier's rental units
    and the CMHC values for one bedroom type at both levels."""

    neighbourhood: str
    zone: str
    share: float
    values: dict[str, CmhcRent]  # level -> value


@dataclass(frozen=True)
class Estimate:
    level: str | None
    reliability: str | None
    grade: str | None  # worst grade among the parts used
    ratio: float  # to the CMHC Montréal average; NaN when not enough data
    coverage: float  # share of the quartier's rental units behind the ratio (0 if none)
    areas: str  # CMHC areas used, e.g. "Villeray 0.530 (b) + Saint-Michel 0.470 (c)"
    label: str
    # The same, structured: (area or zone name, share of the quartier's rental units, grade)
    used: tuple[tuple[str, float, str], ...] = ()


def coverage_pct(coverage: float) -> int | None:
    """Whole percent, rounded down; None when the ratio covers the whole quartier."""
    if coverage >= 1 - COVERAGE_EPS:
        return None
    return math.floor(coverage * 100 + COVERAGE_EPS)


def estimate_quartier(
    parts: Iterable[Part], cma_rent: float, min_coverage: float = config.RENT_MIN_COVERAGE
) -> Estimate:
    parts = list(parts)
    if abs(sum(p.share for p in parts) - 1) > 1e-6:
        raise ValueError(f"shares of {[p.neighbourhood for p in parts]} do not sum to 1")
    if not cma_rent > 0:
        raise ValueError(f"CMA rent must be a positive number, got {cma_rent}")
    for grades, level, reliability in STEPS:
        used = [p for p in parts if _grade(p.values[level]) in grades]
        covered = sum(p.share for p in used)
        if not used or covered < min_coverage - COVERAGE_EPS:
            continue
        ratio = sum(p.share * p.values[level].rent / cma_rent for p in used) / covered
        worst = max(p.values[level].grade for p in used)
        # Parts in the same zone share one zone value: list each area once.
        areas: dict[str, list] = {}
        for p in used:
            name = p.neighbourhood if level == "neighbourhood" else p.zone
            areas.setdefault(name, [0.0, p.values[level].grade])[0] += p.share
        text = " + ".join(
            f"{n} ({g})" if s >= 1 - COVERAGE_EPS else f"{n} {s:.3f} ({g})"
            for n, (s, g) in areas.items()
        )
        label = LABELS[(level, reliability)]
        pct = coverage_pct(covered)
        if pct is not None:
            label += f", covers {pct}% of rental units"
        used_areas = tuple((n, min(s, 1.0), g) for n, (s, g) in areas.items())
        return Estimate(
            level, reliability, worst, ratio, min(covered, 1.0), text, label, used_areas
        )
    return Estimate(None, None, None, math.nan, 0.0, "", NOT_ENOUGH_DATA_LABEL)


# --- all quartiers ----------------------------------------------------------------------

STATCAN_OK_STATUS = {"", "A", "B", "C", "D"}  # E (use with caution) and worse: not decided


def _cmhc_value(table: pd.DataFrame, area: str, unit: str) -> CmhcRent:
    row = table.loc[(area, unit)]
    return CmhcRent(float(row["rent"]), row["grade"])


def estimate_all(
    quartier_map: pd.DataFrame,
    zone_map: pd.DataFrame,
    cmhc: dict[str, pd.DataFrame],
    asking: pd.DataFrame,
    min_coverage: float = config.RENT_MIN_COVERAGE,
) -> pd.DataFrame:
    """One row per (quartier, bedroom type). quartier_map / zone_map: crosswalk loaders.
    cmhc: cmhc_rent.load. asking: statcan_rent.asking_rents for the configured quarter.
    Raises if a CMA value the estimate scales to is missing or flagged."""
    cma = cmhc["cma"].set_index("unit")
    for unit in UNITS:
        if not bool(cma.loc[unit, "usable"]):
            raise ValueError(f"CMHC Montréal average for {unit} is not usable")
        if unit not in asking.index or not bool(asking.loc[unit, "usable"]):
            raise ValueError(f"StatCan Montréal asking rent for {unit} is missing or unusable")
        status = asking.loc[unit, "status"]
        if status not in STATCAN_OK_STATUS:
            raise ValueError(
                f"StatCan Montréal asking rent for {unit} has status {status!r}; "
                "how to label it is not decided"
            )
    nb = cmhc["neighbourhood"].set_index(["area", "unit"])
    zn = cmhc["zone"].set_index(["area", "unit"])
    zone_of = zone_map.set_index("cmhc_neighbourhood")["cmhc_zone"]

    rows = []
    for (qid, name), g in quartier_map.groupby(["quartier_id", "quartier_name"], sort=True):
        for unit in UNITS:
            parts = [
                Part(
                    r.cmhc_neighbourhood,
                    zone_of[r.cmhc_neighbourhood],
                    float(r.share),
                    {
                        "neighbourhood": _cmhc_value(nb, r.cmhc_neighbourhood, unit),
                        "zone": _cmhc_value(zn, zone_of[r.cmhc_neighbourhood], unit),
                    },
                )
                for r in g.itertuples()
            ]
            cma_rent = float(cma.loc[unit, "rent"])
            level_rent = float(asking.loc[unit, "value"])
            e = estimate_quartier(parts, cma_rent, min_coverage)
            rows.append(
                {
                    "quartier_id": qid,
                    "quartier_name": name,
                    "unit": unit,
                    "estimate": e.ratio * level_rent,
                    "label": e.label,
                    "level": e.level,
                    "reliability": e.reliability,
                    "grade": e.grade,
                    "coverage": e.coverage,
                    "coverage_pct": coverage_pct(e.coverage) if e.level else None,
                    "ratio": e.ratio,
                    "cmhc_areas": e.areas,
                    "cmhc_used": [{"name": n, "share": s, "grade": g} for n, s, g in e.used],
                    "n_parts": len(parts),
                    "cmhc_cma_rent": cma_rent,
                    "statcan_asking_rent": level_rent,
                    "statcan_status": asking.loc[unit, "status"],
                }
            )
    out = pd.DataFrame(rows)
    out["coverage_pct"] = out["coverage_pct"].astype("Int64")
    return out
