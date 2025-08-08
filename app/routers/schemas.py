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

    # 🔄 Auto-register CRUD router dynamically
    request.app.include_router(
        generate_crud_router(schema_in.entity_name),
        prefix=f"/{schema_in.entity_name}",
        tags=[schema_in.entity_name],
    )
    return entity_schema
