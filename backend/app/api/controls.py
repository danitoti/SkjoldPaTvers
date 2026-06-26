from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.control import Control
from backend.app.models.event_log import EventLog
from backend.app.models.race import Race
from backend.app.schemas.control import ControlCreate, ControlRead, ControlUpdate

router = APIRouter(prefix="/api/controls", tags=["controls"])


def _race_exists(db: Session, race_id: int) -> bool:
    return db.query(Race.id).filter(Race.id == race_id).first() is not None


@router.post("/", response_model=ControlRead)
def create_control(payload: ControlCreate, db: Session = Depends(get_db)):
    if not _race_exists(db, payload.race_id):
        raise HTTPException(status_code=404, detail="Løp finnes ikke")

    control = Control(
        race_id=payload.race_id,
        sort_order=payload.sort_order,
        name=payload.name,
        emit_code=payload.emit_code,
        is_finish=payload.is_finish,
    )

    db.add(control)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Kunne ikke lagre post. Sjekk at rekkefølge og EMIT-kode er unike for løpet.",
        ) from exc

    db.refresh(control)

    db.add(
        EventLog(
            race_id=control.race_id,
            severity="INFO",
            source="api.controls",
            message=f"Opprettet post {control.sort_order}: {control.name}",
        )
    )
    db.commit()

    return control


@router.get("/", response_model=list[ControlRead])
def list_controls(race_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Control)
        .filter(Control.race_id == race_id)
        .order_by(Control.sort_order.asc())
        .all()
    )


@router.get("/{control_id}", response_model=ControlRead)
def get_control(control_id: int, db: Session = Depends(get_db)):
    control = db.query(Control).filter(Control.id == control_id).first()

    if control is None:
        raise HTTPException(status_code=404, detail="Post finnes ikke")

    return control


@router.put("/{control_id}", response_model=ControlRead)
def update_control(
    control_id: int,
    payload: ControlUpdate,
    db: Session = Depends(get_db),
):
    control = db.query(Control).filter(Control.id == control_id).first()

    if control is None:
        raise HTTPException(status_code=404, detail="Post finnes ikke")

    if payload.sort_order is not None:
        control.sort_order = payload.sort_order

    if payload.name is not None:
        control.name = payload.name

    if payload.emit_code is not None:
        control.emit_code = payload.emit_code

    if payload.is_finish is not None:
        control.is_finish = payload.is_finish

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Kunne ikke oppdatere post. Sjekk at rekkefølge og EMIT-kode er unike for løpet.",
        ) from exc

    db.refresh(control)

    db.add(
        EventLog(
            race_id=control.race_id,
            severity="INFO",
            source="api.controls",
            message=f"Oppdaterte post {control.sort_order}: {control.name}",
        )
    )
    db.commit()

    return control


@router.delete("/{control_id}")
def delete_control(control_id: int, db: Session = Depends(get_db)):
    control = db.query(Control).filter(Control.id == control_id).first()

    if control is None:
        raise HTTPException(status_code=404, detail="Post finnes ikke")

    race_id = control.race_id
    name = control.name

    db.delete(control)
    db.commit()

    db.add(
        EventLog(
            race_id=race_id,
            severity="INFO",
            source="api.controls",
            message=f"Slettet post: {name}",
        )
    )
    db.commit()

    return {"status": "deleted", "control_id": control_id}
