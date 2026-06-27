"""Iter 78y — regenerate vero_seed_prices.json from the canonical cost
basis in vero_catalog.py. Run from /app/backend:
    python build_vero_seed.py
The migration in services.py force-writes these values into
db.vero_prices on boot regardless of what's already there.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vero_catalog import (
    VERO_ADDER_COSTS,
    VERO_ADDER_NAMES,
    VERO_BASE_COSTS,
    VERO_PATIO_COSTS,
    VERO_PRODUCT_TYPES,
    VERO_SINGLE_BUCKET,
    VERO_SINGLE_SISTER_COLOR,
    VERO_TIER_NAMES,
    compute_tier_price,
)


def build_product(tier: str, pt: str) -> dict:
    sizing = VERO_PRODUCT_TYPES[pt]["sizing"]
    if sizing == "ui_bucket":
        cost_by_bucket = VERO_BASE_COSTS.get(pt, {})
        base_prices = {
            bucket: {VERO_SINGLE_SISTER_COLOR: compute_tier_price(cost, tier)}
            for bucket, cost in cost_by_bucket.items()
        }
        # Adders: same 8, computed per tier, replicated across all buckets
        # in this product (currently only one bucket "0-101").
        adder_prices = {}
        for adder_name in VERO_ADDER_NAMES.get(pt, []):
            adder_cost = VERO_ADDER_COSTS.get(adder_name, 0.0)
            adder_prices[adder_name] = {
                bucket: compute_tier_price(adder_cost, tier)
                for bucket in cost_by_bucket.keys()
            }
        return {
            "_sister_colors": [VERO_SINGLE_SISTER_COLOR],
            "_buckets": list(cost_by_bucket.keys()),
            "base_prices": base_prices,
            "adder_prices": adder_prices,
        }
    # Patio Door — fixed model
    patio_prices = {
        model: {VERO_SINGLE_SISTER_COLOR: compute_tier_price(cost, tier)}
        for model, cost in VERO_PATIO_COSTS.items()
    }
    return {
        "_sister_colors": [VERO_SINGLE_SISTER_COLOR],
        "_models": list(VERO_PATIO_COSTS.keys()),
        "patio_prices": patio_prices,
        "adder_prices": {},
    }


def main() -> None:
    out = {}
    for tier in VERO_TIER_NAMES:
        out[tier] = {pt: build_product(tier, pt) for pt in VERO_PRODUCT_TYPES.keys()}

    target = Path(__file__).parent / "vero_seed_prices.json"
    with open(target, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {target}")
    # Quick sanity
    for tier in VERO_TIER_NAMES:
        dh = out[tier]["Vero Double Hung"]["base_prices"]["0-101"][VERO_SINGLE_SISTER_COLOR]
        print(f"  {tier:<16} Vero DH UI 0-101 = ${dh:.2f}")


if __name__ == "__main__":
    main()
