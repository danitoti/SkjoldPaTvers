from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventLogRead(BaseModel):
    id: int
    race_id: int | None
    severity: str
    source: str
    message: str
    related_scan_id: int | None
    related_athlete_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
