"""Pydantic schemas for buildings."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BuildingBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    address: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    total_floors: int = Field(default=0, ge=0)
    status: str = Field(default="active", max_length=50)


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    address: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    total_floors: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, max_length=50)


class BuildingRead(BuildingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
