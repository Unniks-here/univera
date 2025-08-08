from uuid import uuid4, UUID
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import router as auth_router
from .config import settings
from .crud_router import generate_crud_router
from .database import SessionLocal, engine
from .models import Base, EntitySchema, User, Tenant  # <- Add Tenant model
from .routers import files as files_router
from .routers import schemas as schemas_router
from .auth_utils import get_password_hash  # <- Password hashing

# UUID to use for the default tenant
DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

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
        # 🔹 Step 1: Ensure default tenant exists
        default_tenant = db.query(Tenant).filter(Tenant.id == DEFAULT_TENANT_ID).first()
        if not default_tenant:
            db.add(Tenant(id=DEFAULT_TENANT_ID, name="Default Tenant"))
            db.commit()
            print("✅ Default tenant created")

        # 🔹 Step 2: Auto-create admin user if not exists
        admin_username = "admin"
        existing_admin = db.query(User).filter(User.username == admin_username).first()

        if not existing_admin:
            admin_user = User(
                id=uuid4(),
                username=admin_username,
                hashed_password=get_password_hash("admin123"),
                role="admin",
                tenant_id=DEFAULT_TENANT_ID,  # ✅ Real UUID
            )
            db.add(admin_user)
            db.commit()
            print("✅ Admin user created: admin / admin123")
        else:
            print("ℹ️ Admin user already exists.")

        # 🔹 Step 3: Load dynamic entity routers
        schemas = db.query(EntitySchema).all()
        for schema in schemas:
            app.include_router(
                generate_crud_router(schema.entity_name),
                prefix=f"/{schema.entity_name}",
                tags=[schema.entity_name],
            )
    finally:
        db.close()
