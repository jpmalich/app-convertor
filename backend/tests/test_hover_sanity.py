"""Iter 78o — sanity-check rules unit tests."""
from routes.hover_sanity import run_checks


def _codes(m: dict) -> set[str]:
    return {w["code"] for w in run_checks(m)}


def test_no_warnings_on_clean_report():
    """A typical Pittsburgh ranch home should pass every rule."""
    m = {
        "siding_sqft": 1800, "soffit_sqft": 144, "eaves_lf": 144,
        "rakes_lf": 120, "overhang_in": 12,
        "window_count": 10, "door_count": 3,
        "entry_door_count": 1, "patio_door_count": 1, "garage_door_count": 1,
        "opening_perimeter_lf": 220,
        "outside_corner_count": 6, "inside_corner_count": 2,
    }
    assert _codes(m) == set()


def test_soffit_mismatch_flagged():
    """Soffit too large vs eaves × overhang → flag."""
    m = {"eaves_lf": 100, "soffit_sqft": 250, "overhang_in": 12}  # expected ~100
    assert "soffit_area_mismatch" in _codes(m)


def test_soffit_match_passes():
    m = {"eaves_lf": 100, "soffit_sqft": 110, "overhang_in": 12}  # 10% off, ok
    assert "soffit_area_mismatch" not in _codes(m)


def test_rake_eave_ratio_high_flagged():
    m = {"eaves_lf": 100, "rakes_lf": 200}  # ratio 2.0
    assert "rake_eave_ratio" in _codes(m)


def test_rake_eave_ratio_normal_passes():
    m = {"eaves_lf": 100, "rakes_lf": 100}
    assert "rake_eave_ratio" not in _codes(m)


def test_door_count_mismatch():
    m = {
        "door_count": 5,
        "entry_door_count": 1, "patio_door_count": 1, "garage_door_count": 1,
    }
    assert "door_count_mismatch" in _codes(m)


def test_door_count_consistent():
    m = {
        "door_count": 3,
        "entry_door_count": 1, "patio_door_count": 1, "garage_door_count": 1,
    }
    assert "door_count_mismatch" not in _codes(m)


def test_too_many_outside_corners():
    m = {"outside_corner_count": 16}
    assert "too_many_outside_corners" in _codes(m)


def test_inside_gt_outside_info():
    m = {"inside_corner_count": 5, "outside_corner_count": 2}
    assert "inside_gt_outside_corners" in _codes(m)


def test_opening_perim_mismatch():
    # 10 windows + 1 entry: expected ~ 10×14 + 19 = 159 LF
    # Reported 400 LF → 60%+ delta
    m = {
        "window_count": 10, "entry_door_count": 1,
        "opening_perimeter_lf": 400,
    }
    assert "opening_perim_mismatch" in _codes(m)


def test_empty_dict_no_crash():
    assert run_checks({}) == []


def test_non_dict_no_crash():
    assert run_checks(None) == []
    assert run_checks([]) == []
