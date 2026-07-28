"""Pydantic schemas for sensors."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SensorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    sensor_type: str = Field(..., max_length=50)
    unit: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=120)
    status: str = Field(default="active", max_length=50)
    equipment_id: int


class SensorCreate(SensorBase):
    pass


class SensorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    sensor_type: Optional[str] = Field(default=None, max_length=50)
    unit: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=120)
    status: Optional[str] = Field(default=None, max_length=50)
    equipment_id: Optional[int] = None


class SensorRead(SensorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
