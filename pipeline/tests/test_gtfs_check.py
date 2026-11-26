import zipfile
from datetime import date

import pytest

from mtlhousing import config, gtfs_check

CAL_HEADER = (
    "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date"
)


def _feed_zip(path, calendar_rows, calendar_dates_rows, trips_per_service):
    trips = ["route_id,service_id,trip_id"] + [
        f"R,{sid},{sid}-{i}" for sid, n in trips_per_service.items() for i in range(n)
    ]
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("calendar.txt", "\n".join([CAL_HEADER, *calendar_rows]) + "\n")
        z.writestr(
            "calendar_dates.txt",
            "\n".join(["service_id,date,exception_type", *calendar_dates_rows]) + "\n",
        )
        z.writestr("trips.txt", "\n".join(trips) + "\n")
    return path


@pytest.fixture
def feed(tmp_path):
    # Weekday service 2026-11-02 .. 2026-12-27 with 10 trips; holiday 2026-11-11 (Wed)
    # replaced by a reduced service of 3 trips; extra Sunday service on 2026-12-27.
    path = _feed_zip(
        tmp_path / "f.zip",
        ["WK,1,1,1,1,1,0,0,20261102,20261227", "SUN,0,0,0,0,0,0,1,20261102,20261227"],
        ["WK,20261111,2", "HOL,20261111,1", "XTRA,20261228,1"],
        {"WK": 10, "HOL": 3, "SUN": 4, "XTRA": 2},
    )
    return gtfs_check.load_feed(path, "f")


def test_service_range_includes_added_dates(feed):
    assert gtfs_check.service_range(feed) == (date(2026, 11, 2), date(2026, 12, 28))


def test_active_services_apply_exceptions(feed):
    assert gtfs_check.active_services(feed, date(2026, 11, 10)) == {"WK"}
    assert gtfs_check.active_services(feed, date(2026, 11, 11)) == {"HOL"}
    assert gtfs_check.active_services(feed, date(2026, 11, 15)) == {"SUN"}


def test_trip_counts_and_typical(feed):
    assert gtfs_check.trip_count(feed, date(2026, 11, 18)) == 10
    assert gtfs_check.trip_count(feed, date(2026, 11, 11)) == 3
    assert gtfs_check.typical_trip_count(feed, weekday=2) == 10  # median of Wednesdays


def test_check_date_flags_holiday_and_out_of_range(feed):
    assert gtfs_check.check_date([feed], date(2026, 11, 18)) == []
    assert "typical" in gtfs_check.check_date([feed], date(2026, 11, 11))[0]
    assert "outside" in gtfs_check.check_date([feed], date(2027, 1, 5))[0]


def test_candidate_report_lists_tue_wed_with_verdict(feed):
    report = gtfs_check.candidate_report([feed])
    assert set(report["weekday"]) == {"tue", "wed"}
    row = report.set_index("date").loc[date(2026, 11, 11)]
    assert row["f"] == 3 and not row["ok"]


# --- The configured date against the real feeds ----------------------------------

real = pytest.mark.skipif(
    not all(p.exists() for p in config.GTFS_FEEDS.values()), reason="GTFS feeds not downloaded"
)


def test_analysis_date_is_a_tuesday_or_wednesday_read_from_analysis_json():
    # The date moves with each refresh (M5.5), so it isn't pinned here; whether the feeds
    # run normally that day is the next test (and refresh checks it before writing).
    assert config.ANALYSIS_DATE.weekday() in (1, 2)
    assert config.ANALYSIS_DATE == config.read_analysis_date()
    assert config.analysis_departure().date() == config.ANALYSIS_DATE


@real
def test_analysis_date_has_typical_service_in_every_feed():
    feeds = [gtfs_check.load_feed(p, n) for n, p in config.GTFS_FEEDS.items()]
    assert gtfs_check.check_date(feeds, config.ANALYSIS_DATE) == []
