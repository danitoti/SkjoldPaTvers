from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.event_log import EventLog
from backend.app.models.race import Race
from backend.app.schemas.race import RaceCreate, RaceRead

router = APIRouter(prefix="/api/races", tags=["races"])


@router.post("/", response_model=RaceRead)
def create_race(payload: RaceCreate, db: Session = Depends(get_db)):
    race = Race(
        name=payload.name,
        start_time=payload.start_time,
    )

    db.add(race)
    db.commit()
    db.refresh(race)

    event = EventLog(
        race_id=race.id,
        severity="INFO",
        source="api.races",
        message=f"Opprettet løp: {race.name}",
    )

    db.add(event)
    db.commit()

    return race


@router.get("/", response_model=list[RaceRead])
def list_races(db: Session = Depends(get_db)):
    return (
        db.query(Race)
        .order_by(Race.created_at.desc())
        .all()
    )


@router.get("/{race_id}", response_model=RaceRead)
def get_race(race_id: int, db: Session = Depends(get_db)):
    race = db.query(Race).filter(Race.id == race_id).first()

    if race is None:
        raise HTTPException(status_code=404, detail="Løp finnes ikke")

    return race
