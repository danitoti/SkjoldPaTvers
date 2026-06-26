from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.schemas.import_result import ImportResult
from backend.app.services.import_service import import_eqtiming_csv

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/eqtiming/{race_id}", response_model=ImportResult)
async def import_eqtiming(
    race_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Filen må være CSV")

    content = await file.read()

    try:
        summary = import_eqtiming_csv(
            db=db,
            race_id=race_id,
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Import feilet. Sannsynlig duplikat startnummer eller brikkenummer.",
        ) from exc

    return ImportResult(
        race_id=race_id,
        filename=file.filename,
        imported=summary.imported,
        updated=summary.updated,
        skipped=summary.skipped,
        errors=summary.errors,
    )
