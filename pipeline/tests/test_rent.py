import math

import pytest

from mtlhousing.rent import CmhcRent, choose_source

NAN = math.nan
SUPPRESSED = CmhcRent(NAN, None)


def r(rent, grade):
    return CmhcRent(float(rent), grade)


@pytest.mark.parametrize(
    "nbhd, zone, level, rent, reliability",
    [
        # a/b/c at the neighbourhood wins, even over a better zone grade
        (r(1000, "c"), r(1100, "a"), "neighbourhood", 1000, "ok"),
        # neighbourhood d or ** -> zone a/b/c beats any grade d
        (r(1000, "d"), r(1100, "b"), "zone", 1100, "ok"),
        (SUPPRESSED, r(1100, "a"), "zone", 1100, "ok"),
        # no a/b/c anywhere -> grade d, neighbourhood first
        (r(1000, "d"), r(1100, "d"), "neighbourhood", 1000, "low"),
        (r(1000, "d"), SUPPRESSED, "neighbourhood", 1000, "low"),
        (SUPPRESSED, r(1100, "d"), "zone", 1100, "low"),
        # ** at both levels -> not enough data
        (SUPPRESSED, SUPPRESSED, None, NAN, None),
    ],
)
def test_source_order(nbhd, zone, level, rent, reliability):
    s = choose_source(nbhd, zone)
    assert s.level == level and s.reliability == reliability
    assert (math.isnan(s.rent) and math.isnan(rent)) or s.rent == rent


def test_suppressed_is_never_used_even_with_a_stray_value():
    # a rent without a grade (or a grade without a rent) is treated as suppressed
    assert choose_source(CmhcRent(999.0, None), SUPPRESSED).level is None
    assert choose_source(CmhcRent(NAN, "a"), SUPPRESSED).level is None
    # pandas gives NaN, not None, for a missing grade
    assert choose_source(CmhcRent(NAN, NAN), r(1100, "d")).level == "zone"
