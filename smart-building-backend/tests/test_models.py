import os

import pytest
from sqlalchemy import text

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smart_building.db")

from app.database import SessionLocal, init_db
from app.models import Building, Equipment, Sensor


def test_database_initialization_and_relationships():
    init_db()

    with SessionLocal() as session:
        building = Building(
            name="Bamboo Tower",
            address="Mashhad, Iran",
            description="Smart building pilot",
            total_floors=12,
            status="active",
        )
        session.add(building)
        session.flush()

        equipment = Equipment(
            name="HVAC-01",
            equipment_type="HVAC",
            model="AeroX",
            status="running",
            building_id=building.id,
        )
        session.add(equipment)
        session.flush()

        sensor = Sensor(
            name="Temp-01",
            sensor_type="temperature",
            unit="°C",
            location="Lobby",
            status="active",
            equipment_id=equipment.id,
        )
        session.add(sensor)
        session.commit()

        session.refresh(building)
        assert building.name == "Bamboo Tower"
        assert building.equipments[0].name == "HVAC-01"
        assert building.equipments[0].sensors[0].name == "Temp-01"

        result = session.execute(text("SELECT COUNT(*) FROM buildings")).scalar_one()
        assert result == 1
