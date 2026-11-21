"""CMHC Rental Market Survey, average rent by bedroom type, Montréal CMA (Phase 2).

Reads the CSV tables exported from CMHC's Housing Market Information Portal (HMIP):
"Montréal — Average Rent by Bedroom Type by <Neighbourhood|Zone>", "October 2025 Row /
Apartment". The export layout is:

    line 1  title (names the geography level)
    line 2  survey period and structure type
    line 3  header: ,Studio,,1 Bedroom,,2 Bedroom,,3 Bedroom +,,Total,,
    rows    area name, then (rent, reliability grade) for each bedroom type
    last    "Montréal": the CMA total
    blank line, then a Notes block

Rents are kept with CMHC's reliability grade: a excellent, b very good, c good,
d poor (use with caution). "**" means suppressed or not statistically reliable.
`usable` marks grades a, b and c. Grade d is kept and used only as a last resort,
labelled low reliability; ** is never used (rule in rent.choose_source).

Only the ratios to the CMA total are used downstream; see docs/methodology.md, Rent.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

ENCODING = "cp1252"  # HMIP exports are Windows-1252 (é = 0xE9, em dash = 0x97)
LEVELS = {"neighbourhood": "Neighbourhood", "zone": "Zone"}
# Each line ends with a comma, so rows have one trailing empty field.
HEADER = ["", "Studio", "", "1 Bedroom", "", "2 Bedroom", "", "3 Bedroom +", "", "Total", "", ""]
UNITS = ["studio", "1br", "2br", "3br_plus", "total"]  # same keys as statcan_rent
GRADES = {"a", "b", "c", "d"}
USABLE_GRADES = {"a", "b", "c"}
SUPPRESSED = "**"
CMA_ROW = "Montréal"


def _rent(value: str, grade: str, where: str) -> tuple[float, str | None]:
    value, grade = value.strip(), grade.strip().lower()
    if value == SUPPRESSED:
        if grade:
            raise ValueError(f"{where}: suppressed value with grade {grade!r}")
        return float("nan"), None
    if grade not in GRADES:
        raise ValueError(f"{where}: rent {value!r} has grade {grade!r}")
    return float(value.replace(",", "")), grade


def read_hmip_table(path: Path, level: str, period: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse one HMIP export. Returns (areas, cma), both long format with columns
    area, unit, rent, grade, usable. Raises if the file is not the expected table
    (level, period, structure type, header) or is malformed."""
    lines = path.read_bytes().decode(ENCODING).splitlines()
    title = f"Montréal — Average Rent by Bedroom Type by {LEVELS[level]}"
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
            rent, grade = _rent(row[1 + 2 * k], row[2 + 2 * k], f"{path.name}, {area}, {unit}")
            records.append({"area": area, "unit": unit, "rent": rent, "grade": grade})
    df = pd.DataFrame(records)
    df["usable"] = df["grade"].isin(USABLE_GRADES)

    names = df["area"].drop_duplicates().tolist()
    if len(names) * len(UNITS) != len(df):
        raise ValueError(f"{path.name}: duplicate area names")
    if names[-1] != CMA_ROW or names.count(CMA_ROW) != 1:
        raise ValueError(f"{path.name}: the last row must be the {CMA_ROW} CMA total")
    cma = df[df["area"] == CMA_ROW].reset_index(drop=True)
    if not cma.set_index("unit").loc[UNITS[:-1], "usable"].all():
        raise ValueError(f"{path.name}: CMA total is not usable for every bedroom type")
    return df[df["area"] != CMA_ROW].reset_index(drop=True), cma


def load(paths: dict[str, Path], period: str) -> dict[str, pd.DataFrame]:
    """Read the neighbourhood and zone tables. Returns {"neighbourhood": ..., "zone":
    ..., "cma": ...}. Both files must carry the same CMA total."""
    out, cmas = {}, []
    for level in LEVELS:
        out[level], cma = read_hmip_table(paths[level], level, period)
        cmas.append(cma)
    if not cmas[0].equals(cmas[1]):
        raise ValueError("neighbourhood and zone exports have different CMA totals")
    out["cma"] = cmas[0]
    return out


def summary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Count of areas per level and grade, per bedroom type (for the CLI step)."""
    parts = []
    for level in LEVELS:
        t = tables[level].assign(grade=tables[level]["grade"].fillna(SUPPRESSED))
        c = t.pivot_table(index="unit", columns="grade", values="area", aggfunc="count")
        parts.append(c.reindex(UNITS).fillna(0).astype(int).assign(level=level))
    return pd.concat(parts).reset_index().set_index(["level", "unit"])
