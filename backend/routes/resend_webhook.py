"""Resend webhook handler.

Resend signs every webhook with Svix. We verify the signature using the raw
request body + the headers `svix-id`, `svix-timestamp`, `svix-signature`, then
correlate events back to the originating estimate via the `estimate_id` tag we
attach when sending each quote.

Stored on the estimate:
- `last_delivered_at`, `last_opened_at`, `last_clicked_at`, `last_bounced_at`
- `tracking[]` — full append-only event log so the dashboard can show timeline

Resend events we care about:
  email.delivered   email reached the recipient's mail server
  email.opened      recipient opened the email
  email.clicked     recipient clicked a link
  email.bounced     hard/soft bounce
  email.complained  marked as spam

Configure in Resend dashboard: Webhooks → Add Endpoint →
  https://<your-domain>/api/public/resend-webhook
The webhook secret (starts with `whsec_`) goes in backend/.env as
RESEND_WEBHOOK_SECRET.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from db import db, logger

router = APIRouter()

EVENT_FIELD_MAP = {
    "email.delivered": "last_delivered_at",
    "email.opened": "last_opened_at",
    "email.clicked": "last_clicked_at",
    "email.bounced": "last_bounced_at",
    "email.complained": "last_complained_at",
}


def _verify_svix_signature(
    svix_id: str, svix_timestamp: str, svix_signature: str, raw_body: bytes, secret: str
) -> bool:
    """Verify a Svix webhook signature. Returns True if any of the comma-separated
    `v1,<base64>` signatures in `svix-signature` matches the computed HMAC.

    Resend's secret looks like `whsec_xxx...`. We strip the prefix and base64-
    decode the remainder to get the actual signing key (per Svix spec)."""
    if not (svix_id and svix_timestamp and svix_signature and secret):
        return False
    try:
        key_b64 = secret.removeprefix("whsec_")
        key = base64.b64decode(key_b64)
    except Exception:
        return False
    signed_payload = f"{svix_id}.{svix_timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = base64.b64encode(hmac.new(key, signed_payload, hashlib.sha256).digest()).decode()
    # `svix-signature` looks like "v1,abc... v1,def..." — accept any match.
    for sig in svix_signature.split():
        version, _, value = sig.partition(",")
        if version == "v1" and hmac.compare_digest(value, expected):
            return True
    return False


def _extract_estimate_id(payload: dict) -> str | None:
    """Resend includes our outbound `tags` array in event data — find the one
    with name=estimate_id."""
    data = payload.get("data") or {}
    for tag in data.get("tags") or []:
        if isinstance(tag, dict) and tag.get("name") == "estimate_id":
            return tag.get("value")
    return None


@router.post("/public/resend-webhook")
async def resend_webhook(request: Request):
    raw = await request.body()
    secret = os.environ.get("RESEND_WEBHOOK_SECRET", "")
    svix_id = request.headers.get("svix-id") or ""
    svix_ts = request.headers.get("svix-timestamp") or ""
    svix_sig = request.headers.get("svix-signature") or ""

    # If a secret is configured, enforce signature verification. If not (early
    # local testing), accept all events with a warning log — never silent fail.
    if secret:
        if not _verify_svix_signature(svix_id, svix_ts, svix_sig, raw, secret):
            logger.warning("Resend webhook signature verification FAILED — rejecting")
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning("RESEND_WEBHOOK_SECRET not set — webhook running unverified")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type") or ""
    estimate_id = _extract_estimate_id(payload)
    if not estimate_id:
        # Email may have been sent outside our app (e.g. a Resend test) — log + skip.
        logger.info("Resend event %s with no estimate_id tag — skipping", event_type)
        return {"ok": True, "matched": False}

    field = EVENT_FIELD_MAP.get(event_type)
    now = datetime.now(timezone.utc).isoformat()
    event_record = {
        "type": event_type,
        "at": now,
        "email_id": (payload.get("data") or {}).get("email_id"),
    }

    update = {"$push": {"tracking": event_record}}
    if field:
        update["$set"] = {field: now}

    result = await db.estimates.update_one({"id": estimate_id}, update)
    logger.info(
        "Resend event %s → estimate %s (matched=%s)",
        event_type, estimate_id, result.matched_count > 0,
    )
    return {"ok": True, "matched": result.matched_count > 0}
