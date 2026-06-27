from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.services.eqtiming_import_service import import_eqtiming_csv_bytes

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/eqtiming/{race_id}")
async def import_eqtiming_csv(
    race_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()

    summary = import_eqtiming_csv_bytes(
        db=db,
        race_id=race_id,
        content=content,
    )

    db.commit()

    return {
        "status": "ok",
        "created": summary.created,
        "updated": summary.updated,
        "skipped": summary.skipped,
        "errors": summary.errors,
        "detected_columns": summary.detected_columns,
    }
