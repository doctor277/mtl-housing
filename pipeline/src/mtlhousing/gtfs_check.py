"""Check GTFS service calendars and validate the analysis date.

A date is usable when, in every feed:
- it falls inside the feed's service period, and
- the number of trips running that day is typical for that weekday (>= 95% of the
  median over all the same weekdays the feed covers). This catches holidays and
  special schedules that `calendar_dates.txt` removes or replaces.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
TYPICAL_SHARE = 0.95


@dataclass(frozen=True)
class Feed:
    name: str
    calendar: pd.DataFrame  # may be empty
    calendar_dates: pd.DataFrame  # may be empty
    trips_per_service: pd.Series  # service_id -> number of trips
    feed_info: dict | None


def _read(z: zipfile.ZipFile, name: str) -> pd.DataFrame | None:
    if name not in z.namelist():
        return None
    return pd.read_csv(io.BytesIO(z.read(name)), dtype=str, encoding="utf-8-sig")


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()


def load_feed(path: Path, name: str | None = None) -> Feed:
    with zipfile.ZipFile(path) as z:
        cal = _read(z, "calendar.txt")
        cd = _read(z, "calendar_dates.txt")
        trips = _read(z, "trips.txt")
        info = _read(z, "feed_info.txt")
    if trips is None or (cal is None and cd is None):
        raise ValueError(f"{path.name}: needs trips.txt and calendar.txt or calendar_dates.txt")
    cal = (
        cal
        if cal is not None
        else pd.DataFrame(columns=["service_id", *WEEKDAYS, "start_date", "end_date"])
    )
    cd = cd if cd is not None else pd.DataFrame(columns=["service_id", "date", "exception_type"])
    return Feed(
        name=name or path.stem,
        calendar=cal,
        calendar_dates=cd,
        trips_per_service=trips.groupby("service_id").size(),
        feed_info=info.iloc[0].to_dict() if info is not None and len(info) else None,
    )


def service_range(feed: Feed) -> tuple[date, date]:
    """First and last date on which the feed defines any service."""
    starts = [_d(s) for s in feed.calendar["start_date"]]
    ends = [_d(s) for s in feed.calendar["end_date"]]
    added = [
        _d(s) for s in feed.calendar_dates.loc[feed.calendar_dates["exception_type"] == "1", "date"]
    ]
    return min(starts + added), max(ends + added)


def active_services(feed: Feed, day: date) -> set[str]:
    key, wd = day.strftime("%Y%m%d"), WEEKDAYS[day.weekday()]
    cal = feed.calendar
    on = cal[(cal["start_date"] <= key) & (cal["end_date"] >= key) & (cal[wd] == "1")]
    services = set(on["service_id"])
    exc = feed.calendar_dates[feed.calendar_dates["date"] == key]
    services |= set(exc.loc[exc["exception_type"] == "1", "service_id"])
    services -= set(exc.loc[exc["exception_type"] == "2", "service_id"])
    return services


def trip_count(feed: Feed, day: date) -> int:
    ids = active_services(feed, day)
    return int(feed.trips_per_service[feed.trips_per_service.index.isin(ids)].sum())


def typical_trip_count(feed: Feed, weekday: int) -> float:
    """Median trips over every `weekday` (0=Mon) in the feed's service period."""
    start, end = service_range(feed)
    first = start + timedelta(days=(weekday - start.weekday()) % 7)
    days = [first + timedelta(weeks=k) for k in range((end - first).days // 7 + 1)]
    counts = [trip_count(feed, d) for d in days]
    return float(pd.Series(counts).median()) if counts else 0.0


def check_date(feeds: list[Feed], day: date) -> list[str]:
    """Problems with using `day` as the analysis date; empty list means OK."""
    problems = []
    for feed in feeds:
        start, end = service_range(feed)
        if not start <= day <= end:
            problems.append(f"{feed.name}: {day} outside service period {start}..{end}")
            continue
        n, typical = trip_count(feed, day), typical_trip_count(feed, day.weekday())
        if n < TYPICAL_SHARE * typical:
            wd = WEEKDAYS[day.weekday()]
            problems.append(f"{feed.name}: {n} trips on {day}, typical {wd} has {typical:.0f}")
    return problems


def candidate_report(feeds: list[Feed], weekdays: tuple[int, ...] = (1, 2)) -> pd.DataFrame:
    """Every Tue/Wed (by default) inside all feeds' periods, with trip counts and a verdict."""
    start = max(service_range(f)[0] for f in feeds)
    end = min(service_range(f)[1] for f in feeds)
    rows = []
    day = start
    while day <= end:
        if day.weekday() in weekdays:
            row = {"date": day, "weekday": WEEKDAYS[day.weekday()][:3]}
            row |= {f.name: trip_count(f, day) for f in feeds}
            row["ok"] = not check_date(feeds, day)
            rows.append(row)
        day += timedelta(days=1)
    return pd.DataFrame(rows)
