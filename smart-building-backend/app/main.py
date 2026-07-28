"""FastAPI entrypoint for the smart building backend."""

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, ensure_schema, get_db, init_db
from app.models import Building, Equipment, Sensor
from app.schemas import (
    BuildingCreate,
    BuildingRead,
    BuildingUpdate,
    EquipmentCreate,
    EquipmentRead,
    EquipmentUpdate,
    SensorCreate,
    SensorRead,
    SensorUpdate,
)

app = FastAPI(title="Smart Building Backend", version="0.1.0")


@app.on_event("startup")
def startup_event() -> None:
    ensure_schema()


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/buildings", response_model=BuildingRead, tags=["buildings"])
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)) -> Building:
    building = Building(**payload.dict())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@app.get("/buildings", response_model=list[BuildingRead], tags=["buildings"])
def list_buildings(db: Session = Depends(get_db)) -> list[Building]:
    return db.query(Building).all()


@app.get("/buildings/{building_id}", response_model=BuildingRead, tags=["buildings"])
def get_building(building_id: int, db: Session = Depends(get_db)) -> Building:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    return building


@app.put("/buildings/{building_id}", response_model=BuildingRead, tags=["buildings"])
def update_building(building_id: int, payload: BuildingUpdate, db: Session = Depends(get_db)) -> Building:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(building, field, value)

    db.commit()
    db.refresh(building)
    return building


@app.delete("/buildings/{building_id}", tags=["buildings"])
def delete_building(building_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    db.delete(building)
    db.commit()
    return {"message": "Building deleted"}


@app.post("/equipment", response_model=EquipmentRead, tags=["equipment"])
def create_equipment(payload: EquipmentCreate, db: Session = Depends(get_db)) -> Equipment:
    equipment = Equipment(**payload.dict())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


@app.get("/equipment", response_model=list[EquipmentRead], tags=["equipment"])
def list_equipment(db: Session = Depends(get_db)) -> list[Equipment]:
    return db.query(Equipment).all()


@app.post("/sensors", response_model=SensorRead, tags=["sensors"])
def create_sensor(payload: SensorCreate, db: Session = Depends(get_db)) -> Sensor:
    sensor = Sensor(**payload.dict())
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


@app.get("/sensors", response_model=list[SensorRead], tags=["sensors"])
def list_sensors(db: Session = Depends(get_db)) -> list[Sensor]:
    return db.query(Sensor).all()
