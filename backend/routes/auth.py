"""Registration / login / logout / me."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from config import SIGNUP_CODE, SUPPLIER_NAME
from db import db
from deps import (
    create_access_token,
    get_current_user,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from models import LoginIn, RegisterIn
from services import create_company

router = APIRouter()


@router.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())

    # Determine company assignment
    company_id: Optional[str] = None
    role = "user"
    if body.invite_code:
        code = body.invite_code.strip().upper()
        company = await db.companies.find_one({"invite_code": code}, {"_id": 0})
        if not company:
            raise HTTPException(status_code=400, detail="Invalid invite code")
        company_id = company["id"]
        role = "member"
    else:
        # Creating a new company requires the supplier signup code
        provided = (body.signup_code or "").strip().upper()
        if not SIGNUP_CODE or provided != SIGNUP_CODE.upper():
            raise HTTPException(
                status_code=403,
                detail=f"Signup is invite-only. Contact {SUPPLIER_NAME} for an access code.",
            )
        cname = (body.company_name or f"{(body.name or email.split('@')[0])}'s Company").strip()
        company = await create_company(cname, user_id)
        company_id = company["id"]
        role = "owner"

    user_doc = {
        "id": user_id,
        "email": email,
        "name": body.name or email.split("@")[0],
        "password_hash": hash_password(body.password),
        "role": role,
        "company_id": company_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(user_id, email)
    set_auth_cookie(response, token)
    return {"id": user_id, "email": email, "name": user_doc["name"], "role": role, "company_id": company_id}


@router.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], email)
    set_auth_cookie(response, token)
    return {
        "id": user["id"], "email": user["email"], "name": user.get("name"),
        "role": user.get("role", "user"), "company_id": user.get("company_id"),
    }


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", samesite="none", secure=True)
    return {"ok": True}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user
