from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.athlete import Athlete
from backend.app.models.control import Control
from backend.app.models.event_log import EventLog
from backend.app.models.race import Race
from backend.app.services.import_service import import_eqtiming_csv

router = APIRouter(tags=["admin"])

templates = Jinja2Templates(directory="backend/app/templates")


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None or value.strip() == "":
        return None

    return datetime.fromisoformat(value)


def _redirect_to_admin(race_id: int | None = None, message: str | None = None):
    url = "/admin"

    query_parts = []

    if race_id is not None:
        query_parts.append(f"race_id={race_id}")

    if message:
        query_parts.append(f"message={message}")

    if query_parts:
        url += "?" + "&".join(query_parts)

    return RedirectResponse(url=url, status_code=303)


@router.get("/admin")
def admin_dashboard(
    request: Request,
    race_id: int | None = None,
    message: str | None = None,
    db: Session = Depends(get_db),
):
    races = (
        db.query(Race)
        .order_by(Race.created_at.desc())
        .all()
    )

    selected_race = None

    if race_id is not None:
        selected_race = db.query(Race).filter(Race.id == race_id).first()
    elif races:
        selected_race = races[0]

    controls = []
    athletes_count = 0
    events_query = db.query(EventLog)

    if selected_race is not None:
        controls = (
            db.query(Control)
            .filter(Control.race_id == selected_race.id)
            .order_by(Control.sort_order.asc())
            .all()
        )

        athletes_count = (
            db.query(Athlete)
            .filter(Athlete.race_id == selected_race.id)
            .count()
        )

        events_query = events_query.filter(EventLog.race_id == selected_race.id)

    events = (
        events_query
        .order_by(EventLog.created_at.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "races": races,
            "selected_race": selected_race,
            "controls": controls,
            "athletes_count": athletes_count,
            "events": events,
            "message": message,
        },
    )


@router.post("/admin/races")
def create_race(
    name: str = Form(...),
    start_time: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    race = Race(
        name=name.strip(),
        start_time=_parse_datetime(start_time),
    )

    db.add(race)
    db.commit()
    db.refresh(race)

    db.add(
        EventLog(
            race_id=race.id,
            severity="INFO",
            source="admin",
            message=f"Opprettet løp: {race.name}",
        )
    )
    db.commit()

    return _redirect_to_admin(race.id, "Løp opprettet")


@router.post("/admin/races/{race_id}/start-time")
def update_race_start_time(
    race_id: int,
    start_time: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    race = db.query(Race).filter(Race.id == race_id).first()

    if race is None:
        return _redirect_to_admin(message="Løp finnes ikke")

    race.start_time = _parse_datetime(start_time)

    db.add(
        EventLog(
            race_id=race.id,
            severity="INFO",
            source="admin",
            message=f"Oppdaterte starttid for {race.name}",
        )
    )

    db.commit()

    return _redirect_to_admin(race.id, "Starttid oppdatert")


@router.post("/admin/controls")
def create_control(
    race_id: int = Form(...),
    sort_order: int = Form(...),
    name: str = Form(...),
    emit_code: str | None = Form(default=None),
    is_finish: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    control = Control(
        race_id=race_id,
        sort_order=sort_order,
        name=name.strip(),
        emit_code=emit_code.strip() if emit_code else None,
        is_finish=is_finish == "on",
    )

    db.add(control)
    db.commit()
    db.refresh(control)

    db.add(
        EventLog(
            race_id=race_id,
            severity="INFO",
            source="admin",
            message=f"La til post {control.sort_order}: {control.name}",
        )
    )
    db.commit()

    return _redirect_to_admin(race_id, "Post lagt til")


@router.post("/admin/controls/{control_id}/delete")
def delete_control(
    control_id: int,
    db: Session = Depends(get_db),
):
    control = db.query(Control).filter(Control.id == control_id).first()

    if control is None:
        return _redirect_to_admin(message="Post finnes ikke")

    race_id = control.race_id
    name = control.name

    db.delete(control)
    db.commit()

    db.add(
        EventLog(
            race_id=race_id,
            severity="INFO",
            source="admin",
            message=f"Slettet post: {name}",
        )
    )
    db.commit()

    return _redirect_to_admin(race_id, "Post slettet")


@router.post("/admin/import/eqtiming")
async def import_eqtiming_admin(
    race_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()

    try:
        summary = import_eqtiming_csv(
            db=db,
            race_id=race_id,
            content=content,
        )
    except Exception as exc:
        db.rollback()

        db.add(
            EventLog(
                race_id=race_id,
                severity="ERROR",
                source="admin.import",
                message=f"Import feilet: {exc}",
            )
        )
        db.commit()

        return _redirect_to_admin(race_id, "Import feilet")

    message = (
        f"Import OK: "
        f"{summary.imported} nye, "
        f"{summary.updated} oppdatert, "
        f"{summary.skipped} hoppet over"
    )

    return _redirect_to_admin(race_id, message)
