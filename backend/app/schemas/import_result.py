from pydantic import BaseModel


class ImportResult(BaseModel):
    race_id: int
    filename: str
    imported: int
    updated: int
    skipped: int
    errors: list[str]
