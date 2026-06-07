"""Vero Series catalog metadata — buckets, sister colors, glass packages,
patio-door fixed models, and the `catalog_for_tier_async` helper that the
frontend `/api/vero/catalog` endpoint calls to build a contractor-facing
matrix from the per-tier prices stored in `db.vero_prices`.

This file is the structural source of truth. Prices live in Mongo (seeded
from `vero_seed_prices.json` on first boot).
"""
from __future__ import annotations
from typing import Optional

VERO_TIER_NAMES = ["whole-sale", "Contractor", "Builder-Dealer", "one-opp"]

# ──────────────────── Bucket helpers ────────────────────

def parse_bucket_label(label: str) -> tuple[int, int]:
    """'Min-73' → (0, 73). '74-83' → (74, 83). '161-170' → (161, 170)."""
    s = label.strip()
    if "-" not in s:
        return (0, 0)
    left, right = s.split("-", 1)
    try:
        lo = 0 if left.strip().lower().startswith("min") else int(left.strip())
        hi = int(right.strip())
        return (lo, hi)
    except ValueError:
        return (0, 0)


def buckets_to_objects(labels: list[str]) -> list[dict]:
    return [
        {"label": L, "min_ui": parse_bucket_label(L)[0], "max_ui": parse_bucket_label(L)[1]}
        for L in labels
    ]


# ──────────────────── Product type registry ────────────────────

# Each entry tells the catalog layer how to render the product (W×H bucketed
# vs. fixed-model dropdown), and which optional sections to include.
VERO_PRODUCT_TYPES: dict[str, dict] = {
    "Vero Double Hung": {
        "sizing": "ui_bucket",
        "has_tempered_upcharge": True,
        "has_premium_options": True,
    },
    "Vero 2-Lite Slider": {
        "sizing": "ui_bucket",
        "has_tempered_upcharge": True,
        "has_premium_options": False,
    },
    "Vero 3-Lite Slider": {
        "sizing": "ui_bucket",
        "has_tempered_upcharge": False,
        "has_premium_options": False,
    },
    "Vero Picture": {
        "sizing": "ui_bucket",
        "has_tempered_upcharge": False,
        "has_premium_options": True,
    },
    "Vero Patio Door": {
        "sizing": "fixed_model",
        "has_tempered_upcharge": False,
        "has_premium_options": False,
    },
    "Vero 1-Lite Casement": {
        "sizing": "ui_bucket",
        "has_tempered_upcharge": True,
        "has_premium_options": False,
    },
}


# Glass packages are a flat list (the same 6 names appear across DH/2-Lite/
# 3-Lite/Picture/Casement). Prices vary per (product, tier, bucket) and are
# stored in Mongo. Patio Door has its own narrower set (X, X3).
VERO_GLASS_PACKAGES = [
    "IntelliGlass",
    "IntelliGlass N",
    "IntelliGlass X",
    "IntelliGlass C",
    "IntelliGlass X3",
    "IntelliGlass Plus",
]

VERO_PATIO_GLASS = ["IntelliGlass X", "IntelliGlass X3"]


# ──────────────────── Catalog assembly ────────────────────

async def catalog_for_tier_async(tier_name: str, prices_module) -> dict:
    """Build the contractor-facing catalog payload for one tier. Returns the
    list of 6 product types — each with metadata + base price grid + glass
    package grid + (optional) tempered/premium grids.

    `prices_module` must expose `await get_prices(tier, product_type) -> dict`.
    """
    product_types: list[dict] = []
    for pt_name, meta in VERO_PRODUCT_TYPES.items():
        prices = await prices_module.get_prices(tier_name, pt_name)
        product_types.append(_assemble_product(pt_name, meta, prices))
    return {"tier": tier_name, "product_types": product_types}


def _assemble_product(pt_name: str, meta: dict, prices: dict) -> dict:
    sizing = meta["sizing"]
    sister_colors: list[str] = prices.get("_sister_colors") or []
    if sizing == "ui_bucket":
        bucket_labels: list[str] = prices.get("_buckets") or list((prices.get("base_prices") or {}).keys())
        out = {
            "name": pt_name,
            "sizing": "ui_bucket",
            "buckets": buckets_to_objects(bucket_labels),
            "sister_colors": sister_colors,
            "base_prices": prices.get("base_prices") or {},
            "glass_packages": prices.get("glass_packages") or {},
            "tempered": prices.get("tempered") or {},
        }
        if meta.get("has_premium_options"):
            out["premium_options"] = prices.get("premium_options") or {}
        return out
    # Fixed-model (Patio Door)
    models: list[str] = prices.get("_models") or list((prices.get("patio_prices") or {}).keys())
    return {
        "name": pt_name,
        "sizing": "fixed_model",
        "models": models,
        "sister_colors": sister_colors,
        "patio_prices": prices.get("patio_prices") or {},
        "glass_packages": prices.get("glass_packages_patio") or {},
    }


def get_empty_shell(product_type: str) -> dict:
    """Used by `get_prices` when a (tier, product) doc is missing so the
    catalog endpoint still emits valid structure with all-zero numbers."""
    return {
        "_sister_colors": [],
        "_buckets": [],
        "_models": [],
        "base_prices": {},
        "patio_prices": {},
        "glass_packages": {},
        "glass_packages_patio": {},
        "tempered": {},
        "premium_options": {},
        "flat": {},
    }


def validate_product_type(name: str) -> Optional[str]:
    if name not in VERO_PRODUCT_TYPES:
        return f"Unknown Vero product_type: {name}"
    return None


def validate_tier(name: str) -> Optional[str]:
    if name not in VERO_TIER_NAMES:
        return f"Unknown Vero tier: {name}"
    return None
