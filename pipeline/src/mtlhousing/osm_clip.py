"""Clip the province-wide OSM extract to the study bbox with osmium.

R5 only needs the Montréal area; loading all of Québec would waste RAM and time.
`complete_ways` keeps every way that crosses the bbox whole, so streets and paths
at the edge are not cut mid-segment.

A JSON sidecar records the source hash, bbox and OSM data timestamp. The clip is
skipped when the sidecar already matches (same source file, same bbox).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from mtlhousing import config
from mtlhousing.sample_points import sha256

Bbox = tuple[float, float, float, float]


def osmium_exe() -> str:
    exe = shutil.which("osmium")
    if exe is None:
        raise RuntimeError("osmium not found; activate the mtlhousing conda env")
    return exe


def run_osmium(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run osmium with argv[0] == "osmium".

    On Windows osmium derives a subcommand from its program name, so calling it by its
    full path (ending in osmium.EXE) fails with "Unknown command or option 'osmium.EXE'".
    The full path goes in `executable` instead.
    """
    return subprocess.run(
        ["osmium", *args], executable=osmium_exe(), capture_output=True, text=True, check=check
    )


def extract_command(src: Path, dst: Path, bbox: Bbox) -> list[str]:
    left, bottom, right, top = bbox
    if not (left < right and bottom < top):
        raise ValueError(f"invalid bbox {bbox}")
    return [
        "osmium",
        "extract",
        "--bbox",
        f"{left},{bottom},{right},{top}",
        "--strategy",
        "complete_ways",
        "--set-bounds",
        "--overwrite",
        "-o",
        str(dst),
        str(src),
    ]


def header_option(path: Path, key: str) -> str | None:
    """Value of a PBF header option (e.g. 'timestamp'), or None if absent."""
    out = run_osmium(["fileinfo", "-g", f"header.option.{key}", str(path)], check=False)
    value = out.stdout.strip()
    return value if out.returncode == 0 and value else None


def osm_timestamp(path: Path) -> str | None:
    """When the OSM data was exported (Geofabrik replication timestamp)."""
    return header_option(path, "osmosis_replication_timestamp") or header_option(path, "timestamp")


def clip_osm(
    src: Path = config.OSM_PBF,
    dst: Path = config.OSM_CLIPPED_PBF,
    bbox: Bbox = config.BBOX,
    meta_path: Path = config.OSM_CLIPPED_META,
) -> dict:
    """Clip `src` to `bbox`. Returns the metadata dict (also written to `meta_path`)."""
    wanted = {"source": src.name, "source_sha256": sha256(src), "bbox": list(bbox)}
    if dst.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if {k: meta.get(k) for k in wanted} == wanted:
            return meta

    dst.parent.mkdir(parents=True, exist_ok=True)
    run_osmium(extract_command(src, dst, bbox)[1:])
    meta = {
        **wanted,
        "osm_timestamp": osm_timestamp(src),
        "output": dst.name,
        "output_bytes": dst.stat().st_size,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta
