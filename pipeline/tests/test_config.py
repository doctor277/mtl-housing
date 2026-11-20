import pytest

from mtlhousing import config


def test_repo_root_is_detected():
    assert (config.REPO_ROOT / "pipeline" / "pyproject.toml").is_file()
    assert (config.REPO_ROOT / "DATA_SOURCES.md").is_file()


def test_bbox_is_valid_and_covers_downtown():
    min_lon, min_lat, max_lon, max_lat = config.BBOX
    assert min_lon < max_lon and min_lat < max_lat
    # Downtown Montréal (Place Ville Marie, approx.) must be inside.
    lon, lat = -73.569, 45.501
    assert min_lon < lon < max_lon and min_lat < lat < max_lat


def test_campuses_are_the_three_supported():
    assert set(config.CAMPUSES) == {"udem", "mcgill", "concordia_sgw"}
    for key, campus in config.CAMPUSES.items():
        assert campus.id == key
        assert len(campus.destinations) >= 1


def test_destination_ids_are_unique_and_prefixed_by_campus():
    pairs = config.all_destinations()
    ids = [d.id for _, d in pairs]
    assert len(ids) == len(set(ids))
    for campus_id, d in pairs:
        assert d.id.startswith(campus_id + "_"), d.id
        assert d.osm_ref.split("/")[0] in {"node", "way"}


def test_udem_has_both_buildings():
    ids = [d.id for d in config.CAMPUSES["udem"].destinations]
    assert ids == ["udem_roger_gaudry", "udem_jean_brillant"]


def test_destinations_are_inside_bbox():
    min_lon, min_lat, max_lon, max_lat = config.BBOX
    for _, d in config.all_destinations():
        assert min_lon < d.lon < max_lon, d.id
        assert min_lat < d.lat < max_lat, d.id


def _km(a, b):
    # Equirectangular approximation, good to <1% at this scale.
    import math

    x = math.radians(b.lon - a.lon) * math.cos(math.radians((a.lat + b.lat) / 2))
    y = math.radians(b.lat - a.lat)
    return 6371 * math.hypot(x, y)


def test_destinations_are_plausibly_placed():
    d = {dest.id: dest for _, dest in config.all_destinations()}
    # McGill and Concordia SGW are both downtown, about 1 km apart.
    assert 0.5 < _km(d["mcgill_roddick_gates"], d["concordia_sgw_hall"]) < 1.5
    # UdeM is on the other side of Mount Royal, about 3-4 km from downtown.
    assert 2.5 < _km(d["udem_roger_gaudry"], d["mcgill_roddick_gates"]) < 4.5
    # The two UdeM buildings are about 500 m apart on the same hillside.
    assert 0.3 < _km(d["udem_roger_gaudry"], d["udem_jean_brillant"]) < 0.8


def test_departure_window_is_morning_peak():
    hour, minute = config.DEPARTURE_START_HHMM
    assert 6 <= hour <= 9 and 0 <= minute < 60
    assert 0 < config.DEPARTURE_WINDOW.total_seconds() <= 2 * 3600


def test_jvm_memory_format():
    assert config.JVM_MAX_MEMORY[:-1].isdigit() and config.JVM_MAX_MEMORY[-1] in "GM"


def test_saved_times_must_match_walk_speed():
    config.check_routing_speed({"speed_walking_kmh": config.WALK_SPEED_KMH}, "udem")
    with pytest.raises(ValueError, match="travel-times"):
        config.check_routing_speed({"speed_walking_kmh": config.WALK_SPEED_KMH + 0.8}, "udem")
    with pytest.raises(ValueError):
        config.check_routing_speed({}, "udem")
