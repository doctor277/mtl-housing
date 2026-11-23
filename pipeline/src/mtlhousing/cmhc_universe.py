"""CMHC Rental Market Survey, rental universe (number of units) by bedroom type (Phase 2).

Reads the HMIP exports "Montréal — Universe by Bedroom Type by <Zone|Neighbourhood|
Census Tract>", "October 2025 Row / Apartment" (Primary Rental Market, table 2.2.11).
They are used only to check the crosswalk (mtlhousing.crosswalk): a zone's count must equal
the sum of its neighbourhoods', and a neighbourhood's the sum of its census tracts'.

Layout, like the average-rent exports but with one column per bedroom type and no grade:

    line 1  title (names the geography level)
    line 2  survey period and structure type
    line 3  header: ,Studio,1 Bedroom,2 Bedroom,3 Bedroom +,Total,
    rows    area name (a tract is named like "0012.01"), then a count per bedroom type
    last    "Montréal": the CMA total
    blank line, then a Notes block

A count is "1,234" or "**" (suppressed), kept as <NA>.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

from mtlhousing.cmhc_rent import CMA_ROW, ENCODING, SUPPRESSED, UNITS

LEVELS = {"zone": "Zone", "neighbourhood": "Neighbourhood", "tract": "Census Tract"}
HEADER = ["", "Studio", "1 Bedroom", "2 Bedroom", "3 Bedroom +", "Total", ""]


def _count(value: str, where: str) -> int | None:
    value = value.strip()
    if value == SUPPRESSED:
        return None
    digits = value.replace(",", "")
    if not digits.isdigit():
        raise ValueError(f"{where}: count {value!r} is not a number or {SUPPRESSED}")
    return int(digits)


def read_universe_table(path: Path, level: str, period: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse one HMIP universe export. Returns (areas, cma), long format with columns
    area, unit, units (nullable Int64). Raises if the file is not the expected table."""
    lines = path.read_bytes().decode(ENCODING).splitlines()
    title = f"Montréal — Universe by Bedroom Type by {LEVELS[level]}"
    if lines[0].strip() != title:
        raise ValueError(f"{path.name}: title is {lines[0]!r}, expected {title!r}")
    if lines[1].strip().rstrip(",") != f"{period} Row / Apartment":
        raise ValueError(f"{path.name}: period line is {lines[1]!r}, expected {period}")
    rows = list(csv.reader(io.StringIO("\n".join(lines[2:]))))
    if rows[0] != HEADER:
        raise ValueError(f"{path.name}: unexpected header {rows[0]}")
    try:
        end = rows.index([], 1)
    except ValueError:
        raise ValueError(f"{path.name}: no blank line before the notes") from None
    if not rows[end + 1] or rows[end + 1][0] != "Notes":
        raise ValueError(f"{path.name}: expected a Notes block after the data")

    records = []
    for row in rows[1:end]:
        if len(row) != len(HEADER) or row[-1].strip():
            raise ValueError(f"{path.name}: row has {len(row)} fields: {row}")
        area = row[0].strip()
        for k, unit in enumerate(UNITS):
            n = _count(row[1 + k], f"{path.name}, {area}, {unit}")
            records.append({"area": area, "unit": unit, "units": n})
    df = pd.DataFrame(records)
    df["units"] = df["units"].astype("Int64")

    names = df["area"].drop_duplicates().tolist()
    if len(names) * len(UNITS) != len(df):
        raise ValueError(f"{path.name}: duplicate area names")
    if names[-1] != CMA_ROW or names.count(CMA_ROW) != 1:
        raise ValueError(f"{path.name}: the last row must be the {CMA_ROW} CMA total")
    cma = df[df["area"] == CMA_ROW].reset_index(drop=True)
    if cma["units"].isna().any():
        raise ValueError(f"{path.name}: CMA total is suppressed")
    return df[df["area"] != CMA_ROW].reset_index(drop=True), cma


def load(paths: dict[str, Path], period: str) -> dict[str, pd.DataFrame]:
    """Read the zone, neighbourhood and tract tables. Returns one frame per level plus
    "cma". All three files must carry the same CMA total."""
    out, cmas = {}, []
    for level in LEVELS:
        out[level], cma = read_universe_table(paths[level], level, period)
        cmas.append(cma)
    if not all(c.equals(cmas[0]) for c in cmas[1:]):
        raise ValueError("the universe exports have different CMA totals")
    out["cma"] = cmas[0]
    return out
