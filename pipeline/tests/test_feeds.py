"""refresh-feeds (M5.5): checks, all-or-nothing swap, archive, manifest. Fake feeds only:
agency "A", route "R", services "WK"; nothing is downloaded."""

import zipfile
from datetime import date

import pytest

from mtlhousing import config, feeds

CAL_HEADER = (
    "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date"
)


def fake_feed(path, start="20261102", end="20270103", version="V1", trips=5, skip=()):
    trip_rows = "".join(f"R,WK,T{i}\n" for i in range(trips))
    files = {
        "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\n"
        "A,Agency A,https://a.invalid,America/Toronto\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,Stop 1,45.5,-73.6\n",
        "routes.txt": "route_id,agency_id,route_type\nR,A,3\n",
        "trips.txt": "route_id,service_id,trip_id\n" + trip_rows,
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T0,08:00:00,08:00:00,S1,1\n",
        "calendar.txt": f"{CAL_HEADER}\nWK,1,1,1,1,1,0,0,{start},{end}\n",
        "feed_info.txt": "feed_publisher_name,feed_publisher_url,feed_lang,feed_version\n"
        f"P,https://p.invalid,fr,{version}\n",
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, text in files.items():
            if name not in skip:
                # fixed timestamp: the same content gives the same bytes (and sha256)
                z.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), text)
    return path


def test_inspect_reads_version_and_period(tmp_path):
    f = feeds.inspect(fake_feed(tmp_path / "x.zip"), "stm")
    assert (f.version, f.start, f.end) == ("V1", date(2026, 11, 2), date(2027, 1, 3))
    assert f.notes() == "feed_version V1; valid 20261102-20270103"
    assert len(f.sha256) == 64


@pytest.mark.parametrize("skip", [("stop_times.txt",), ("agency.txt",)])
def test_inspect_rejects_a_feed_missing_a_file(tmp_path, skip):
    with pytest.raises(ValueError, match="missing"):
        feeds.inspect(fake_feed(tmp_path / "x.zip", skip=skip), "stm")


def test_inspect_rejects_a_file_that_is_not_a_zip(tmp_path):
    bad = tmp_path / "x.zip"
    bad.write_text("<html>error page</html>")
    with pytest.raises(ValueError, match="not a zip"):
        feeds.inspect(bad, "stm")


def test_notes_keep_the_rows_other_details():
    f = feeds.FeedFile("rem", "0" * 64, "V2", date(2027, 1, 5), date(2027, 6, 30))
    old = "feed_version V1; valid 20260519-20261231; branches A1 / A3; CC BY 4.0 (__Licence.txt)"
    assert feeds.updated_notes(old, f) == (
        "feed_version V2; valid 20270105-20270630; branches A1 / A3; CC BY 4.0 (__Licence.txt)"
    )
    assert feeds.updated_notes("no feed_version; valid 20261019-20270103; lines 11", f) == (
        "feed_version V2; valid 20270105-20270630; lines 11"
    )


def manifest_rows(sha="0" * 64):
    return [
        {
            "file": f"data/raw/gtfs/{config.GTFS_FEEDS[n].name}",
            "source": n,
            "source_url": "https://old.invalid",
            "downloaded_on": "2026-01-01",
            "sha256": sha,
            "notes": "feed_version V0; valid 20260101-20261231; kept note",
        }
        for n in config.GTFS_URLS
    ] + [
        {
            "file": "data/raw/other.csv",
            "source": "x",
            "source_url": "u",
            "downloaded_on": "d",
            "sha256": "s",
            "notes": "n",
        }
    ]


