"""Photo / file uploads (per-contractor)."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from config import UPLOAD_DIR
from deps import get_current_user

router = APIRouter()


@router.post("/uploads")
async def upload_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = (file.filename or "").split(".")[-1].lower() or "jpg"
    if ext not in {"jpg", "jpeg", "png", "webp", "heic"}:
        ext = "jpg"
    name = f"{uuid.uuid4().hex}.{ext}"
    dest = UPLOAD_DIR / name
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (>10MB)")
    with open(dest, "wb") as f:
        f.write(content)
    return {"url": f"/api/uploads/{name}", "name": name}


@router.get("/uploads/{name}")
async def serve_upload(name: str):
    target = UPLOAD_DIR / name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(target))
