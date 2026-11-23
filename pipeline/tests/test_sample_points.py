import zipfile

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from mtlhousing import config, sample_points

# --- extract_gaf: filter + cache ----------------------------------------------

HEADER = ",".join(f'"{c}"' for c in sample_points.GAF_COLUMNS)


def _row(cd, csd, da, lat, lon, db, pop, tot, occ, ct="0001.00"):
    return f'{cd},{cd}001,"{csd}",{ct},{da},{lat},{lon},{db},{pop},{tot},{occ}'


def _write_zip(path, rows):
    text = "\n".join([HEADER, *rows]) + "\n"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("gaf.csv", text.encode("cp1252"))


@pytest.fixture
def gaf_zip(tmp_path):
    path = tmp_path / "gaf.zip"
    _write_zip(
        path,
        [
            _row("2466", "Montréal", "1", 45.5, -73.6, "11", 10, 5, 4),
            _row("2466", "Montréal", "1", 45.5, -73.6, "12", 20, 8, 8),
            _row("2465", "Laval", "2", 45.6, -73.7, "21", 30, 9, 9),
        ],
    )
    return path


def test_extract_filters_division_and_decodes_cp1252(gaf_zip, tmp_path):
    rows = sample_points.extract_gaf(gaf_zip, tmp_path / "out.parquet", "2466")
    assert rows["dbuid"].tolist() == ["11", "12"]
    assert rows["csd_name"].iloc[0] == "Montréal"
    assert rows["ct_name"].iloc[0] == "0001.00"
    assert rows["occupied_dwellings"].sum() == 12


def test_extract_uses_cache_until_zip_changes(gaf_zip, tmp_path):
    out = tmp_path / "out.parquet"
    sample_points.extract_gaf(gaf_zip, out, "2466")
    first_mtime = out.stat().st_mtime_ns
    sample_points.extract_gaf(gaf_zip, out, "2466")
    assert out.stat().st_mtime_ns == first_mtime  # cache hit, not rewritten

    _write_zip(gaf_zip, [_row("2466", "Montréal", "9", 45.5, -73.6, "91", 1, 1, 1)])
    rows = sample_points.extract_gaf(gaf_zip, out, "2466")
    assert rows["dbuid"].tolist() == ["91"]  # rebuilt from the new zip


# --- da_points ---------------------------------------------------------------


def _gaf(rows):
    return pd.DataFrame(
        rows, columns=["dauid", "da_lat", "da_lon", "total_dwellings", "occupied_dwellings"]
    )


def test_da_points_sums_blocks_and_drops_empty_das():
    pts = sample_points.da_points(
        _gaf(
            [
                ("1", 45.5, -73.6, 5, 4),
                ("1", 45.5, -73.6, 8, 8),
                ("2", 45.6, -73.7, 3, 0),  # no residents -> dropped
            ]
        )
    )
    assert pts["point_id"].tolist() == ["da:1"]
    assert pts["weight"].iloc[0] == 12 and pts["total_dwellings"].iloc[0] == 13
    assert (pts.geometry.x.iloc[0], pts.geometry.y.iloc[0]) == (-73.6, 45.5)


def test_da_points_rejects_inconsistent_representative_point():
    with pytest.raises(ValueError, match="representative point"):
        sample_points.da_points(_gaf([("1", 45.5, -73.6, 1, 1), ("1", 45.7, -73.6, 1, 1)]))


def test_da_points_keeps_census_tract_and_rejects_a_da_in_two_tracts():
    gaf = _gaf([("1", 45.5, -73.6, 1, 1), ("1", 45.5, -73.6, 1, 1)]).assign(ct_name="0012.01")
    assert sample_points.da_points(gaf)["ct_name"].tolist() == ["0012.01"]
    gaf.loc[1, "ct_name"] = "0012.02"
    with pytest.raises(ValueError, match="more than one census tract"):
        sample_points.da_points(gaf)


def test_extract_rebuilds_when_columns_change(gaf_zip, tmp_path, monkeypatch):
    out = tmp_path / "out.parquet"
    sample_points.extract_gaf(gaf_zip, out, "2466")
    fewer = {k: v for k, v in sample_points.GAF_COLUMNS.items() if v != "ct_name"}
    monkeypatch.setattr(sample_points, "GAF_COLUMNS", fewer)
    assert "ct_name" not in sample_points.extract_gaf(gaf_zip, out, "2466")  # rebuilt


# --- build_sample_points ---------------------------------------------------------


def _quartiers():
    return gpd.GeoDataFrame(
        {"id": ["A", "B"], "name": ["Alpha", "Beta"], "dwellings": [30, 10]},
        geometry=[box(0, 0, 1, 1), box(2, 0, 3, 1)],
        crs=config.CRS_WGS84,
    )


def _points(xy_weights, csd_names=None):
    return gpd.GeoDataFrame(
        {
            "point_id": [f"da:{i}" for i in range(len(xy_weights))],
            "source": "statcan_da",
            "weight": [w for _, _, w in xy_weights],
            "total_dwellings": [w for _, _, w in xy_weights],
            "csd_name": csd_names or ["Montréal"] * len(xy_weights),
        },
        geometry=gpd.points_from_xy([x for x, _, _ in xy_weights], [y for _, y, _ in xy_weights]),
        crs=config.CRS_WGS84,
    )


