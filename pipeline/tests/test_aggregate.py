import math

import numpy as np
import pandas as pd
import pytest

from mtlhousing import aggregate, config

INF = math.inf

# --- weighted_quantile ------------------------------------------------------------


def test_weighted_quantile_equal_weights_is_inverse_cdf():
    v, w = [10, 20, 30, 40], [1, 1, 1, 1]
    assert aggregate.weighted_quantile(v, w, 0.5) == 20  # lower median, no interpolation
    assert aggregate.weighted_quantile(v, w, 0.1) == 10
    assert aggregate.weighted_quantile(v, w, 0.9) == 40


def test_weighted_quantile_follows_weights():
    # 75% of dwellings at 10 min -> median is 10 even though half the points are 20.
    assert aggregate.weighted_quantile([10, 20], [3, 1], 0.5) == 10
    assert aggregate.weighted_quantile([10, 20], [1, 3], 0.5) == 20


def test_weighted_quantile_unreachable_ranks_last():
    v, w = [10, 20, INF], [1, 1, 1]
    assert aggregate.weighted_quantile(v, w, 0.5) == 20
    assert aggregate.weighted_quantile(v, w, 0.9) == INF  # p90 is "more than max"
    assert aggregate.weighted_quantile([INF, INF], [1, 1], 0.5) == INF


def test_weighted_quantile_empty_is_nan():
    assert math.isnan(aggregate.weighted_quantile([], [], 0.5))


def test_weighted_quantile_is_scale_invariant_and_monotone():
    rng = np.random.default_rng(0)
    for _ in range(50):
        v = rng.integers(5, 120, size=rng.integers(1, 30)).astype(float)
        w = rng.integers(1, 900, size=v.size).astype(float)
        qs = [aggregate.weighted_quantile(v, w, q) for q in (0.1, 0.5, 0.9)]
        assert qs == sorted(qs)
        assert all(v.min() <= x <= v.max() for x in qs)
        assert qs == [aggregate.weighted_quantile(v, w * 7.5, q) for q in (0.1, 0.5, 0.9)]


# --- adjustments and per-home fastest ----------------------------------------------


def _times(rows):
    return pd.DataFrame(rows, columns=["point_id", "destination_id", "travel_time_min"])


def test_negative_adjustment_never_goes_below_zero():
    t = _times([("a", "x", 10.0), ("b", "x", 1.0), ("c", "x", np.nan)])
    out = aggregate.apply_access_adjustments(t, {"x": -1.5})
    assert out["travel_time_min"].tolist()[:2] == [8.5, 0.0]
    assert np.isnan(out["travel_time_min"].iloc[2])


def test_adjustment_applies_to_one_destination_and_keeps_nan():
    t = _times([("a", "x", 10.0), ("a", "y", 10.0), ("b", "x", np.nan)])
    out = aggregate.apply_access_adjustments(t, {"x": 2.2})
    assert out["travel_time_min"].tolist()[:2] == [12.2, 10.0]
    assert np.isnan(out["travel_time_min"].iloc[2])
    assert out["travel_time_raw_min"].tolist()[:2] == [10.0, 10.0]


def test_per_home_fastest_treats_unreachable_as_inf():
    t = _times(
        [
            ("a", "x", 12.0),
            ("a", "y", 10.0),
            ("b", "x", 30.0),
            ("b", "y", np.nan),
            ("c", "x", np.nan),
            ("c", "y", np.nan),
        ]
    )
    wide = aggregate.per_home(t, ["x", "y"])
    assert wide.loc["a", "fastest"] == 10 and wide.loc["a", "fastest_destination"] == "y"
    assert wide.loc["b", "fastest"] == 30 and wide.loc["b", "fastest_destination"] == "x"
    assert wide.loc["c", "fastest"] == INF and pd.isna(wide.loc["c", "fastest_destination"])


# --- quartier_stats --------------------------------------------------------------


def _sample(rows):
    return pd.DataFrame(rows, columns=["point_id", "quartier_id", "weight", "in_scope"])


def test_quartier_stats_end_to_end_on_udem_ids():
    rg, jb = "udem_roger_gaudry", "udem_jean_brillant"
    times = _times(
        [
            ("p1", rg, 20.0), ("p1", jb, 21.0),  # RG faster before adjustment, JB after (+2.2)
            ("p2", rg, 30.0), ("p2", jb, 40.0),
            ("p3", rg, 50.0), ("p3", jb, np.nan),
            ("p4", rg, np.nan), ("p4", jb, np.nan),  # unreachable
            ("out", rg, 5.0), ("out", jb, 5.0),  # out of scope -> ignored
        ]
    )  # fmt: skip
    sample = _sample(
        [
            ("p1", "Q", 100, True),
            ("p2", "Q", 100, True),
            ("p3", "Q", 100, True),
            ("p4", "Q", 100, True),
            ("out", "Q", 1000, False),
        ]
    )
    stats = aggregate.quartier_stats(times, sample, "udem", adjustments={rg: 2.2})
    s = stats.set_index("target")

    f = s.loc["fastest"]
    # fastest per home: p1 21 (JB), p2 32.2 (RG), p3 52.2 (RG), p4 inf
    assert f["median"] == pytest.approx(32.2) and f["p10"] == 21 and f["p90"] == INF
    assert f["n_points"] == 4 and f["n_unreachable"] == 1
    assert f["unreachable_share"] == pytest.approx(0.25)
    assert f["flags"] == ["many_unreachable"]

    assert s.loc[rg, "fastest_share"] == pytest.approx(0.5)
    assert s.loc[jb, "fastest_share"] == pytest.approx(0.25)
    assert s.loc[jb, "n_unreachable"] == 2
    assert set(stats["target"]) == {"fastest", rg, jb}


def test_low_sample_flag():
    rg, jb = "udem_roger_gaudry", "udem_jean_brillant"
    times = _times([("p1", rg, 10.0), ("p1", jb, 12.0)])
    stats = aggregate.quartier_stats(times, _sample([("p1", "Q", 5, True)]), "udem", {})
    assert stats.set_index("target").loc["fastest", "flags"] == ["low_sample"]


# --- Integration on the real UdeM results ----------------------------------------

real = pytest.mark.skipif(
    not config.travel_times_parquet("udem").exists(), reason="run travel-times first"
)


@pytest.fixture(scope="module")
def real_stats():
    import geopandas as gpd

    from mtlhousing import boundaries

    times = pd.read_parquet(config.travel_times_parquet("udem"))
    sample = gpd.read_parquet(config.SAMPLE_POINTS_PARQUET)
    names = boundaries.load_quartiers().set_index("id")["name"]
    stats = aggregate.quartier_stats(times, sample, "udem")
    return stats.assign(name=stats["quartier_id"].map(names))


@real
def test_real_every_quartier_has_three_targets(real_stats):
    assert real_stats["quartier_id"].nunique() == 91
    assert len(real_stats) == 91 * 3
    f = real_stats[real_stats["target"] == "fastest"].set_index("name")
    assert f.loc["Édouard-Montpetit", "median"] < 15
    assert "low_sample" in f.loc["Senneville", "flags"]
    assert f.loc["Dorval", "n_unreachable"] == 0  # L'Île-Dorval is out of scope, not unreachable


@real
def test_real_fastest_is_never_slower_than_either_building(real_stats):
    wide = real_stats.pivot(index="quartier_id", columns="target", values="median")
    assert (wide["fastest"] <= wide["udem_roger_gaudry"]).all()
    assert (wide["fastest"] <= wide["udem_jean_brillant"]).all()
