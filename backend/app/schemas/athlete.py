from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AthleteRead(BaseModel):
    id: int
    race_id: int
    start_number: int | None
    chip_number: str | None
    first_name: str | None
    last_name: str | None
    club: str | None
    gender: str | None
    class_name: str | None
    distance: str | None
    country: str | None
    birth_year: int | None
    eqtiming_participant_uid: str | None
    eqtiming_athlete_uid: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
