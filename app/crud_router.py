from datetime import date
import re
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
    # check required fields
    for field in schema_fields:
        if field.get("required") and field["name"] not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field['name']}")

    for key, value in data.items():
        if key not in fields_map:
            raise HTTPException(status_code=400, detail=f"Unknown field: {key}")
        f_def = fields_map[key]
        f_type = f_def["type"]
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
            except Exception as e:  # pragma: no cover - simple validation
                raise HTTPException(status_code=400, detail=f"Field {key} must be ISO date") from e
        elif f_type == "file" and not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"Field {key} must be file URL string")
        # relation types are stored as record id (string/UUID)

        # additional validations
        if f_type in {"integer", "float"}:
            if f_def.get("min") is not None and value < f_def["min"]:
                raise HTTPException(status_code=400, detail=f"Field {key} below min")
            if f_def.get("max") is not None and value > f_def["max"]:
                raise HTTPException(status_code=400, detail=f"Field {key} above max")
        if f_type == "string":
            if f_def.get("min_length") is not None and len(value) < f_def["min_length"]:
                raise HTTPException(status_code=400, detail=f"Field {key} shorter than min_length")
            if f_def.get("max_length") is not None and len(value) > f_def["max_length"]:
                raise HTTPException(status_code=400, detail=f"Field {key} longer than max_length")
            if f_def.get("pattern") and not re.fullmatch(f_def["pattern"], value):
                raise HTTPException(status_code=400, detail=f"Field {key} does not match pattern")


def _check_uniques(schema_fields: list[dict], data: Dict[str, Any], db: Session, entity_name: str, tenant_id: UUID, record_id: UUID | None = None):
    for field in schema_fields:
        if field.get("unique") and field["name"] in data:
            value = data[field["name"]]
            query = db.query(models.Record).filter(
                models.Record.entity_name == entity_name,
                models.Record.tenant_id == tenant_id,
                models.Record.data[field["name"]].astext == str(value),
            )
            if record_id:
                query = query.filter(models.Record.id != record_id)
            if query.first():
                raise HTTPException(status_code=400, detail=f"Field {field['name']} must be unique")


def _check_permission(db: Session, tenant_id: UUID, role: str, action: str, entity_name: str):
    perm = (
        db.query(models.EntityPermission)
        .filter(
            models.EntityPermission.tenant_id == tenant_id,
            models.EntityPermission.entity_name == entity_name,
            models.EntityPermission.role == role,
        )
        .first()
    )
    if not perm or not getattr(perm, f"can_{action}"):
        raise HTTPException(status_code=403, detail="Not enough permissions")


def generate_crud_router(entity_name: str) -> APIRouter:
    router = APIRouter(prefix="", tags=[entity_name])

    @router.post("/", response_model=dict)
    def create_record(
        payload: Dict[str, Any],
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
    ):
        _check_permission(db, current_user.tenant_id, current_user.role, "create", entity_name)
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
        _validate_data(schema_obj.schema, payload)
        _check_uniques(schema_obj.schema, payload, db, entity_name, current_user.tenant_id)
        record = models.Record(
            tenant_id=current_user.tenant_id,
            entity_name=entity_name,
            data=payload,
            created_by=current_user.id,
            updated_by=current_user.id,
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
        _check_permission(db, current_user.tenant_id, current_user.role, "read", entity_name)
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
        _check_permission(db, current_user.tenant_id, current_user.role, "read", entity_name)
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
        return record

    @router.put("/{record_id}", response_model=dict)
    def update_record(
        record_id: UUID,
        payload: Dict[str, Any],
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
    ):
        _check_permission(db, current_user.tenant_id, current_user.role, "update", entity_name)
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
        _check_uniques(schema_obj.schema, payload, db, entity_name, current_user.tenant_id, record.id)
        before = record.data.copy()
        record.data = payload
        record.updated_by = current_user.id
        log = models.RecordLog(
            record_id=record.id,
            tenant_id=current_user.tenant_id,
            entity_name=entity_name,
            before_data=before,
            after_data=payload,
            changed_by=current_user.id,
        )
        db.add(log)
        db.commit()
        db.refresh(record)
        return record

    @router.delete("/{record_id}")
    def delete_record(
        record_id: UUID,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user),
    ):
        _check_permission(db, current_user.tenant_id, current_user.role, "delete", entity_name)
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
