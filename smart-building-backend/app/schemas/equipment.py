"""Pydantic schemas for equipment."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    equipment_type: str = Field(default="generic", max_length=50)
    model: Optional[str] = Field(default=None, max_length=120)
    status: str = Field(default="unknown", max_length=50)
    building_id: int


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    equipment_type: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=120)
    status: Optional[str] = Field(default=None, max_length=50)
    building_id: Optional[int] = None


class EquipmentRead(EquipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