def fake_get(versions, end="20270103"):
    """A downloader that writes a fake feed per URL (by feed name)."""
    by_url = {u: n for n, u in config.GTFS_URLS.items()}

    def get(url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        fake_feed(dest, version=versions[by_url[url]], end=end)

    return get


def test_check_reports_new_files_and_coming_ends(tmp_path):
    get = fake_get({"stm": "V9", "rem": "V9", "exo_trains": "V9"}, end="20261215")
    found = feeds.check(date(2026, 11, 26), tmp_path, get, manifest_rows())
    assert sum("a new file is published" in f for f in found) == 3
    assert sum("ends on 2026-12-15, 30 days or less after a check." in f for f in found) == 3
    # The same feed checked a week later gives the same line (the Issue skips repeats).
    assert feeds.check(date(2026, 12, 3), tmp_path, get, manifest_rows()) == found
    assert "the pipeline uses feed_version V0; valid 20260101-20261231" in found[0]


def test_check_is_quiet_when_nothing_changed(tmp_path):
    get = fake_get({"stm": "V1", "rem": "V1", "exo_trains": "V1"})
    sample = tmp_path / "s.zip"
    get(config.GTFS_URLS["stm"], sample)
    rows = manifest_rows(sha=feeds.sha256(sample))
    assert feeds.check(date(2026, 11, 26), tmp_path / "w", get, rows) == []


def test_refresh_swaps_archives_and_updates_the_manifest(tmp_path):
    gtfs = tmp_path / "gtfs"
    gtfs.mkdir()
    for path in config.GTFS_FEEDS.values():
        fake_feed(gtfs / path.name, version="OLD")
    manifest = tmp_path / "manifest.csv"
    feeds.write_manifest(manifest_rows(), manifest)

    get = fake_get(dict.fromkeys(config.GTFS_URLS, "NEW"))
    lines = feeds.refresh(date(2026, 11, 26), gtfs, get, manifest)

    assert all("new file (feed_version NEW" in line for line in lines)
    for name, path in config.GTFS_FEEDS.items():
        assert feeds.inspect(gtfs / path.name, name).version == "NEW"
        (archived,) = (gtfs / "archive").glob(f"{name}-OLD-*.zip")  # version + hash
        assert feeds.inspect(archived, name).version == "OLD"
    rows = {r["file"]: r for r in feeds.read_manifest(manifest)}
    stm = rows["data/raw/gtfs/stm.zip"]
    assert stm["downloaded_on"] == "2026-11-26"
    assert stm["source_url"] == config.GTFS_URLS["stm"]
    assert stm["notes"] == "feed_version NEW; valid 20261102-20270103; kept note"
    assert stm["sha256"] == feeds.sha256(gtfs / "stm.zip")
    assert rows["data/raw/other.csv"]["notes"] == "n"  # other rows untouched
    assert manifest.read_bytes().count(b"\r") == 0


def test_refresh_replaces_nothing_when_one_feed_is_bad(tmp_path):
    gtfs = tmp_path / "gtfs"
    gtfs.mkdir()
    for path in config.GTFS_FEEDS.values():
        fake_feed(gtfs / path.name, version="OLD")
    manifest = tmp_path / "manifest.csv"
    feeds.write_manifest(manifest_rows(), manifest)
    before = manifest.read_bytes()
    good = fake_get(dict.fromkeys(config.GTFS_URLS, "NEW"))

    def get(url, dest):
        if url == config.GTFS_URLS["exo_trains"]:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("<html>maintenance</html>")
        else:
            good(url, dest)

    with pytest.raises(ValueError, match="exo_trains: not a zip"):
        feeds.refresh(date(2026, 11, 26), gtfs, get, manifest)
    for name, path in config.GTFS_FEEDS.items():
        assert feeds.inspect(gtfs / path.name, name).version == "OLD"
    assert not (gtfs / "archive").exists()
    assert manifest.read_bytes() == before


def _three_old_feeds(tmp_path):
    gtfs = tmp_path / "gtfs"
    gtfs.mkdir()
    for path in config.GTFS_FEEDS.values():
        fake_feed(gtfs / path.name, version="OLD")
    manifest = tmp_path / "manifest.csv"
    feeds.write_manifest(manifest_rows(), manifest)
    return gtfs, manifest, manifest.read_bytes()


def test_refresh_replaces_nothing_when_a_current_file_is_unreadable(tmp_path):
    # M5.5 pr-reviewer: stm must not be swapped before rem's current file turns out bad.
    gtfs, manifest, before = _three_old_feeds(tmp_path)
    fake_feed(gtfs / "rem.zip", version="OLD", skip=("stops.txt",))
    with pytest.raises(ValueError, match="rem: missing stops.txt"):
        feeds.refresh(
            date(2026, 11, 26), gtfs, fake_get(dict.fromkeys(config.GTFS_URLS, "NEW")), manifest
        )
    assert feeds.inspect(gtfs / "stm.zip", "stm").version == "OLD"
    assert not (gtfs / "archive").exists()
    assert manifest.read_bytes() == before


def test_refresh_refuses_a_feed_that_has_already_ended(tmp_path):
    gtfs, manifest, before = _three_old_feeds(tmp_path)
    get = fake_get(dict.fromkeys(config.GTFS_URLS, "NEW"), end="20261120")
    with pytest.raises(ValueError, match="ended on 2026-11-20"):
        feeds.refresh(date(2026, 11, 26), gtfs, get, manifest)
    assert feeds.inspect(gtfs / "stm.zip", "stm").version == "OLD"
    assert manifest.read_bytes() == before


def test_a_reissued_version_does_not_overwrite_its_archive(tmp_path):
    gtfs, manifest, _ = _three_old_feeds(tmp_path)

    def publish(trips):  # version "V" every time, different bytes
        def get(url, dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            fake_feed(dest, version="V", trips=trips)

        return get

    for trips in (5, 6, 7):
        feeds.refresh(date(2026, 11, 26), gtfs, publish(trips), manifest)
    assert len(list((gtfs / "archive").glob("stm-V-*.zip"))) == 2


def test_refresh_leaves_an_unchanged_feed_alone(tmp_path):
    gtfs = tmp_path / "gtfs"
    gtfs.mkdir()
    for path in config.GTFS_FEEDS.values():
        fake_feed(gtfs / path.name, version="SAME")
    manifest = tmp_path / "manifest.csv"
    feeds.write_manifest(manifest_rows(), manifest)
    before = manifest.read_bytes()
    get = fake_get(dict.fromkeys(config.GTFS_URLS, "SAME"))
    lines = feeds.refresh(date(2026, 11, 26), gtfs, get, manifest)
    assert all("unchanged" in line for line in lines)
    assert not (gtfs / "archive").exists()
    assert manifest.read_bytes() == before


def test_the_archive_is_never_committed():
    # Owner, M5.5: data/raw/gtfs/archive/ is gitignored; the manifest records versions.
    ignore = (config.REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "data/raw/gtfs/archive/" in ignore
