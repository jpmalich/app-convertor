"""Vero Series catalog metadata — buckets, sister colors, adders.

After Iter 44 the Vero pricing model mirrors Mezzo 1:1:
  - One `base_prices` matrix per (tier, product_type, bucket)
  - One `adder_prices` matrix per (tier, product_type, adder_name, bucket)
  - All adders are flat (no sqft-based rate on Vero)
  - Patio Door stays fixed-model (just base prices on 3 panel sizes)

This file is the structural source of truth. Prices live in Mongo
(seeded from `vero_seed_prices.json` on first boot).
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


# ──────────────────── Adder names per product ────────────────────

# Canonical adder order — display order in the UI ("most common" rows
# first). Howard's preference per the Iter-44 conversation:
#   Row 1: Climatech Plus, Solid Color Flat Grids, Head Expander, Sentry System
#   Row 2: Obscure Full, Climatech TG2 Plus, Foam Wrap, Foam Frame
#   Row 3: Climatech Plus Tempered, Climatech TG2 Tempered, Integral Nailing Fin, Oriel Style Double Hung
VERO_ADDER_NAMES = {
    "Vero Double Hung": [
        "Climatech Plus",
        "Solid Color Flat Grids",
        "Head Expander",
        "Sentry System",
        "Obscure Full",
        "Climatech TG2 Plus",
        "Foam Wrap",
        "Foam Frame",
        "Climatech Plus Tempered",
        "Climatech TG2 Tempered",
        "Integral Nailing Fin",
        "Oriel Style Double Hung",
    ],
    "Vero 2-Lite Slider": [
        "Climatech Plus",
        "Solid Color Flat Grids",
        "Head Expander",
        "Obscure Full",
        "Climatech TG2 Plus",
        "Foam Wrap",
        "Foam Frame",
        "Climatech Plus Tempered",
        "Climatech TG2 Tempered",
        "Integral Nailing Fin",
    ],
    "Vero 3-Lite Slider": [
        "Climatech Plus",
        "Solid Color Flat Grids",
        "Head Expander",
        "Obscure Full",
        "Climatech TG2 Plus",
        "Foam Wrap",
        "Foam Frame",
        "Climatech Plus Tempered",
        "Climatech TG2 Tempered",
        "Integral Nailing Fin",
    ],
    "Vero Picture": [
        "Climatech Plus",
        "Solid Color Flat Grids",
        "Head Expander",
        "Obscure Full",
        "Climatech TG2 Plus",
        "Foam Wrap",
        "Foam Frame",
        "Climatech Plus Tempered",
        "Climatech TG2 Tempered",
        "Integral Nailing Fin",
    ],
    "Vero Patio Door": [],  # fixed-model; adders not applicable
}


# ──────────────────── Product type registry ────────────────────

VERO_PRODUCT_TYPES: dict[str, dict] = {
    "Vero Double Hung":   {"sizing": "ui_bucket"},
    "Vero 2-Lite Slider": {"sizing": "ui_bucket"},
    "Vero 3-Lite Slider": {"sizing": "ui_bucket"},
    "Vero Picture":       {"sizing": "ui_bucket"},
    "Vero Patio Door":    {"sizing": "fixed_model"},
}


# ──────────────────── Catalog assembly ────────────────────

async def catalog_for_tier_async(tier_name: str, prices_module) -> dict:
    """Build the contractor-facing catalog payload for one tier."""
    product_types: list[dict] = []
    for pt_name, meta in VERO_PRODUCT_TYPES.items():
        prices = await prices_module.get_prices(tier_name, pt_name)
        product_types.append(_assemble_product(pt_name, meta, prices))
    return {"tier": tier_name, "product_types": product_types}


def _assemble_product(pt_name: str, meta: dict, prices: dict) -> dict:
    sizing = meta["sizing"]
    sister_colors: list[str] = prices.get("_sister_colors") or []
    adder_prices = prices.get("adder_prices") or {}

    if sizing == "ui_bucket":
        bucket_labels: list[str] = prices.get("_buckets") or list((prices.get("base_prices") or {}).keys())
        # Pull (almost-flat) sister-color price out of the {bucket: {color: $}} shape
        flat_base = {}
        for b, payload in (prices.get("base_prices") or {}).items():
            if isinstance(payload, dict):
                flat_base[b] = float(payload.get(sister_colors[0], 0.0)) if sister_colors else 0.0
            else:
                flat_base[b] = float(payload or 0.0)
        # Build adder list in canonical display order; fall back to any
        # extra adders the doc has but the canonical list doesn't.
        canonical = VERO_ADDER_NAMES.get(pt_name, [])
        seen = set()
        adders_out: list[dict] = []
        for ad_name in canonical + [a for a in adder_prices.keys() if a not in canonical]:
            if ad_name in seen:
                continue
            seen.add(ad_name)
            prices_by_bucket = adder_prices.get(ad_name) or {}
            adders_out.append({
                "name": ad_name,
                "kind": "flat",
                "prices_by_bucket": {
                    b: float(prices_by_bucket.get(b, 0.0))
                    for b in bucket_labels
                },
            })
        return {
            "name": pt_name,
            "sizing": "ui_bucket",
            "buckets": buckets_to_objects(bucket_labels),
            "sister_colors": sister_colors,
            "base_prices": flat_base,
            "adders": adders_out,
        }

    # Fixed-model (Patio Door)
    models: list[str] = prices.get("_models") or list((prices.get("patio_prices") or {}).keys())
    flat_patio: dict[str, float] = {}
    for m, payload in (prices.get("patio_prices") or {}).items():
        if isinstance(payload, dict):
            flat_patio[m] = float(payload.get(sister_colors[0], 0.0)) if sister_colors else 0.0
        else:
            flat_patio[m] = float(payload or 0.0)
    return {
        "name": pt_name,
        "sizing": "fixed_model",
        "models": models,
        "sister_colors": sister_colors,
        "patio_prices": flat_patio,
        "adders": [],
    }


def get_empty_shell(product_type: str) -> dict:
    return {
        "_sister_colors": [],
        "_buckets": [],
        "_models": [],
        "base_prices": {},
        "patio_prices": {},
        "adder_prices": {},
    }


def validate_product_type(name: str) -> Optional[str]:
    if name not in VERO_PRODUCT_TYPES:
        return f"Unknown Vero product_type: {name}"
    return None


def validate_tier(name: str) -> Optional[str]:
    if name not in VERO_TIER_NAMES:
        return f"Unknown Vero tier: {name}"
    return None
