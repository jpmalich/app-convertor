"""ISS Siding REST endpoint.

  GET /api/iss/catalog → contractor-facing single-tier line book.
"""
from fastapi import APIRouter, Depends

from iss_catalog import build_iss_catalog
from deps import get_current_user

router = APIRouter(prefix="/iss", tags=["iss"])


@router.get("/catalog")
async def iss_catalog(user: dict = Depends(get_current_user)):
    return build_iss_catalog()
