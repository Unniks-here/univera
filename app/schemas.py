from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class FieldType(str, Enum):
    string = "string"
    integer = "integer"
    float = "float"
    boolean = "boolean"
    date = "date"
    file = "file"
    relation = "relation"


class FieldUI(BaseModel):
    label: Optional[str] = None
    component: Optional[str] = None
    tooltip: Optional[str] = None
    options: Optional[List[str]] = None


class FieldDefinition(BaseModel):
    name: str
    type: FieldType
    relation: Optional[str] = None  # target entity for relation fields
    required: bool = False
    unique: bool = False
    pattern: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    group: Optional[str] = None
    ui: Optional[FieldUI] = None


class EntitySchemaCreate(BaseModel):
    entity_name: str
    fields: List[FieldDefinition]


class EntitySchemaRead(EntitySchemaCreate):
    id: UUID
    version: int

    class Config:
        orm_mode = True


class EntitySchemaUpdate(BaseModel):
    fields: List[FieldDefinition]


class RecordBase(BaseModel):
    data: Dict[str, Any]


class RecordCreate(RecordBase):
    pass


class RecordRead(RecordBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    class Config:
        orm_mode = True


class RecordLogRead(BaseModel):
    id: UUID
    record_id: UUID
    before_data: Dict[str, Any]
    after_data: Dict[str, Any]
    changed_at: datetime
    changed_by: UUID

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    username: str
    password: str
    tenant_id: UUID
    role: str = "user"


class UserRead(BaseModel):
    id: UUID
    username: str
    tenant_id: UUID
    role: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class PermissionBase(BaseModel):
    role: str
    can_read: bool = True
    can_create: bool = True
    can_update: bool = True
    can_delete: bool = True


class PermissionRead(PermissionBase):
    id: UUID
    entity_name: str

    class Config:
        orm_mode = True
