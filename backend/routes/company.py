"""Per-contractor company GET/PUT."""
from fastapi import APIRouter, Depends

from db import db
from deps import get_company_for, get_current_user
from models import CompanyUpdate

router = APIRouter()


@router.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    return await get_company_for(user)


@router.put("/company")
async def update_company(body: CompanyUpdate, user: dict = Depends(get_current_user)):
    company = await get_company_for(user)
    updates = {}
    if body.name is not None and body.name.strip():
        updates["name"] = body.name.strip()
    if body.logo_url is not None:
        # Empty string clears the logo
        updates["logo_url"] = body.logo_url or None
    if body.quote_footer_enabled is not None:
        updates["quote_footer_enabled"] = bool(body.quote_footer_enabled)
    if updates:
        await db.companies.update_one({"id": company["id"]}, {"$set": updates})
    return await db.companies.find_one({"id": company["id"]}, {"_id": 0})
