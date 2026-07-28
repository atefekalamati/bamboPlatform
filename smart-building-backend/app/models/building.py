"""Building model."""

from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Building(Base):
    """Represents a physical building or structure."""

    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    address = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    total_floors = Column(Integer, default=0)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    equipments = relationship("Equipment", back_populates="building", cascade="all, delete-orphan")
