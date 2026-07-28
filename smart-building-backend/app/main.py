"""FastAPI entrypoint for the smart building backend."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import ensure_schema, get_db
from app.exceptions import WorkflowError
from app.models import Building, Equipment, Sensor
from app.routers.pilots import router as pilots_router
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

@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    yield


app = FastAPI(title="BAMBO Pilot Backend", version="0.2.0", lifespan=lifespan)
app.include_router(pilots_router)


@app.exception_handler(WorkflowError)
async def workflow_error_handler(_, exc: WorkflowError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_body())


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/buildings", response_model=BuildingRead, tags=["buildings"])
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)) -> Building:
    building = Building(**payload.model_dump())
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

    for field, value in payload.model_dump(exclude_unset=True).items():
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
    if not db.get(Building, payload.building_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    equipment = Equipment(**payload.model_dump())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


@app.get("/equipment", response_model=list[EquipmentRead], tags=["equipment"])
def list_equipment(db: Session = Depends(get_db)) -> list[Equipment]:
    return db.query(Equipment).all()


@app.get("/equipment/{equipment_id}", response_model=EquipmentRead, tags=["equipment"])
def get_equipment(equipment_id: int, db: Session = Depends(get_db)) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return equipment


@app.put("/equipment/{equipment_id}", response_model=EquipmentRead, tags=["equipment"])
def update_equipment(
    equipment_id: int, payload: EquipmentUpdate, db: Session = Depends(get_db)
) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    changes = payload.model_dump(exclude_unset=True)
    if "building_id" in changes and not db.get(Building, changes["building_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    for field, value in changes.items():
        setattr(equipment, field, value)
    db.commit()
    db.refresh(equipment)
    return equipment


@app.delete("/equipment/{equipment_id}", tags=["equipment"])
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    db.delete(equipment)
    db.commit()
    return {"message": "Equipment deleted"}


@app.post("/sensors", response_model=SensorRead, tags=["sensors"])
def create_sensor(payload: SensorCreate, db: Session = Depends(get_db)) -> Sensor:
    if not db.get(Equipment, payload.equipment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    sensor = Sensor(**payload.model_dump())
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


@app.get("/sensors", response_model=list[SensorRead], tags=["sensors"])
def list_sensors(db: Session = Depends(get_db)) -> list[Sensor]:
    return db.query(Sensor).all()


@app.get("/sensors/{sensor_id}", response_model=SensorRead, tags=["sensors"])
def get_sensor(sensor_id: int, db: Session = Depends(get_db)) -> Sensor:
    sensor = db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor


@app.put("/sensors/{sensor_id}", response_model=SensorRead, tags=["sensors"])
def update_sensor(sensor_id: int, payload: SensorUpdate, db: Session = Depends(get_db)) -> Sensor:
    sensor = db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    changes = payload.model_dump(exclude_unset=True)
    if "equipment_id" in changes and not db.get(Equipment, changes["equipment_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    for field, value in changes.items():
        setattr(sensor, field, value)
    db.commit()
    db.refresh(sensor)
    return sensor


@app.delete("/sensors/{sensor_id}", tags=["sensors"])
def delete_sensor(sensor_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    sensor = db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    db.delete(sensor)
    db.commit()
    return {"message": "Sensor deleted"}
