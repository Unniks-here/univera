from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import router as auth_router
from .config import settings
from .crud_router import generate_crud_router
from .database import SessionLocal, engine
from .models import Base, EntitySchema
from .routers import files as files_router
from .routers import schemas as schemas_router

app = FastAPI(title="Univera No-Code Platform")

# Include base routers
app.include_router(auth_router)
app.include_router(schemas_router.router)
app.include_router(files_router.router)

# Serve uploaded files (development use)
app.mount("/files", StaticFiles(directory=settings.file_storage_path), name="files")


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        schemas = db.query(EntitySchema).all()
        for schema in schemas:
            app.include_router(
                generate_crud_router(schema.entity_name),
                prefix=f"/{schema.entity_name}",
                tags=[schema.entity_name],
            )
    finally:
        db.close()
