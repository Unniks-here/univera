from datetime import date
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import get_current_active_user
from .database import get_db


# Helper to validate data against schema definitions
def _validate_data(schema_fields: list[dict], data: Dict[str, Any]):
    fields_map = {f["name"]: f for f in schema_fields}
    for key, value in data.items():
        if key not in fields_map:
            raise HTTPException(status_code=400, detail=f"Unknown field: {key}")
        f_type = fields_map[key]["type"]
        if f_type == "string" and not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"Field {key} must be string")
        elif f_type == "integer" and not isinstance(value, int):
            raise HTTPException(status_code=400, detail=f"Field {key} must be integer")
        elif f_type == "float" and not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail=f"Field {key} must be float")
        elif f_type == "boolean" and not isinstance(value, bool):
            raise HTTPException(status_code=400, detail=f"Field {key} must be boolean")
        elif f_type == "date":
            try:
                date.fromisoformat(value)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Field {key} must be ISO date") from e
        elif f_type == "file" and not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"Field {key} must be file URL string")


def generate_crud_router(entity_name: str) -> APIRouter:
    router = APIRouter(prefix="", tags=[entity_name])

    @router.post("/", response_model=dict)
    def create_record(
        payload: Dict[str, Any],
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
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

        # 🔍 Validate fields using schema definition
        _validate_data(schema_obj.schema, payload)

        # ✅ Uniqueness check for fields marked as unique
        for field_def in schema_obj.schema:
            if field_def.get("unique", False):
                field_name = field_def["name"]
                value = payload.get(field_name)
                if value is None:
                    continue
                exists = (
                    db.query(models.Record)
                    .filter(
                        models.Record.tenant_id == current_user.tenant_id,
                        models.Record.entity_name == entity_name,
                        models.Record.data[field_name].astext == str(value)
                    )
                    .first()
                )
                if exists:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{field_name} must be unique. Duplicate value: {value}",
                    )

        # 🚀 Create the new record
        record = models.Record(
            tenant_id=current_user.tenant_id,
            entity_name=entity_name,
            data=payload,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.data

    @router.get("/", response_model=list[schemas.RecordRead])
    def list_records(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
    ):
        records = (
            db.query(models.Record)
            .filter(
                models.Record.entity_name == entity_name,
                models.Record.tenant_id == current_user.tenant_id,
            )
            .all()
        )
        return [schemas.RecordRead.from_orm(record) for record in records]

    @router.get("/{record_id}", response_model=schemas.RecordRead)
    def get_record(
        record_id: UUID,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
    ):
        record = (
            db.query(models.Record)
            .filter(
                models.Record.id == record_id,
                models.Record.entity_name == entity_name,
                models.Record.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        return schemas.RecordRead.from_orm(record)

    @router.put("/{record_id}", response_model=schemas.RecordRead)
    def update_record(
        record_id: UUID,
        payload: Dict[str, Any],
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
    ):
        record = (
            db.query(models.Record)
            .filter(
                models.Record.id == record_id,
                models.Record.entity_name == entity_name,
                models.Record.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
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
        _validate_data(schema_obj.schema, payload)
        record.data = payload
        db.commit()
        db.refresh(record)
        return schemas.RecordRead.from_orm(record)

    @router.delete("/{record_id}")
    def delete_record(
        record_id: UUID,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
    ):
        record = (
            db.query(models.Record)
            .filter(
                models.Record.id == record_id,
                models.Record.entity_name == entity_name,
                models.Record.tenant_id == current_user.tenant_id,
            )
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        db.delete(record)
        db.commit()
        return {"status": "deleted"}

    return router
