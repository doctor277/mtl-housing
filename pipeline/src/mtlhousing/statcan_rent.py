"""Statistics Canada table 46-10-0092-01: asking and paid rent, Montréal CMA.

"Asking rent and paid rent prices, by rental unit type and number of bedrooms,
experimental estimates", quarterly. Used in Phase 2 as the citywide *asking* rent that
CMHC's relative neighbourhood rent levels are scaled to (see docs/methodology.md, Rent).

Only the Montréal CMA rows for apartments and rooms are kept. Every value keeps its
StatCan status symbol (A-D quality, E use with caution, F too unreliable, x suppressed,
.. not available); `usable` is False when there is no value or the status is F or x.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

TABLE_CSV = "46100092.csv"
MONTREAL_CMA_DGUID = "2021S0503462"

# StatCan rental unit type -> our unit key. Québec naming: studio = 1½/2½ (CMHC
# "Bachelor"), 1 bedroom = 3½, 2 bedrooms = 4½, 3+ bedrooms = 5½ and up. Houses are
# dropped: CMHC's survey (the neighbourhood-level source) covers apartments only.
UNIT_TYPES = {
    "Apartment - No bedroom": "studio",
    "Apartment - 1 bedroom": "1br",
    "Apartment - 2 bedrooms": "2br",
    "Apartment - 3 or more bedrooms": "3br_plus",
    "Room": "room",
}
ESTIMATES = {"Average asking rent": "asking", "Average paid rent": "paid"}
UNUSABLE_STATUS = {"F", "x"}


def load_montreal_rents(zip_path: Path) -> pd.DataFrame:
    """Montréal CMA rows as ref_date (YYYY-MM, quarter start), unit, estimate, value,
    status, usable. Every (ref_date, unit, estimate) in the table appears once, with
    value NaN when StatCan publishes nothing."""
    with zipfile.ZipFile(zip_path) as z, z.open(TABLE_CSV) as f:
        raw = pd.read_csv(f, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df = raw[
        (raw["DGUID"] == MONTREAL_CMA_DGUID)
        & raw["Rental unit type"].isin(UNIT_TYPES)
        & raw["Estimates"].isin(ESTIMATES)
    ]
    if df.empty:
        raise ValueError(f"{zip_path}: no Montréal CMA rows (DGUID {MONTREAL_CMA_DGUID})")
    if (df["UOM"] != "Dollars").any() or (df["SCALAR_FACTOR"] != "units").any():
        raise ValueError(f"{zip_path}: unexpected unit or scale")
    out = pd.DataFrame(
        {
            "ref_date": df["REF_DATE"],
            "unit": df["Rental unit type"].map(UNIT_TYPES),
            "estimate": df["Estimates"].map(ESTIMATES),
            "value": pd.to_numeric(df["VALUE"].replace("", None), errors="coerce"),
            "status": df["STATUS"],
        }
    )
    if out.duplicated(["ref_date", "unit", "estimate"]).any():
        raise ValueError(f"{zip_path}: duplicate Montréal rows")
    out["usable"] = out["value"].notna() & ~out["status"].isin(UNUSABLE_STATUS)
    return out.sort_values(["ref_date", "estimate", "unit"]).reset_index(drop=True)


def quarter_label(ref_date: str) -> str:
    """'2025-10' -> '2025 Q4'."""
    year, month = ref_date.split("-")
    return f"{year} Q{(int(month) - 1) // 3 + 1}"


def asking_rents(rents: pd.DataFrame, ref_date: str) -> pd.DataFrame:
    """Asking rent per unit type for one quarter (index = unit). Raises if the quarter
    is missing from the table."""
    q = rents[(rents["ref_date"] == ref_date) & (rents["estimate"] == "asking")]
    if q.empty:
        have = f"{rents['ref_date'].min()}..{rents['ref_date'].max()}"
        raise ValueError(f"quarter {ref_date} not in the table ({have})")
    return q.set_index("unit")[["value", "status", "usable"]]
