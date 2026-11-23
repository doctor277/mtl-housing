import pandas as pd
import pytest

from mtlhousing import config, validation


@pytest.mark.parametrize(
    ("google", "tol"),
    [(7, 5.0), (31, 5.0), (33.4, 5.01), (40, 6.0), (60, 9.0)],
)
def test_tolerance_is_max_of_5_min_and_15_percent(google, tol):
    assert validation.tolerance_min(google) == pytest.approx(tol)


def test_implied_adjustment():
    assert validation.implied_adjustment(7, 5.84) == 1.2
    assert validation.implied_adjustment(7, 8.5) == -1.5


def test_walk_routes_calibrate_every_adjusted_building():
    # Every access adjustment has a platform -> entrance walk route behind it (a walk route
    # without an adjustment is fine: McGill's matched R5 within its range).
    walk_dests = set()
    for campus in config.CAMPUSES:
        routes = validation.load_routes(validation.routes_csv(campus))
        walk_dests |= set(routes.loc[routes["kind"] == "walk", "destination_id"])
    assert set(config.ACCESS_ADJUSTMENT_MIN) <= walk_dests


def test_verdict_edges():
    assert validation.verdict(36.0, 31) == "pass"  # exactly +5
    assert validation.verdict(36.1, 31) == "fail"
    assert validation.verdict(25.9, 31) == "fail"  # too fast fails too
    assert validation.verdict(69.0, 60) == "pass"  # 15% = 9
    assert validation.verdict(float("nan"), 60) == "no_result"
    assert validation.verdict(30.0, None) == ""


@pytest.mark.parametrize("campus", list(config.CAMPUSES))
def test_routes_csv_is_well_formed(campus):
    routes = validation.load_routes(validation.routes_csv(campus))
    assert set(routes["kind"]) <= {"transit", "walk"}
    own = {d.id for d in config.CAMPUSES[campus].destinations}
    assert set(routes["destination_id"]) <= own
    transit = routes[routes["kind"] == "transit"]
    assert transit[["lat", "lon"]].notna().all().all()
    lo_lon, lo_lat, hi_lon, hi_lat = config.BBOX
    assert transit["lat"].between(lo_lat, hi_lat).all()
    assert transit["lon"].between(lo_lon, hi_lon).all()
    walk = routes[routes["kind"] == "walk"]
    assert len(walk) >= 1 and walk["gtfs_stop_ids"].notna().all()
    # Google times are collected by hand (VALIDATION.md); every route must have one.
    assert routes["google_min"].notna().all() and routes["google_min"].gt(0).all()


@pytest.mark.skipif(
    not all(p.exists() for p in config.GTFS_FEEDS.values()), reason="GTFS feeds not downloaded"
)
@pytest.mark.parametrize("campus", list(config.CAMPUSES))
def test_walk_routes_start_at_real_gtfs_stops(campus):
    routes = validation.load_routes(validation.routes_csv(campus))
    names = validation.gtfs_names()
    for refs in routes.loc[routes["kind"] == "walk", "gtfs_stop_ids"]:
        for ref in refs.split("|"):
            feed, sid = ref.split(":", 1)
            assert sid in names[feed][1], ref


def test_load_routes_rejects_unknown_destination(tmp_path):
    p = tmp_path / "r.csv"
    pd.DataFrame(
        [{"route": "1", "kind": "transit", "destination_id": "nope", "google_min": 1}]
    ).to_csv(p, index=False)
    with pytest.raises(ValueError, match="nope"):
        validation.load_routes(p)


def test_describe_itinerary_names_lines_and_stops():
    td = pd.Timedelta
    legs = pd.DataFrame(
        [
            {"segment": 0, "transport_mode": "TransportMode.WALK", "travel_time": td(minutes=9),
             "wait_time": td(0), "feed": None, "route_id": None, "start_stop_id": None,
             "end_stop_id": None},
            {"segment": 1, "transport_mode": "TransportMode.SUBWAY",
             "travel_time": td(minutes=6), "wait_time": td(minutes=1), "feed": "stm",
             "route_id": "2", "start_stop_id": "stm:A", "end_stop_id": "B"},
        ]
    )  # fmt: skip
    names = {"stm": ({"2": "2"}, {"A": ("Laurier", 0, 0), "B": ("Jean-Talon", 0, 0)})}
    assert (
        validation.describe_itinerary(legs, names)
        == "walk 9 ; metro 2 Laurier -> Jean-Talon (wait 1)"
    )
