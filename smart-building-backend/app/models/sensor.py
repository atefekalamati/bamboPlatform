"""Sensor model."""

from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Sensor(Base):
    """Represents a sensor attached to equipment."""

    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    sensor_type = Column(String(50), nullable=False)
    unit = Column(String(50), nullable=True)
    location = Column(String(120), nullable=True)
    status = Column(String(50), default="active")
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    equipment = relationship("Equipment", back_populates="sensors")
