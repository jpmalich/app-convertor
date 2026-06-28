"""Centralised env-driven configuration. Import these constants anywhere."""
import os
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).parent

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-" + uuid.uuid4().hex)
JWT_ALG = "HS256"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@wolfandson.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")
ADMIN_COMPANY = os.environ.get("ADMIN_COMPANY", "Pro-Quote Estimating Tool")

SUPPLIER_NAME = os.environ.get("SUPPLIER_NAME", "Alside Supply")
SUPPLIER_TAGLINE = os.environ.get(
    "SUPPLIER_TAGLINE",
    "Howard Hunt · Territory Sales Manager · (724) 640-4333",
)
SUPPLIER_ADMIN_TOKEN = os.environ.get("SUPPLIER_ADMIN_TOKEN", "")

SIGNUP_CODE = os.environ.get("SIGNUP_CODE", "")
if not SIGNUP_CODE:
    # Stable fallback derived from JWT_SECRET so the code survives restarts when not pinned.
    SIGNUP_CODE = "ALSIDE-" + uuid.uuid5(uuid.NAMESPACE_DNS, JWT_SECRET).hex[:6].upper()

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

# SEC-001 — Iter 78z+++: CORS allowlist parsing. Each origin is comma
# separated; whitespace + empty entries get stripped. We deliberately
# leave the env var with NO default so an unconfigured deploy fails
# closed (no `*` fallback when credentials are sent). The server-side
# check in `server.py` refuses to combine `*` with `allow_credentials`.
CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
]

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
