import importlib
import sqlite3
import sys

from sqlalchemy import text


def test_database_initialization_and_relationships(monkeypatch, tmp_path):
    db_path = tmp_path / "test_smart_building.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    for module_name in ["app.database", "app.models", "app.models.building", "app.models.equipment", "app.models.sensor"]:
        sys.modules.pop(module_name, None)

    import app.database as database
    import app.models as models

    database = importlib.reload(database)
    models = importlib.reload(models)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE buildings (id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT, description TEXT, total_floors INTEGER, status TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE equipment (id INTEGER PRIMARY KEY, name TEXT NOT NULL, equipment_type TEXT NOT NULL, model TEXT, status TEXT, building_id INTEGER NOT NULL, created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE sensors (id INTEGER PRIMARY KEY, name TEXT NOT NULL, sensor_type TEXT NOT NULL, unit TEXT, location TEXT, status TEXT, equipment_id INTEGER NOT NULL, created_at TEXT, updated_at TEXT)"
        )
        conn.commit()

    with database.get_session() as session:
        building = models.Building(
            name="Bamboo Tower",
            address="Mashhad, Iran",
            description="Smart building pilot",
            total_floors=12,
            status="active",
        )
        session.add(building)
        session.flush()

        equipment = models.Equipment(
            name="HVAC-01",
            equipment_type="HVAC",
            model="AeroX",
            status="running",
            building_id=building.id,
        )
        session.add(equipment)
        session.flush()

        sensor = models.Sensor(
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
