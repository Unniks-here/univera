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


class FieldDefinition(BaseModel):
    name: str
    type: FieldType
    relation: Optional[str] = None  # target entity for relation fields


class EntitySchemaCreate(BaseModel):
    entity_name: str
    fields: List[FieldDefinition]


class EntitySchemaRead(EntitySchemaCreate):
    id: UUID

    class Config:
        orm_mode = True


class RecordBase(BaseModel):
    data: Dict[str, Any]


class RecordCreate(RecordBase):
    pass


class RecordRead(RecordBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

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
