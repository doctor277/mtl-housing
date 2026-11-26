"""refresh (M5.5): the date gate, the step order, and the change report. Fake data only:
quartiers "A"/"B"/"C", campus "udem" with made-up minutes; no routing runs."""

import json
from datetime import date

import pytest

from mtlhousing import config, refresh


def commute(day, results, version="V1"):
    return {
        "meta": {
            "analysis_date": day,
            "gtfs_feeds": [{"name": "stm", "version": version, "start": "s", "end": "e"}],
            "campuses": {"udem": {}},
        },
        "results": results,
    }


def r(median, unreachable=0.0):
    return {"median": median, "unreachable_share": unreachable}


NAMES = {"A": "Quartier A", "B": "Quartier B", "C": "Quartier C"}


def test_report_says_when_nothing_changed():
    same = {"A": {"udem": r(20.0)}}
    text = refresh.change_report(commute("2026-12-01", same), commute("2026-12-01", same), NAMES)
    assert "**No commute number changed.**" in text
    assert "| stm | V1 (s–e) | V1 (s–e) |" in text


def test_report_lists_moves_and_unreachable_changes():
    before = {"A": {"udem": r(20.0)}, "B": {"udem": r(30.0, 0.0)}, "C": {"udem": r(40.0)}}
    after = {"A": {"udem": r(27.5)}, "B": {"udem": r(31.0, 0.2)}, "C": {"udem": r(38.0)}}
    text = refresh.change_report(
        commute("2026-12-01", before), commute("2027-01-13", after, version="V2"), NAMES
    )
    assert text.startswith("# Commute refresh: 2026-12-01 → 2027-01-13")
    assert "| stm | V1 (s–e) | V2 (s–e) |" in text
    assert "median change +1.0 min" in text
    assert "Faster: 1, slower: 2, unchanged: 0" in text
    assert "- Quartier A: 20.0 → 27.5 (+7.5)" in text
    assert "Quartier B: 0% → 20%" in text
    assert "Quartier C: 40.0" not in text  # moved by less than 5 min


@pytest.fixture
def files(tmp_path):
    analysis = tmp_path / "analysis.json"
    analysis.write_text(json.dumps({"analysis_date": "2026-12-01", "note": "n"}), encoding="utf-8")
    commute_json = tmp_path / "commute.json"
    one = commute("2026-12-01", {"A": {"udem": r(20.0)}})
    commute_json.write_text(json.dumps(one), encoding="utf-8")
    geo = tmp_path / "n.geojson"
    features = [{"properties": {"id": "A", "name": "Quartier A"}}]
    geo.write_text(json.dumps({"features": features}), encoding="utf-8")
    return analysis, commute_json, geo, tmp_path / "out"


def run(day, files, step, download=False):
    analysis, commute_json, geo, out = files
    return refresh.run(
        day,
        download=download,
        step=step,
        analysis_json=analysis,
        commute_json=commute_json,
        geojson=geo,
        out_dir=out,
        feeds_loader=lambda: [],
    )


def test_refresh_runs_every_step_in_order_and_writes_the_report(files):
    out = files[3]
    calls = []
    report = run(date(2026, 12, 1), files, calls.append, download=True)
    expected = [["refresh-feeds"]]
    for c in config.CAMPUSES:
        expected += [["travel-times", "--campus", c], ["aggregate", "--campus", c]]
    expected += [["export"]]
    for c in config.CAMPUSES:
        validate_csv = out / f"validate_{c}_2026-12-01.csv"
        expected += [["validate", "--campus", c, "--out", str(validate_csv)]]
    assert calls == expected
    assert report == out / "report-2026-12-01.md"
    assert "**No commute number changed.**" in report.read_text(encoding="utf-8")


def test_refresh_without_download_skips_the_feeds(files):
    calls = []
    run(date(2026, 12, 1), files, calls.append)
    assert ["refresh-feeds"] not in calls


def test_a_rejected_date_stops_before_anything_changes(files):
    analysis = files[0]
    calls = []
    before = analysis.read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match="2026-12-04 is a Friday"):
        run(date(2026, 12, 4), files, calls.append)
    assert calls == []
    assert analysis.read_text(encoding="utf-8") == before


def test_the_new_date_is_written_before_routing(files):
    analysis = files[0]
    seen = []

    def step(args):
        if args[0] == "travel-times":
            seen.append(config.read_analysis_date(analysis))

    run(date(2027, 1, 13), files, step)
    assert seen and set(seen) == {date(2027, 1, 13)}
    assert json.loads(analysis.read_text(encoding="utf-8"))["note"] == "n"  # the note is kept
