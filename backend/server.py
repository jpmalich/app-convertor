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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_start():
    await run_startup()


@app.on_event("shutdown")
async def shutdown():
    client.close()
