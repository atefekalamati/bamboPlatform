"""Equipment model."""

from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Equipment(Base):
    """Represents a managed equipment item within a building."""

    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    equipment_type = Column(String(50), nullable=False, default="generic")
    model = Column(String(120), nullable=True)
    status = Column(String(50), default="unknown")
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    building = relationship("Building", back_populates="equipments")
    sensors = relationship("Sensor", back_populates="equipment", cascade="all, delete-orphan")
