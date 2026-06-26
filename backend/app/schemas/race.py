from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RaceCreate(BaseModel):
    name: str
    start_time: datetime | None = None


class RaceRead(BaseModel):
    id: int
    name: str
    start_time: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
