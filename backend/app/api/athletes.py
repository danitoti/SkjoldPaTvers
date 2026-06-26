from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.athlete import Athlete
from backend.app.schemas.athlete import AthleteRead

router = APIRouter(prefix="/api/athletes", tags=["athletes"])


@router.get("/", response_model=list[AthleteRead])
def list_athletes(
    race_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return (
        db.query(Athlete)
        .filter(Athlete.race_id == race_id)
        .order_by(Athlete.start_number.asc())
        .limit(limit)
        .all()
    )
