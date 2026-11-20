import zipfile

import pandas as pd
import pytest

from mtlhousing import config, statcan_rent

HEADER = (
    '"REF_DATE","GEO","DGUID","Rental unit type","Estimates","UOM","UOM_ID",'
    '"SCALAR_FACTOR","SCALAR_ID","VECTOR","COORDINATE","VALUE","STATUS","SYMBOL",'
    '"TERMINATED","DECIMALS"'
)
MTL = statcan_rent.MONTREAL_CMA_DGUID


def _row(date, dguid, unit, est, value, status=""):
    geo = "Montréal, Census metropolitan area (CMA)" if dguid == MTL else "Other"
    return (
        f'"{date}","{geo}","{dguid}","{unit}","{est}","Dollars","81","units","0",'
        f'"v1","7.1.1","{value}","{status}","","","0"'
    )


@pytest.fixture
def table_zip(tmp_path):
    rows = [
        _row("2025-10", MTL, "Apartment - 1 bedroom", "Average asking rent", 1550),
        _row("2025-10", MTL, "Apartment - 1 bedroom", "Average paid rent", 1180, "E"),
        _row("2025-10", MTL, "Apartment - No bedroom", "Average asking rent", 1290),
        _row("2025-10", MTL, "Apartment - No bedroom", "Average paid rent", ""),
        _row("2025-10", MTL, "Apartment - 2 bedrooms", "Average asking rent", 1920, "F"),
        _row("2025-10", MTL, "House - 2 bedrooms", "Average asking rent", 2500),
        _row("2025-10", MTL, "Room", "Average asking rent", 710),
        _row("2025-10", "2021S0503535", "Apartment - 1 bedroom", "Average asking rent", 2400),
        _row("2026-04", MTL, "Apartment - 1 bedroom", "Average asking rent", 1480),
    ]
    path = tmp_path / "46100092-eng.zip"
    with zipfile.ZipFile(path, "w") as z:
        text = "﻿" + "\n".join([HEADER, *rows]) + "\n"
        z.writestr(statcan_rent.TABLE_CSV, text.encode("utf-8"))
    return path


def test_keeps_montreal_apartments_and_rooms_only(table_zip):
    df = statcan_rent.load_montreal_rents(table_zip)
    assert set(df["unit"]) == {"studio", "1br", "2br", "room"}
    assert len(df) == 7  # house row and the other CMA dropped


def test_status_decides_usable(table_zip):
    df = statcan_rent.load_montreal_rents(table_zip).set_index(["ref_date", "unit", "estimate"])
    assert df.loc[("2025-10", "1br", "paid"), "status"] == "E"
    assert bool(df.loc[("2025-10", "1br", "paid"), "usable"])  # E: caution, still usable
    assert not bool(df.loc[("2025-10", "2br", "asking"), "usable"])  # F
    empty = df.loc[("2025-10", "studio", "paid")]
    assert pd.isna(empty["value"]) and not bool(empty["usable"])


def test_asking_rents_for_a_quarter(table_zip):
    q = statcan_rent.asking_rents(statcan_rent.load_montreal_rents(table_zip), "2025-10")
    assert q.loc["1br", "value"] == 1550 and q.loc["room", "value"] == 710
    with pytest.raises(ValueError, match="2024-10 not in the table"):
        statcan_rent.asking_rents(statcan_rent.load_montreal_rents(table_zip), "2024-10")


def test_quarter_label():
    assert statcan_rent.quarter_label("2025-10") == "2025 Q4"
    assert statcan_rent.quarter_label("2026-04") == "2026 Q2"


def test_no_montreal_rows_raises(tmp_path):
    path = tmp_path / "t.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(statcan_rent.TABLE_CSV, HEADER + "\n")
    with pytest.raises(ValueError, match="no Montréal CMA rows"):
        statcan_rent.load_montreal_rents(path)


@pytest.mark.skipif(not config.STATCAN_RENT_ZIP.exists(), reason="raw StatCan table not present")
def test_real_table_has_the_configured_quarter():
    q = statcan_rent.asking_rents(
        statcan_rent.load_montreal_rents(config.STATCAN_RENT_ZIP), config.STATCAN_RENT_QUARTER
    )
    assert q.loc[["studio", "1br", "2br", "3br_plus"], "usable"].all()
