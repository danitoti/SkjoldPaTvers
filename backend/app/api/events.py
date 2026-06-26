from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.event_log import EventLog
from backend.app.schemas.event_log import EventLogRead

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/", response_model=list[EventLogRead])
def list_events(
    race_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(EventLog)

    if race_id is not None:
        query = query.filter(EventLog.race_id == race_id)

    return (
        query
        .order_by(EventLog.created_at.desc())
        .limit(limit)
        .all()
    )
