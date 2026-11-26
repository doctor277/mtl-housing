"""The M5.5 command-line options, and the --report file the weekly workflow reads
(.github/workflows/feeds.yml opens an Issue only when that file is not empty)."""

import sys

import pytest

from mtlhousing import __main__ as cli
from mtlhousing import feeds


@pytest.mark.parametrize(
    "findings, empty", [([], True), (["stm: a new file is published (fake)."], False)]
)
def test_check_report_is_empty_only_when_nothing_needs_a_refresh(
    tmp_path, monkeypatch, findings, empty
):
    monkeypatch.setattr(feeds, "check", lambda today, workdir: findings)
    report = tmp_path / "feeds.md"
    cli.step_refresh_feeds(check=True, report=str(report))
    text = report.read_text(encoding="utf-8")
    assert (text == "") is empty
    if not empty:
        assert "- stm: a new file is published (fake)." in text


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["refresh-feeds", "--check", "--report", "r.md"], ("refresh-feeds", (True, "r.md"))),
        (["refresh-feeds"], ("refresh-feeds", (False, None))),
        (["refresh", "--date", "2027-01-13"], ("refresh", ("2027-01-13", False))),
        (["refresh", "--date", "2026-12-01", "--no-download"], ("refresh", ("2026-12-01", True))),
        (["validate", "--campus", "z", "--out", "o.csv"], ("validate", ("z", "o.csv"))),
        (["validate", "--campus", "z"], ("validate", ("z", None))),
    ],
)
def test_options_reach_their_step(monkeypatch, argv, expected):
    calls = []
    name = expected[0]
    monkeypatch.setitem(cli.STEPS, name, lambda *a: calls.append((name, a)))
    monkeypatch.setattr(sys, "argv", ["python -m mtlhousing", *argv])
    cli.main()
    assert calls == [expected]
