import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon, box

from mtlhousing import boundaries, config

# --- Unit tests on tiny in-memory fixtures -----------------------------------

BOWTIE = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])  # self-intersecting


def _raw(rows):
    return gpd.GeoDataFrame(
        {k: [r[k] for r in rows] for k in ("no_qr", "nom_qr", "nom_arr", "nom_mun")},
        geometry=[r["geometry"] for r in rows],
        crs="EPSG:4326",
    )


def _fixture():
    raw = _raw(
        [
            dict(no_qr="02", nom_qr="B", nom_arr="Arr X", nom_mun="Montréal", geometry=BOWTIE),
            dict(
                no_qr="01", nom_qr="A", nom_arr=None, nom_mun="Westmount", geometry=box(2, 0, 3, 1)
            ),
        ]
    )
    log = pd.DataFrame({"No_QR": ["01", "02"], "Nb_log": ["100", "250"]})
    return raw, log


def test_normalise_columns_order_and_values():
    q = boundaries.normalise_quartiers(*_fixture())
    assert list(q.columns) == boundaries.COLUMNS
    assert q["id"].tolist() == ["01", "02"]  # sorted by id
    assert q.crs.equals(config.CRS_WGS84)


def test_ville_liee_borough_falls_back_to_municipality():
    q = boundaries.normalise_quartiers(*_fixture()).set_index("id")
    assert q.loc["01", "borough"] == "Westmount"
    assert q.loc["02", "borough"] == "Arr X"


def test_dwellings_are_joined_by_id_as_int():
    q = boundaries.normalise_quartiers(*_fixture()).set_index("id")
    assert q.loc["01", "dwellings"] == 100 and q.loc["02", "dwellings"] == 250


def test_invalid_geometry_is_repaired_to_multipolygon():
    q = boundaries.normalise_quartiers(*_fixture())
    assert q.is_valid.all()
    assert (q.geom_type == "MultiPolygon").all()
    assert q.set_index("id").loc["02", "geometry"].area == pytest.approx(0.5)


def test_id_mismatch_with_csv_raises():
    raw, log = _fixture()
    log.loc[0, "No_QR"] = "99"
    with pytest.raises(ValueError, match="differ"):
        boundaries.normalise_quartiers(raw, log)


def test_duplicate_ids_raise():
    raw, log = _fixture()
    raw.loc[1, "no_qr"] = "02"
    with pytest.raises(ValueError, match="duplicate"):
        boundaries.normalise_quartiers(raw, log)


# --- Integration test on the real downloaded file ------------------------------

real = pytest.mark.skipif(
    not (config.QUARTIERS_GEOJSON.exists() and config.LOGEMENTS_CSV.exists()),
    reason="raw boundary files not downloaded",
)

AGGLO_MUNICIPALITIES = {
    "Montréal", "Baie-D'Urfé", "Beaconsfield", "Côte-Saint-Luc", "Dollard-Des Ormeaux",
    "Dorval", "Hampstead", "Kirkland", "Montréal-Est", "Montréal-Ouest", "Mont-Royal",
    "Pointe-Claire", "Sainte-Anne-de-Bellevue", "Senneville", "Westmount",
}  # fmt: skip
# L'Île-Dorval (seasonal, no transit) is not in the city's layer; see docs/methodology.md.


@pytest.fixture(scope="module")
def quartiers():
    return boundaries.load_quartiers()


@real
def test_real_file_shape(quartiers):
    assert len(quartiers) == 91
    assert quartiers["id"].is_unique
    assert quartiers.is_valid.all() and not quartiers.is_empty.any()
    assert (quartiers.geom_type == "MultiPolygon").all()
    assert quartiers[["name", "borough", "municipality"]].notna().all().all()


@real
def test_real_file_covers_the_agglomeration(quartiers):
    assert set(quartiers["municipality"]) == AGGLO_MUNICIPALITIES
    assert 950_000 < quartiers["dwellings"].sum() < 1_100_000


@real
def test_real_file_has_no_significant_overlaps(quartiers):
    # Source has digitising slivers up to a few hundred m²; anything ≥ 1000 m² is a real error.
    assert boundaries.find_overlaps(quartiers, min_area_m2=1000) == []
