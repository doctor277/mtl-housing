"""One command for the full commute rebuild (M5.5, `refresh --date YYYY-MM-DD`).

    refresh-feeds          download and check the schedules (skipped with --no-download)
    gtfs-check (in here)   the date must be a Tuesday or Wednesday with normal service in
                           every feed; otherwise stop, with pipeline/analysis.json untouched
    analysis.json          the new date is written
    travel-times, aggregate   for every campus (heavy: about an hour for the three campuses)
    export                 web/public/data/commute.json and neighbourhoods.geojson
    validate --out         reference only, to data/interim/refresh/ (the committed results in
                           pipeline/validation/ stay: their Google times are for their own day)
    change report          data/interim/refresh/report-<date>.md, for the PR

Each step runs as its own `python -m mtlhousing …` process: every step reads the new date
from analysis.json, and each routing run gets a fresh JVM. Any failing step stops the run.
Rents are not touched (a newer StatCan quarter is a manual check, M6).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from mtlhousing import config, gtfs_check

REFRESH_DIR = config.INTERIM_DIR / "refresh"
MOVE_MIN = 5  # report neighbourhoods whose median moved by at least this many minutes
UNREACHABLE_PTS = 5  # … or whose unreachable share moved by at least this many points

Runner = Callable[[Sequence[str]], None]


def run_step(args: Sequence[str]) -> None:
    print(f"\n$ python -m mtlhousing {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, "-m", "mtlhousing", *args], check=True)


def date_problems(day: date, feeds: list[gtfs_check.Feed]) -> list[str]:
    problems = (
        [] if day.weekday() in (1, 2) else [f"{day} is a {day:%A}, not a Tuesday or Wednesday"]
    )
    return problems + gtfs_check.check_date(feeds, day)


def write_analysis_date(day: date, path: Path = config.ANALYSIS_JSON) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["analysis_date"] = day.isoformat()
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


# --- change report ----------------------------------------------------------------------


def _median_of(values: list[float]) -> float | None:
    v = sorted(values)
    if not v:
        return None
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def change_report(old: dict, new: dict, names: dict[str, str]) -> str:
    """Markdown summary of how the commute numbers moved between two commute.json files."""
    om, nm = old["meta"], new["meta"]
    lines = [
        f"# Commute refresh: {om['analysis_date']} → {nm['analysis_date']}",
        "",
        "| Feed | Before | After |",
        "|---|---|---|",
    ]
    feeds_old = {f["name"]: f for f in om["gtfs_feeds"]}
    for f in nm["gtfs_feeds"]:
        o = feeds_old.get(f["name"], {})
        lines.append(
            f"| {f['name']} | {o.get('version') or '-'} ({o.get('start')}–{o.get('end')}) "
            f"| {f.get('version') or '-'} ({f['start']}–{f['end']}) |"
        )
    if old["results"] == new["results"]:
        lines += ["", "**No commute number changed.**", ""]
        return "\n".join(lines)
    for campus in nm["campuses"]:
        moved, unreach, deltas, gone, added = [], [], [], [], []
        for qid in sorted(set(old["results"]) | set(new["results"])):
            o = old["results"].get(qid, {}).get(campus)
            n = new["results"].get(qid, {}).get(campus)
            name = names.get(qid, qid)
            if o and not n:
                gone.append(name)
                continue
            if n and not o:
                added.append(name)
                continue
            if not (o and n):
                continue
            if o["median"] is not None and n["median"] is not None:
                d = n["median"] - o["median"]
                deltas.append(d)
                if abs(d) >= MOVE_MIN:
                    moved.append((d, name, o["median"], n["median"]))
            elif o["median"] != n["median"]:
                moved.append((0.0, name, o["median"], n["median"]))
            ou, nu = o.get("unreachable_share"), n.get("unreachable_share")
            if ou is not None and nu is not None and abs(nu - ou) * 100 >= UNREACHABLE_PTS:
                unreach.append(f"{name}: {ou:.0%} → {nu:.0%}")
        med = _median_of(deltas)
        lines += [
            "",
            f"## {campus}",
            "",
            f"- Neighbourhoods compared: {len(deltas)}; median change {med:+.1f} min"
            if med is not None
            else "- No neighbourhood to compare.",
            f"- Faster: {sum(d < 0 for d in deltas)}, slower: {sum(d > 0 for d in deltas)}, "
            f"unchanged: {sum(d == 0 for d in deltas)}",
        ]
        if moved:
            lines += ["", f"Moved by {MOVE_MIN} min or more (median, before → after):", ""]
            for d, name, a, b in sorted(moved, key=lambda t: -abs(t[0])):
                lines.append(
                    f"- {name}: {a} → {b}"
                    + (f" ({d:+.1f})" if a is not None and b is not None else "")
                )
        if unreach:
            lines += ["", f"Unreachable share moved by {UNREACHABLE_PTS} points or more:", ""]
            lines += [f"- {u}" for u in unreach]
        if gone or added:
            lines += [
                "",
                f"- No longer with results: {', '.join(gone) or 'none'}; "
                f"newly with results: {', '.join(added) or 'none'}",
            ]
    return "\n".join(lines) + "\n"


def quartier_names(geojson: Path) -> dict[str, str]:
    gj = json.loads(geojson.read_text(encoding="utf-8"))
    return {f["properties"]["id"]: f["properties"]["name"] for f in gj["features"]}


# --- the command ------------------------------------------------------------------------


def run(
    day: date,
    download: bool = True,
    step: Runner = run_step,
    analysis_json: Path = config.ANALYSIS_JSON,
    commute_json: Path = config.WEB_DATA_DIR / "commute.json",
    geojson: Path = config.WEB_DATA_DIR / "neighbourhoods.geojson",
    out_dir: Path = REFRESH_DIR,
    feeds_loader: Callable[[], list[gtfs_check.Feed]] | None = None,
) -> Path:
    """The whole rebuild; returns the change report's path. Stops at the first failure."""
    if download:
        step(["refresh-feeds"])
    feeds = (feeds_loader or _load_feeds)()
    problems = date_problems(day, feeds)
    if problems:
        raise SystemExit(f"{day} can't be the analysis date: " + "; ".join(problems))
    old = json.loads(commute_json.read_text(encoding="utf-8"))
    write_analysis_date(day, analysis_json)
    for campus in config.CAMPUSES:
        step(["travel-times", "--campus", campus])
        step(["aggregate", "--campus", campus])
    step(["export"])
    out_dir.mkdir(parents=True, exist_ok=True)
    for campus in config.CAMPUSES:
        out = out_dir / f"validate_{campus}_{day}.csv"
        step(["validate", "--campus", campus, "--out", str(out)])
    new = json.loads(commute_json.read_text(encoding="utf-8"))
    report = out_dir / f"report-{day}.md"
    report.write_text(
        change_report(old, new, quartier_names(geojson)), encoding="utf-8", newline="\n"
    )
    return report


def _load_feeds() -> list[gtfs_check.Feed]:
    return [gtfs_check.load_feed(p, n) for n, p in config.GTFS_FEEDS.items()]
