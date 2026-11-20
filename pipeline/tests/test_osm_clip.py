import json
import shutil

import pytest

from mtlhousing import config, osm_clip

needs_osmium = pytest.mark.skipif(shutil.which("osmium") is None, reason="osmium not on PATH")

# Two nodes inside the bbox, one outside, and a way from inside to outside.
TINY_OSM = """<?xml version='1.0' encoding='UTF-8'?>
<osm version="0.6" generator="test" timestamp="2026-11-19T00:00:00Z">
  <node id="1" version="1" lat="45.50" lon="-73.60"/>
  <node id="2" version="1" lat="45.51" lon="-73.59"/>
  <node id="3" version="1" lat="46.50" lon="-72.00"/>
  <way id="10" version="1"><nd ref="1"/><nd ref="2"/><tag k="highway" v="footway"/></way>
  <way id="11" version="1"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way>
</osm>
"""

BBOX = (-73.7, 45.4, -73.5, 45.6)


def test_extract_command_uses_complete_ways_and_bbox(tmp_path):
    cmd = osm_clip.extract_command(tmp_path / "in.pbf", tmp_path / "out.pbf", BBOX)
    assert cmd[:4] == ["osmium", "extract", "--bbox", "-73.7,45.4,-73.5,45.6"]
    assert "complete_ways" in cmd and "--set-bounds" in cmd


def test_extract_command_rejects_inverted_bbox(tmp_path):
    with pytest.raises(ValueError):
        osm_clip.extract_command(tmp_path / "a", tmp_path / "b", (-73.5, 45.4, -73.7, 45.6))


def _ids(path):
    out = osm_clip.run_osmium(["cat", "-f", "opl", str(path)]).stdout
    return {line.split()[0] for line in out.splitlines() if line}


@needs_osmium
def test_clip_keeps_crossing_ways_whole_and_writes_meta(tmp_path):
    src = tmp_path / "tiny.osm"
    src.write_text(TINY_OSM, encoding="utf-8")
    dst, meta_path = tmp_path / "clip.osm.pbf", tmp_path / "clip.json"

    meta = osm_clip.clip_osm(src, dst, BBOX, meta_path)

    ids = _ids(dst)
    assert {"n1", "n2", "w10", "w11"} <= ids
    assert "n3" in ids  # complete_ways keeps the outside node of a crossing way
    assert meta["bbox"] == list(BBOX)
    assert json.loads(meta_path.read_text(encoding="utf-8")) == meta


@needs_osmium
def test_clip_is_skipped_when_meta_matches(tmp_path):
    src = tmp_path / "tiny.osm"
    src.write_text(TINY_OSM, encoding="utf-8")
    dst, meta_path = tmp_path / "clip.osm.pbf", tmp_path / "clip.json"
    osm_clip.clip_osm(src, dst, BBOX, meta_path)
    mtime = dst.stat().st_mtime_ns

    osm_clip.clip_osm(src, dst, BBOX, meta_path)
    assert dst.stat().st_mtime_ns == mtime

    osm_clip.clip_osm(src, dst, (-73.65, 45.45, -73.55, 45.55), meta_path)  # new bbox
    assert dst.stat().st_mtime_ns != mtime


@needs_osmium
@pytest.mark.skipif(not config.OSM_CLIPPED_META.exists(), reason="run `osm-clip` step first")
def test_real_clip_matches_config():
    meta = json.loads(config.OSM_CLIPPED_META.read_text(encoding="utf-8"))
    assert meta["bbox"] == list(config.BBOX)
    assert meta["source"] == config.OSM_PBF.name
    assert meta["osm_timestamp"].startswith("2026-11-19")
    assert meta["output_bytes"] < config.OSM_PBF.stat().st_size / 5
