"""Rent estimates per quartier (Phase 2). See docs/methodology.md, Rent.

Source rule for one CMHC neighbourhood and bedroom type, in order:
1. the neighbourhood's rent, if CMHC grades it a, b or c;
2. else the zone's rent, if graded a, b or c;
3. else the neighbourhood's rent if graded d, labelled low reliability;
4. else the zone's rent if graded d, labelled low reliability;
5. else nothing: "not enough data".
Grade d is only used when no a/b/c value exists at either level. "**" (suppressed or
not statistically reliable) is never used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

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


def choose_source(neighbourhood: CmhcRent, zone: CmhcRent) -> Source:
    candidates = dict(zip(LEVELS, (neighbourhood, zone), strict=True))
    for grades, reliability in ((GOOD_GRADES, "ok"), ((LOW_GRADE,), "low")):
        for level in LEVELS:
            r = candidates[level]
            if _grade(r) in grades:
                return Source(level, r.rent, r.grade, reliability)
    return NOT_ENOUGH_DATA
