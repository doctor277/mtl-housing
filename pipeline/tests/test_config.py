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


def test_departure_window_is_morning_peak():
    hour, minute = config.DEPARTURE_START_HHMM
    assert 6 <= hour <= 9 and 0 <= minute < 60
    assert 0 < config.DEPARTURE_WINDOW.total_seconds() <= 2 * 3600


def test_jvm_memory_format():
    assert config.JVM_MAX_MEMORY[:-1].isdigit() and config.JVM_MAX_MEMORY[-1] in "GM"
