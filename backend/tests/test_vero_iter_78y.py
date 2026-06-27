"""Iter 78y — Vero catalog regression tests.

Locks in Howard's master pricing file directive (2026-02-13):
  • Vero collapsed to 3 product types: Double Hung, 2-Lite Slider, Patio Door.
  • Vero collapsed to 3 tiers: whole-sale / Contractor / Builder-Dealer.
    one-opp removed; fallback to Builder-Dealer.
  • DH + 2-Lite Slider use a single "0-101" UI bucket each.
  • 8 adders replace the previous 12 for DH + 2-Lite Slider.
  • Gross-margin formula: sell = cost / (1 - margin%) with 35/30/25.
"""
import pytest

from vero_catalog import (
    VERO_ADDER_COSTS,
    VERO_ADDER_NAMES,
    VERO_BASE_COSTS,
    VERO_MARGIN_PCT,
    VERO_PATIO_COSTS,
    VERO_PRODUCT_TYPES,
    VERO_SINGLE_BUCKET,
    VERO_SINGLE_SISTER_COLOR,
    VERO_TIER_NAMES,
    compute_tier_price,
)


def test_one_opp_dropped_from_vero_tiers():
    """one-opp is no longer a Vero tier per Howard's directive."""
    assert "one-opp" not in VERO_TIER_NAMES
    assert VERO_TIER_NAMES == ["whole-sale", "Contractor", "Builder-Dealer"]


def test_obsolete_product_types_removed():
    """3-Lite Slider + Picture dropped per Howard's master file."""
    for obsolete in ("Vero 3-Lite Slider", "Vero Picture"):
        assert obsolete not in VERO_PRODUCT_TYPES
        assert obsolete not in VERO_ADDER_NAMES
    # Active product types only
    assert set(VERO_PRODUCT_TYPES.keys()) == {
        "Vero Double Hung",
        "Vero 2-Lite Slider",
        "Vero Patio Door",
    }


def test_dh_and_slider_share_single_ui_bucket():
    for pt in ("Vero Double Hung", "Vero 2-Lite Slider"):
        assert list(VERO_BASE_COSTS[pt].keys()) == [VERO_SINGLE_BUCKET]
        assert VERO_BASE_COSTS[pt][VERO_SINGLE_BUCKET] == 186.92


def test_dh_and_slider_have_same_8_adders():
    canonical = [
        "Quattro .25 U Factor 2 coats LoE",
        "Elite TG2 .24 U Factor 1 coat",
        "TG2 Triple Pane/Argon .19 U Factor",
        "Head Expander 0-101",
        "Grids",
        "Sentry System - Tilt Lock upgrade",
        "Integral Nail Fin 0-101",
        "Heavy Duty 1/2 Screen White ONLY",
    ]
    assert VERO_ADDER_NAMES["Vero Double Hung"] == canonical
    assert VERO_ADDER_NAMES["Vero 2-Lite Slider"] == canonical
    # Patio Door has no adders
    assert VERO_ADDER_NAMES["Vero Patio Door"] == []
    # Every adder name has a cost basis
    for n in canonical:
        assert n in VERO_ADDER_COSTS
        assert VERO_ADDER_COSTS[n] > 0


def test_patio_door_three_models():
    assert len(VERO_PATIO_COSTS) == 3
    assert all(cost > 0 for cost in VERO_PATIO_COSTS.values())
    # Largest panel costs the most
    costs = sorted(VERO_PATIO_COSTS.values())
    assert costs == [718.19, 780.29, 877.16]


def test_margin_pct_per_tier():
    assert VERO_MARGIN_PCT == {
        "whole-sale": 35,
        "Contractor": 30,
        "Builder-Dealer": 25,
    }


def test_compute_tier_price_spot_checks():
    # DH @ $186.92 cost
    assert compute_tier_price(186.92, "whole-sale") == 287.57
    assert compute_tier_price(186.92, "Contractor") == 267.03
    assert compute_tier_price(186.92, "Builder-Dealer") == 249.23
    # Patio Door 5068 @ $718.19 cost
    assert compute_tier_price(718.19, "whole-sale") == 1104.91
    assert compute_tier_price(718.19, "Contractor") == 1025.99
    assert compute_tier_price(718.19, "Builder-Dealer") == 957.59
    # Fallback for unknown tier (e.g. legacy one-opp company) → Builder-Dealer
    assert compute_tier_price(186.92, "one-opp") == 249.23
    assert compute_tier_price(186.92, "unknown-tier") == 249.23


def test_adder_costs_spot_checks():
    """Per master Excel — Howard 2026-02-13."""
    assert VERO_ADDER_COSTS["Quattro .25 U Factor 2 coats LoE"] == 37.26
    assert VERO_ADDER_COSTS["Elite TG2 .24 U Factor 1 coat"] == 55.58
    assert VERO_ADDER_COSTS["TG2 Triple Pane/Argon .19 U Factor"] == 66.76
    assert VERO_ADDER_COSTS["Head Expander 0-101"] == 3.73
    assert VERO_ADDER_COSTS["Grids"] == 30.12
    assert VERO_ADDER_COSTS["Sentry System - Tilt Lock upgrade"] == 26.70
    assert VERO_ADDER_COSTS["Integral Nail Fin 0-101"] == 13.66
    assert VERO_ADDER_COSTS["Heavy Duty 1/2 Screen White ONLY"] == 18.01
