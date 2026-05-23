"""Domain helpers reused by routes AND startup migrations.

Keeping these in a single module prevents circular imports between
routes/* (which need them at request time) and startup.py (which
needs them during the initial seed/migration).
"""
import uuid
from datetime import datetime, timezone

from config import SUPPLIER_NAME, SUPPLIER_TAGLINE
from db import db, logger
from deps import make_invite_code
from catalog_seed import TIER_NAMES, DEFAULT_TIER_NAME, build_tier_sections


# ---------------------------------------------------------------------------
# Branding (settings singleton)
# ---------------------------------------------------------------------------
async def get_branding() -> dict:
    doc = await db.settings.find_one({"id": "branding"}, {"_id": 0})
    if not doc:
        doc = {
            "id": "branding",
            "supplier_name": SUPPLIER_NAME,
            "supplier_tagline": SUPPLIER_TAGLINE,
            "supplier_logo_url": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.settings.insert_one(doc)
        doc.pop("_id", None)
    return doc


# ---------------------------------------------------------------------------
# Price tiers
# ---------------------------------------------------------------------------
async def ensure_tiers_seeded():
    """Seed the 4 standard price tiers if they don't exist yet."""
    existing = {t["name"] async for t in db.price_tiers.find({}, {"name": 1})}
    for name in TIER_NAMES:
        if name not in existing:
            now = datetime.now(timezone.utc).isoformat()
            await db.price_tiers.insert_one({
                "id": str(uuid.uuid4()),
                "name": name,
                "sections": build_tier_sections(name),
                "created_at": now,
                "updated_at": now,
            })
            logger.info("Seeded price tier %s", name)


async def get_default_tier_id() -> str | None:
    t = await db.price_tiers.find_one({"name": DEFAULT_TIER_NAME}, {"id": 1})
    return t["id"] if t else None


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------
async def create_company(name: str, owner_user_id: str) -> dict:
    tier_id = await get_default_tier_id()
    company = {
        "id": str(uuid.uuid4()),
        "name": name,
        "owner_user_id": owner_user_id,
        "invite_code": make_invite_code(),
        "logo_url": None,
        "quote_footer_enabled": True,
        "price_tier_id": tier_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.companies.insert_one(company)
    # Per-company catalog stores only labor overrides; material is locked to the
    # assigned price tier (managed by the supplier in /branding-admin).
    await db.catalogs.insert_one({
        "company_id": company["id"],
        "overrides": {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return company


# ---------------------------------------------------------------------------
# Estimate totals (shared by CSV export + future PDF generator)
# ---------------------------------------------------------------------------
def calc_totals(est: dict) -> dict:
    lines = est.get("lines", []) or []
    misc_labor = est.get("misc_labor", []) or []
    misc_material = est.get("misc_material", []) or []
    sub_mat = (
        sum((ln.get("qty", 0) or 0) * (ln.get("mat", 0) or 0) for ln in lines)
        + sum((m.get("mat", 0) or 0) for m in misc_material)
    )
    sub_lab = (
        sum((ln.get("qty", 0) or 0) * (ln.get("lab", 0) or 0) for ln in lines)
        + sum((m.get("lab", 0) or 0) for m in misc_material)
        + sum((m.get("lab", 0) or 0) for m in misc_labor)
    )
    wasted = sub_mat * (1 + (est.get("waste_pct", 0) or 0) / 100)
    tax = wasted * ((est.get("tax_rate", 0) or 0) / 100) if est.get("tax_enabled") else 0
    base = wasted + tax + sub_lab
    pct = (est.get("margin_pct", 0) or 0) / 100
    # Legacy estimates without pricing_mode were created under the old markup behaviour.
    mode = est.get("pricing_mode") or "markup"
    if mode == "margin":
        denom = 1 - min(pct, 0.99)  # cap to avoid divide-by-zero
        sell = base / denom if denom > 0 else base
    else:
        sell = base * (1 + pct)
    profit = sell - base
    return {
        "sub_mat": sub_mat, "sub_lab": sub_lab,
        "wasted": wasted, "tax": tax,
        "base": base, "sell": sell, "profit": profit,
    }
