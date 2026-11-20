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
        assert campus.osm_ref.split("/")[0] in {"node", "way"}


def test_campuses_are_inside_bbox():
    min_lon, min_lat, max_lon, max_lat = config.BBOX
    for campus in config.CAMPUSES.values():
        assert min_lon < campus.lon < max_lon, campus.id
        assert min_lat < campus.lat < max_lat, campus.id


def _km(a, b):
    # Equirectangular approximation, good to <1% at this scale.
    import math

    x = math.radians(b.lon - a.lon) * math.cos(math.radians((a.lat + b.lat) / 2))
    y = math.radians(b.lat - a.lat)
    return 6371 * math.hypot(x, y)


def test_campus_points_are_plausibly_placed():
    c = config.CAMPUSES
    # McGill and Concordia SGW are both downtown, about 1 km apart.
    assert 0.5 < _km(c["mcgill"], c["concordia_sgw"]) < 1.5
    # UdeM is on the other side of Mount Royal, about 3-4 km from downtown.
    assert 2.5 < _km(c["udem"], c["mcgill"]) < 4.5


def test_departure_window_is_morning_peak():
    hour, minute = config.DEPARTURE_START_HHMM
    assert 6 <= hour <= 9 and 0 <= minute < 60
    assert 0 < config.DEPARTURE_WINDOW.total_seconds() <= 2 * 3600


def test_jvm_memory_format():
    assert config.JVM_MAX_MEMORY[:-1].isdigit() and config.JVM_MAX_MEMORY[-1] in "GM"
