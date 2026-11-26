"""Download, check and swap the GTFS schedule feeds (M5.5, `refresh-feeds`).

- `inspect`: a downloaded file must be a valid zip with the GTFS files routing needs; it
  reports the feed's version and service period.
- `check` (`refresh-feeds --check`): downloads each feed to a temporary place and reports
  whether it differs from the version recorded in data/manifest.csv, or expires within
  EXPIRY_WARN_DAYS. It changes nothing; the weekly GitHub Actions job runs it.
- `refresh` (`refresh-feeds`): downloads and checks every feed first; only if all three are
  good does it archive the current files (data/raw/gtfs/archive/, gitignored), put the new
  ones in place and update the manifest. Any failure stops before anything is replaced, so
  old data is never reused silently and never half-swapped.

The download addresses are config.GTFS_URLS (checked 2026-11-25: the STM's fixed address
serves the same file as its open-data page).
"""

from __future__ import annotations

import csv
import hashlib
import io
import shutil
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mtlhousing import config, gtfs_check

EXPIRY_WARN_DAYS = 30
# Files routing needs; a feed also needs calendar.txt or calendar_dates.txt (gtfs_check).
REQUIRED = ("agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt")
USER_AGENT = "mtl-housing-pipeline (GTFS refresh)"

Downloader = Callable[[str, Path], None]


@dataclass(frozen=True)
class FeedFile:
    name: str
    sha256: str
    version: str | None
    start: date
    end: date

    def notes(self) -> str:
        v = f"feed_version {self.version}" if self.version else "no feed_version"
        return f"{v}; valid {self.start:%Y%m%d}-{self.end:%Y%m%d}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    """Fetch `url` to `dest` (through a .part file, so a cut download never looks whole)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as r, part.open("wb") as f:
        shutil.copyfileobj(r, f)
    part.replace(dest)


def inspect(path: Path, name: str) -> FeedFile:
    """Check a downloaded feed and describe it. Raises ValueError on anything wrong."""
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            names = set(z.namelist())
    except zipfile.BadZipFile as e:
        raise ValueError(f"{name}: not a zip file ({e})") from e
    if bad:
        raise ValueError(f"{name}: corrupt file in the zip: {bad}")
    missing = [f for f in REQUIRED if f not in names]
    if missing:
        raise ValueError(f"{name}: missing {', '.join(missing)}")
    feed = gtfs_check.load_feed(path, name)
    start, end = gtfs_check.service_range(feed)
    version = (feed.feed_info or {}).get("feed_version")
    if version is not None and str(version) in ("", "nan"):
        version = None
    return FeedFile(name, sha256(path), str(version) if version else None, start, end)


# --- manifest -------------------------------------------------------------------------


def manifest_key(name: str) -> str:
    return f"data/raw/gtfs/{config.GTFS_FEEDS[name].name}"


def read_manifest(path: Path = config.MANIFEST_CSV) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_manifest(rows: list[dict[str, str]], path: Path = config.MANIFEST_CSV) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")


def updated_notes(old: str, feed: FeedFile) -> str:
    """The feed's version and period first; any other note the row had is kept."""
    keep = [
        p
        for p in (s.strip() for s in old.split(";"))
        if p and not p.startswith(("feed_version", "no feed_version", "valid "))
    ]
    return "; ".join([feed.notes(), *keep])


def update_manifest(
    rows: list[dict[str, str]], feeds: list[FeedFile], downloaded_on: date
) -> list[dict[str, str]]:
    by_key = {manifest_key(f.name): f for f in feeds}
    out = []
    for r in rows:
        f = by_key.get(r["file"])
        if f:
            r = {
                **r,
                "source_url": config.GTFS_URLS[f.name],
                "downloaded_on": downloaded_on.isoformat(),
                "sha256": f.sha256,
                "notes": updated_notes(r["notes"], f),
            }
        out.append(r)
    missing = set(by_key) - {r["file"] for r in rows}
    if missing:
        raise ValueError(f"manifest has no row for {sorted(missing)}")
    return out


# --- check and refresh ------------------------------------------------------------------


def check(
    today: date,
    workdir: Path,
    get: Downloader = download,
    manifest: list[dict[str, str]] | None = None,
) -> list[str]:
    """What needs attention, one line per feed: a new version, or an end of service within
    EXPIRY_WARN_DAYS. Empty when nothing does. Raises on a failed download or a bad file."""
    rows = {r["file"]: r for r in (manifest if manifest is not None else read_manifest())}
    findings = []
    for name, url in config.GTFS_URLS.items():
        path = workdir / f"{name}.zip"
        get(url, path)
        feed = inspect(path, name)
        pinned = rows[manifest_key(name)]
        if feed.sha256 != pinned["sha256"]:
            used = "; ".join(s.strip() for s in pinned["notes"].split(";")[:2])
            findings.append(
                f"{name}: a new file is published ({feed.notes()}); the pipeline uses {used}."
            )
        days = (feed.end - today).days
        if days <= EXPIRY_WARN_DAYS:
            findings.append(
                f"{name}: the published feed ends on {feed.end} ({days} days from {today})."
            )
    return findings


def refresh(
    today: date,
    gtfs_dir: Path = config.GTFS_DIR,
    get: Downloader = download,
    manifest_path: Path = config.MANIFEST_CSV,
) -> list[str]:
    """Download, check, then archive and swap all three feeds; update the manifest.
    Returns one line per feed. Nothing is replaced unless every feed downloaded and
    passed its checks."""
    incoming = gtfs_dir / ".incoming"
    new: dict[str, FeedFile] = {}
    for name, url in config.GTFS_URLS.items():
        path = incoming / f"{name}.zip"
        get(url, path)
        new[name] = inspect(path, name)  # raises: nothing below runs

    lines = []
    changed = []
    for name, feed in new.items():
        current = gtfs_dir / config.GTFS_FEEDS[name].name
        if current.exists() and sha256(current) == feed.sha256:
            (incoming / f"{name}.zip").unlink()
            lines.append(f"{name}: unchanged ({feed.notes()})")
            continue
        if current.exists():
            old = inspect(current, name)
            label = old.version or old.sha256[:12]
            archive = gtfs_dir / "archive" / f"{name}-{label}.zip"
            archive.parent.mkdir(parents=True, exist_ok=True)
            current.replace(archive)
            lines.append(
                f"{name}: new file ({feed.notes()}); previous kept as archive/{archive.name}"
            )
        else:
            lines.append(f"{name}: downloaded ({feed.notes()})")
        (incoming / f"{name}.zip").replace(current)
        changed.append(feed)
    if changed:
        write_manifest(update_manifest(read_manifest(manifest_path), changed, today), manifest_path)
    return lines
