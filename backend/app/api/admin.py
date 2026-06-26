from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
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


def _clean(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return value


def _redirect_to_admin(
    race_id: int | None = None,
    message: str | None = None,
    athlete_search: str | None = None,
):
    url = "/admin"

    query_parts = []

    if race_id is not None:
        query_parts.append(f"race_id={race_id}")

    if message:
        query_parts.append(f"message={message}")

    if athlete_search:
        query_parts.append(f"athlete_search={athlete_search}")

    if query_parts:
        url += "?" + "&".join(query_parts)

    return RedirectResponse(url=url, status_code=303)


@router.get("/admin")
def admin_dashboard(
    request: Request,
    race_id: int | None = None,
    message: str | None = None,
    athlete_search: str | None = None,
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
    athletes = []
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

        athletes_query = (
            db.query(Athlete)
            .filter(Athlete.race_id == selected_race.id)
        )

        search_value = _clean(athlete_search)

        if search_value:
            filters = [
                Athlete.chip_number.ilike(f"%{search_value}%"),
                Athlete.first_name.ilike(f"%{search_value}%"),
                Athlete.last_name.ilike(f"%{search_value}%"),
                Athlete.club.ilike(f"%{search_value}%"),
                Athlete.class_name.ilike(f"%{search_value}%"),
            ]

            if search_value.isdigit():
                filters.append(Athlete.start_number == int(search_value))

            athletes_query = athletes_query.filter(or_(*filters))

        athletes = (
            athletes_query
            .order_by(Athlete.start_number.asc())
            .limit(100)
            .all()
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
            "athletes": athletes,
            "athletes_count": athletes_count,
            "athlete_search": athlete_search or "",
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
        emit_code=_clean(emit_code),
        is_finish=is_finish == "on",
    )

    db.add(control)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect_to_admin(
            race_id,
            "Kunne ikke lagre post. Sjekk duplikat rekkefølge eller EMIT-kode.",
        )

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


@router.post("/admin/athletes/{athlete_id}/chip")
def update_athlete_chip(
    athlete_id: int,
    race_id: int = Form(...),
    chip_number: str | None = Form(default=None),
    athlete_search: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()

    if athlete is None:
        return _redirect_to_admin(race_id, "Løper finnes ikke", athlete_search)

    old_chip = athlete.chip_number
    athlete.chip_number = _clean(chip_number)

    db.add(
        EventLog(
            race_id=race_id,
            severity="INFO",
            source="admin.athletes",
            message=(
                f"Endret brikkenummer for startnr {athlete.start_number}: "
                f"{old_chip or '-'} -> {athlete.chip_number or '-'}"
            ),
            related_athlete_id=athlete.id,
        )
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect_to_admin(
            race_id,
            "Kunne ikke lagre brikkenummer. Det er sannsynligvis allerede i bruk.",
            athlete_search,
        )

    return _redirect_to_admin(race_id, "Brikkenummer oppdatert", athlete_search)


@router.get("/admin/emit-test")
def emit_test_page(
    request: Request,
    race_id: int | None = None,
    db: Session = Depends(get_db),
):
    races = (
        db.query(Race)
        .order_by(Race.created_at.desc())
        .all()
    )

    selected_race = None
    controls = []

    if race_id is not None:
        selected_race = db.query(Race).filter(Race.id == race_id).first()
    elif races:
        selected_race = races[0]

    if selected_race is not None:
        controls = (
            db.query(Control)
            .filter(Control.race_id == selected_race.id)
            .order_by(Control.sort_order.asc())
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="emit_test.html",
        context={
            "races": races,
            "selected_race": selected_race,
            "controls": controls,
            "raw_text": "",
            "parsed": None,
            "validation": None,
            "error": None,
        },
    )


@router.post("/admin/emit-test")
def emit_test_parse(
    request: Request,
    raw_text: str = Form(...),
    race_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    from backend.app.parser.emit_parser import parse_emit_scan
    from backend.app.services.emit_validation_service import (
        validate_emit_scan_against_controls,
    )

    races = (
        db.query(Race)
        .order_by(Race.created_at.desc())
        .all()
    )

    selected_race = None
    controls = []

    if race_id is not None:
        selected_race = db.query(Race).filter(Race.id == race_id).first()
    elif races:
        selected_race = races[0]

    if selected_race is not None:
        controls = (
            db.query(Control)
            .filter(Control.race_id == selected_race.id)
            .order_by(Control.sort_order.asc())
            .all()
        )

    parsed = None
    validation = None
    error = None

    try:
        parsed = parse_emit_scan(raw_text)

        if selected_race is not None:
            validation = validate_emit_scan_against_controls(
                parsed=parsed,
                controls=controls,
            )
    except Exception as exc:
        error = str(exc)

    return templates.TemplateResponse(
        request=request,
        name="emit_test.html",
        context={
            "races": races,
            "selected_race": selected_race,
            "controls": controls,
            "raw_text": raw_text,
            "parsed": parsed,
            "validation": validation,
            "error": error,
        },
    )


@router.get("/admin/scans/manual")
def manual_scan_page(
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

    raw_scans = []
    athletes_by_id = {}

    if selected_race is not None:
        from backend.app.models.raw_scan import RawScan

        raw_scans = (
            db.query(RawScan)
            .filter(RawScan.race_id == selected_race.id)
            .order_by(RawScan.received_at.desc())
            .limit(25)
            .all()
        )

        athlete_ids = [
            scan.athlete_id
            for scan in raw_scans
            if scan.athlete_id is not None
        ]

        if athlete_ids:
            athletes = (
                db.query(Athlete)
                .filter(Athlete.id.in_(athlete_ids))
                .all()
            )
            athletes_by_id = {athlete.id: athlete for athlete in athletes}

    return templates.TemplateResponse(
        request=request,
        name="manual_scan.html",
        context={
            "races": races,
            "selected_race": selected_race,
            "raw_scans": raw_scans,
            "athletes_by_id": athletes_by_id,
            "message": message,
        },
    )


@router.post("/admin/scans/manual")
def manual_scan_submit(
    race_id: int = Form(...),
    raw_text: str = Form(...),
    db: Session = Depends(get_db),
):
    from backend.app.services.scan_service import store_emit_scan

    try:
        summary = store_emit_scan(
            db=db,
            race_id=race_id,
            raw_text=raw_text,
        )
    except Exception as exc:
        db.rollback()

        db.add(
            EventLog(
                race_id=race_id,
                severity="ERROR",
                source="scan.manual",
                message=f"Kunne ikke lagre skanning: {exc}",
            )
        )
        db.commit()

        return RedirectResponse(
            url=f"/admin/scans/manual?race_id={race_id}&message=Skanning feilet",
            status_code=303,
        )

    if summary.parse_status == "ok":
        message = f"Skanning lagret: brikke {summary.chip_number}"
    elif summary.parse_status == "unknown_chip":
        message = f"Skanning lagret, men brikken er ukjent: {summary.chip_number}"
    elif summary.parse_status == "warning":
        message = f"Skanning lagret med {summary.warning_count} advarsel/advarsler"
    else:
        message = "Skanning lagret med feil"

    return RedirectResponse(
        url=f"/admin/scans/manual?race_id={race_id}&message={message}",
        status_code=303,
    )
