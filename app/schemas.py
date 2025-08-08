from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

# ----------- ENUM FOR FIELD TYPES ----------- #
class FieldType(str, Enum):
    string = "string"
    integer = "integer"
    float = "float"
    boolean = "boolean"
    date = "date"
    file = "file"
    relation = "relation"

# ----------- FIELD DEFINITION ----------- #
class FieldDefinition(BaseModel):
    name: str
    type: FieldType
    relation: Optional[str] = None
    unique: bool = False


# ----------- ENTITY SCHEMA MODELS ----------- #
class EntitySchemaCreate(BaseModel):
    entity_name: str
    fields: List[FieldDefinition] = Field(alias="schema")

    model_config = ConfigDict(
        populate_by_name=True
    )

class EntitySchemaRead(BaseModel):
    id: UUID
    entity_name: str
    fields: List[FieldDefinition] = Field(alias="schema")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

# ----------- RECORD MODELS ----------- #
class RecordBase(BaseModel):
    data: Dict[str, Any]

class RecordCreate(RecordBase):
    pass

class RecordRead(RecordBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------- USER MODELS ----------- #
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

    model_config = ConfigDict(from_attributes=True)

# ----------- AUTH MODELS ----------- #
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

    model_config = ConfigDict(from_attributes=True)
class EntitySchemaUpdate(BaseModel):
    entity_name: Optional[str] = None
    fields: Optional[List[FieldDefinition]] = Field(default=None, alias="schema")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
