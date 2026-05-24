"""Compose all sub-routers under the /api prefix."""
from fastapi import APIRouter

from . import auth, branding, catalog, company, email, estimates, public, uploads

api_router = APIRouter(prefix="/api")
api_router.include_router(branding.router)
api_router.include_router(auth.router)
api_router.include_router(company.router)
api_router.include_router(catalog.router)
api_router.include_router(estimates.router)
api_router.include_router(uploads.router)
api_router.include_router(email.router)
api_router.include_router(public.router)


@api_router.get("/")
async def root():
    return {"ok": True, "app": "Vinyl Siding Estimator"}
