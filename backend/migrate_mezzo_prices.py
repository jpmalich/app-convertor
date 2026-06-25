"""One-shot migration: force-update `db.mezzo_prices` for the 3 tiers
Howard's new price sheets cover (whole-sale, Contractor, Builder-Dealer).
The 4th tier (`one-opp`) is intentionally NOT touched.

Idempotent — running it twice produces the same result. Each (tier,
product_type) doc is replaced with the matrix loaded from
`mezzo_seed_prices.json`. Existing keys not present in the new seed
default to $0 (which matches the schema invariant — every bucket × adder
cell is always populated).

Usage:
    cd /app/backend
    python migrate_mezzo_prices.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db import db, logger
from mezzo_catalog import MEZZO_ADDER_NAMES, MEZZO_BUCKETS, MEZZO_PRODUCT_TYPES
from mezzo_prices import _empty_matrix, _merge_seed_into_matrix

SEED_PATH = Path(__file__).parent / "mezzo_seed_prices.json"
TIERS_TO_REFRESH = ["whole-sale", "Contractor", "Builder-Dealer"]


async def main():
    with open(SEED_PATH) as f:
        seed = json.load(f)
    total = 0
    for tier in TIERS_TO_REFRESH:
        tier_seed = seed.get(tier) or {}
        for product_type in MEZZO_PRODUCT_TYPES.keys():
            matrix = _empty_matrix(product_type)
            matrix = _merge_seed_into_matrix(matrix, tier_seed.get(product_type) or {})
            await db.mezzo_prices.update_one(
                {"tier": tier, "product_type": product_type},
                {"$set": {
                    "tier": tier,
                    "product_type": product_type,
                    **matrix,
                }},
                upsert=True,
            )
            total += 1
            sample_label = next(iter(matrix["base_prices"].keys()), None)
            sample_val = matrix["base_prices"].get(sample_label, 0.0) if sample_label else 0.0
            logger.info(
                f"Updated {tier} / {product_type} — "
                f"{len(matrix['base_prices'])} buckets, "
                f"sample {sample_label}: ${sample_val:.2f}"
            )
            print(
                f"  ✓ {tier:<16}/ {product_type:<22} {len(matrix['base_prices'])} buckets "
                f"({sample_label} = ${sample_val:.2f})"
            )
    print(f"\nMigration complete — {total} (tier, product_type) docs refreshed.")
    print("`one-opp` tier was intentionally not touched.")


if __name__ == "__main__":
    asyncio.run(main())