def test_points_are_assigned_and_empty_quartier_gets_fallback():
    pts = _points([(0.2, 0.2, 10), (0.5, 0.5, 10), (0.8, 0.8, 10), (5, 5, 99)])
    sample, summary = sample_points.build_sample_points(pts, _quartiers(), min_points=3)

    a = sample[sample["quartier_id"] == "A"]
    assert len(a) == 3 and (a["source"] == "statcan_da").all()
    b = sample[sample["quartier_id"] == "B"]
    assert b["source"].tolist() == ["polygon_fallback"]
    assert b.geometry.iloc[0].within(box(2, 0, 3, 1))

    s = summary.set_index("quartier_id")
    assert s.loc["A", "n_points"] == 3 and not s.loc["A", "low_sample"]
    assert s.loc["A", "dwelling_ratio"] == pytest.approx(1.0)
    assert s.loc["B", "fallback"] and s.loc["B", "low_sample"] and s.loc["B", "n_points"] == 0
    assert summary.attrs["points_outside_quartiers"] == 1


def test_quartier_with_few_points_is_low_sample_without_fallback():
    pts = _points([(0.5, 0.5, 30), (2.5, 0.5, 5)])
    sample, summary = sample_points.build_sample_points(pts, _quartiers(), min_points=3)
    s = summary.set_index("quartier_id")
    assert s.loc["B", "n_points"] == 1 and s.loc["B", "low_sample"] and not s.loc["B", "fallback"]
    assert (sample["source"] == "statcan_da").all()


def test_out_of_scope_point_is_kept_marked_and_not_counted():
    pts = _points(
        [(0.2, 0.2, 10), (0.5, 0.5, 10), (0.8, 0.8, 10), (2.5, 0.5, 25)],
        csd_names=["Montréal", "Montréal", "Montréal", "Island"],
    )
    sample, summary = sample_points.build_sample_points(
        pts, _quartiers(), min_points=3, out_of_scope={"Island": "no transit"}
    )
    island = sample[sample["point_id"] == "da:3"].iloc[0]
    assert not island["in_scope"] and island["scope_note"] == "no transit"
    assert sample.loc[sample["point_id"] != "da:3", "in_scope"].all()
    s = summary.set_index("quartier_id")
    # B's only census point is out of scope: 0 counted points, a fallback point, flagged.
    assert s.loc["B", "n_points"] == 0 and s.loc["B", "n_out_of_scope"] == 1
    assert s.loc["B", "fallback"]
    assert s.loc["A", "n_out_of_scope"] == 0


# --- Integration on the real files ---------------------------------------------

real = pytest.mark.skipif(
    not (config.STATCAN_GAF_ZIP.exists() and config.QUARTIERS_GEOJSON.exists()),
    reason="raw StatCan / boundary files not downloaded",
)


@pytest.fixture(scope="module")
def real_result():
    from mtlhousing import boundaries

    quartiers = boundaries.load_quartiers()
    pts = sample_points.da_points(sample_points.extract_gaf())
    sample, summary = sample_points.build_sample_points(pts, quartiers)
    return quartiers, sample, summary


@real
def test_real_every_quartier_has_census_points(real_result):
    quartiers, sample, summary = real_result
    assert set(sample["quartier_id"]) == set(quartiers["id"])
    assert not summary["fallback"].any()
    assert summary.attrs["points_outside_quartiers"] == 0
    assert 3000 < len(sample) < 3500


@real
def test_real_ile_dorval_is_out_of_scope_in_dorval(real_result):
    quartiers, sample, summary = real_result
    out = sample[~sample["in_scope"]]
    assert out["csd_name"].tolist() == ["L'Île-Dorval"]
    dorval = quartiers.loc[quartiers["name"] == "Dorval", "id"].iloc[0]
    assert out["quartier_id"].tolist() == [dorval]
    assert "seasonal ferry" in out["scope_note"].iloc[0]
    assert summary.set_index("quartier_id").loc[dorval, "n_out_of_scope"] == 1


@real
def test_real_points_lie_inside_their_quartier(real_result):
    quartiers, sample, _ = real_result
    poly = sample["quartier_id"].map(quartiers.set_index("id").geometry)
    assert all(pt.within(pg) for pt, pg in zip(sample.geometry, poly, strict=True))


@real
def test_real_dwellings_agree_with_city_counts(real_result):
    # StatCan 2021 vs the city's (more recent) counts. Downtown has grown since 2021,
    # so allow 0.7; anything outside 0.7-1.2 would mean points landed in the wrong quartier.
    _, _, summary = real_result
    r = summary["dwelling_ratio"]
    assert 0.95 < r.median() < 1.05
    assert r.between(0.7, 1.2).all(), summary.loc[~r.between(0.7, 1.2), ["name", "dwelling_ratio"]]
