from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ControlCreate(BaseModel):
    race_id: int
    sort_order: int
    name: str
    emit_code: str | None = None
    is_finish: bool = False


class ControlUpdate(BaseModel):
    sort_order: int | None = None
    name: str | None = None
    emit_code: str | None = None
    is_finish: bool | None = None


class ControlRead(BaseModel):
    id: int
    race_id: int
    sort_order: int
    name: str
    emit_code: str | None
    is_finish: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
