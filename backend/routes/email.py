"""Quote-email delivery via Resend + email-config status."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException

from config import RESEND_API_KEY, SENDER_EMAIL
from db import db, logger
from deps import get_current_user
from models import EmailQuoteIn

router = APIRouter()


@router.post("/estimates/{est_id}/email")
async def email_quote(est_id: str, body: EmailQuoteIn, user: dict = Depends(get_current_user)):
    est = await db.estimates.find_one(
        {"id": est_id, "company_id": user["company_id"]}, {"_id": 0}
    )
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    if not RESEND_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Add RESEND_API_KEY to enable.",
        )
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        # Look up the contractor's actual company name for the subject fallback.
        company = await db.companies.find_one(
            {"id": user["company_id"]}, {"_id": 0, "name": 1}
        )
        company_name = (company or {}).get("name") or "your contractor"
        # Replies should go back to the contractor — not the shared Resend sending address.
        # Prefer the company owner so a teammate's quote still hits the right inbox.
        owner = await db.users.find_one(
            {"company_id": user["company_id"], "role": "owner"},
            {"_id": 0, "email": 1, "name": 1},
        )
        reply_to_email = (owner or {}).get("email") or user.get("email")
        params = {
            "from": SENDER_EMAIL,
            "to": [body.recipient_email],
            "reply_to": reply_to_email,
            "subject": body.subject or f"Your siding estimate from {company_name}",
            "html": body.html_quote,
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {"status": "sent", "id": result.get("id")}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("email failed")
        raise HTTPException(status_code=500, detail=f"Email failed: {e}")


@router.get("/email/status")
async def email_status(user: dict = Depends(get_current_user)):
    return {"configured": bool(RESEND_API_KEY), "sender": SENDER_EMAIL if RESEND_API_KEY else None}
