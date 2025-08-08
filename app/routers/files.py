import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from ..auth import get_current_active_user
from ..config import settings
from .. import models

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user),
):
    storage_dir = Path(settings.file_storage_path) / str(current_user.tenant_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = storage_dir / filename
    with file_path.open("wb") as buffer:
        buffer.write(await file.read())
    file_url = f"/files/{current_user.tenant_id}/{filename}"
    return {"url": file_url}
