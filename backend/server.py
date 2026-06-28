"""FastAPI entrypoint. Wires CORS, sub-routers, and startup tasks. All business
logic now lives in `routes/`, `services.py`, `startup.py`, etc."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from config import CORS_ORIGINS  # noqa: E402
from db import client  # noqa: E402
from routes import api_router  # noqa: E402
from startup import run_startup  # noqa: E402

app = FastAPI(title="Vinyl Siding Estimator API")
app.include_router(api_router)

# SEC-001 — Iter 78z+++: never combine `*` with credentials. The
# Starlette CORS middleware reflects the request Origin when set to
# `*` + credentials, which lets any 3rd-party site read tenant data
# with the auth cookie. Strip any wildcard out and require an explicit
# allowlist; if the env var was empty, the list is empty and every
# preflight is refused (fail closed).
_allowed_origins = [o for o in CORS_ORIGINS if o != "*"]
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_start():
    await run_startup()


@app.on_event("shutdown")
async def shutdown():
    client.close()
