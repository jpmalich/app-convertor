"""Public branding + supplier-admin endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from config import SUPPLIER_NAME, SUPPLIER_TAGLINE, SIGNUP_CODE, UPLOAD_DIR
from db import db
from deps import check_admin_token
from models import BrandingUpdate
from services import get_branding

router = APIRouter()


@router.get("/branding")
async def public_branding():
    b = await get_branding()
    return {
        "supplier_name": b.get("supplier_name") or SUPPLIER_NAME,
        "supplier_tagline": b.get("supplier_tagline") or SUPPLIER_TAGLINE,
        "supplier_logo_url": b.get("supplier_logo_url"),
        "default_pricing_mode": b.get("default_pricing_mode") or "margin",
    }


@router.put("/admin/branding")
async def admin_update_branding(body: BrandingUpdate, request: Request):
    check_admin_token(request)
    updates = {}
    if body.supplier_name is not None and body.supplier_name.strip():
        updates["supplier_name"] = body.supplier_name.strip()
    if body.supplier_tagline is not None:
        updates["supplier_tagline"] = body.supplier_tagline.strip()
    if body.supplier_logo_url is not None:
        updates["supplier_logo_url"] = body.supplier_logo_url or None
    if body.default_pricing_mode is not None:
        mode = body.default_pricing_mode.strip().lower()
        if mode not in {"margin", "markup"}:
            raise HTTPException(status_code=400, detail="default_pricing_mode must be 'margin' or 'markup'")
        updates["default_pricing_mode"] = mode
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.update_one({"id": "branding"}, {"$set": updates}, upsert=True)
    return await get_branding()


@router.post("/admin/upload-logo")
async def admin_upload_logo(request: Request, file: UploadFile = File(...)):
    check_admin_token(request)
    ext = (file.filename or "").split(".")[-1].lower() or "png"
    if ext not in {"jpg", "jpeg", "png", "webp", "svg"}:
        ext = "png"
    name = f"supplier-logo-{uuid.uuid4().hex[:8]}.{ext}"
    dest = UPLOAD_DIR / name
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo too large (>5MB)")
    with open(dest, "wb") as f:
        f.write(content)
    url = f"/api/uploads/{name}"
    await db.settings.update_one(
        {"id": "branding"},
        {"$set": {"supplier_logo_url": url, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"url": url}


@router.get("/admin/signup-code")
async def admin_get_signup_code(request: Request):
    check_admin_token(request)
    return {"signup_code": SIGNUP_CODE}
