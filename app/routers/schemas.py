from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_admin_user, get_current_active_user
from ..database import get_db
from ..crud_router import generate_crud_router

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.post("/", response_model=schemas.EntitySchemaRead)
def create_entity_schema(
    schema_in: schemas.EntitySchemaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
):
    # 🔐 Prevent duplicate entity_name per tenant
    existing = (
        db.query(models.EntitySchema)
        .filter_by(tenant_id=current_user.tenant_id, entity_name=schema_in.entity_name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Entity '{schema_in.entity_name}' already exists.")

    fields = [field.dict() for field in schema_in.fields]
    entity_schema = models.EntitySchema(
        tenant_id=current_user.tenant_id,
        entity_name=schema_in.entity_name,
        schema=fields,
    )
    db.add(entity_schema)
    db.commit()
    db.refresh(entity_schema)
    db.add(
        models.EntitySchemaVersion(
            tenant_id=current_user.tenant_id,
            entity_name=schema_in.entity_name,
            version=entity_schema.version,
            schema=fields,
        )
    )
    # default permissions for admin and user
    for role in ["admin", "user"]:
        db.add(
            models.EntityPermission(
                tenant_id=current_user.tenant_id,
                entity_name=schema_in.entity_name,
                role=role,
            )
        )
    db.commit()
    # Auto-register CRUD router for new entity
    request.app.include_router(
        generate_crud_router(schema_in.entity_name),
        prefix=f"/{schema_in.entity_name}",
        tags=[schema_in.entity_name],
    )
    return entity_schema


@router.get("/", response_model=list[schemas.EntitySchemaRead])
def list_entity_schemas(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    return (
        db.query(models.EntitySchema)
        .filter(models.EntitySchema.tenant_id == current_user.tenant_id)
        .all()
    )


@router.put("/{entity_name}", response_model=schemas.EntitySchemaRead)
def update_entity_schema(
    entity_name: str,
    schema_in: schemas.EntitySchemaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
):
    schema_obj = (
        db.query(models.EntitySchema)
        .filter(
            models.EntitySchema.entity_name == entity_name,
            models.EntitySchema.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not schema_obj:
        raise HTTPException(status_code=404, detail="Entity not found")
    fields = [field.dict() for field in schema_in.fields]
    schema_obj.schema = fields
    schema_obj.version += 1
    db.add(
        models.EntitySchemaVersion(
            tenant_id=current_user.tenant_id,
            entity_name=entity_name,
            version=schema_obj.version,
            schema=fields,
        )
    )
    db.commit()
    db.refresh(schema_obj)
    return schema_obj


@router.post("/{entity_name}/rollback/{version}", response_model=schemas.EntitySchemaRead)
def rollback_entity_schema(
    entity_name: str,
    version: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
):
    schema_obj = (
        db.query(models.EntitySchema)
        .filter(
            models.EntitySchema.entity_name == entity_name,
            models.EntitySchema.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not schema_obj:
        raise HTTPException(status_code=404, detail="Entity not found")
    version_obj = (
        db.query(models.EntitySchemaVersion)
        .filter(
            models.EntitySchemaVersion.entity_name == entity_name,
            models.EntitySchemaVersion.tenant_id == current_user.tenant_id,
            models.EntitySchemaVersion.version == version,
        )
        .first()
    )
    if not version_obj:
        raise HTTPException(status_code=404, detail="Version not found")
    schema_obj.schema = version_obj.schema
    schema_obj.version += 1
    db.add(
        models.EntitySchemaVersion(
            tenant_id=current_user.tenant_id,
            entity_name=entity_name,
            version=schema_obj.version,
            schema=version_obj.schema,
        )
    )
    db.commit()
    db.refresh(schema_obj)
    return schema_obj


@router.put("/{entity_name}/permissions/{role}", response_model=schemas.PermissionRead)
def set_permissions(
    entity_name: str,
    role: str,
    perm_in: schemas.PermissionBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user),
):
    perm = (
        db.query(models.EntityPermission)
        .filter(
            models.EntityPermission.entity_name == entity_name,
            models.EntityPermission.tenant_id == current_user.tenant_id,
            models.EntityPermission.role == role,
        )
        .first()
    )
    if not perm:
        perm = models.EntityPermission(
            tenant_id=current_user.tenant_id,
            entity_name=entity_name,
            role=role,
        )
        db.add(perm)
    perm.can_read = perm_in.can_read
    perm.can_create = perm_in.can_create
    perm.can_update = perm_in.can_update
    perm.can_delete = perm_in.can_delete
    db.commit()
    db.refresh(perm)
    return perm
