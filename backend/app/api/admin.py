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
    from backend.app.services.result_service import rebuild_results_for_race

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

    summary = rebuild_results_for_race(
        db=db,
        race_id=race.id,
    )

    db.commit()

    return _redirect_to_admin(
        race.id,
        (
            f"Starttid oppdatert. "
            f"{summary['rebuilt']} resultat(er) beregnet på nytt."
        ),
    )


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
    scan_received_at: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    from backend.app.services.scan_service import store_emit_scan

    try:
        summary = store_emit_scan(
            db=db,
            race_id=race_id,
            raw_text=raw_text,
            received_at_override=_parse_datetime(scan_received_at),
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


@router.get("/admin/results")
def results_page(
    request: Request,
    race_id: int | None = None,
    db: Session = Depends(get_db),
):
    from backend.app.models.result import Result

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

    rows = []

    if selected_race is not None:
        results = (
            db.query(Result)
            .filter(Result.race_id == selected_race.id)
            .order_by(Result.total_seconds.asc())
            .all()
        )

        athlete_ids = [result.athlete_id for result in results]

        athletes_by_id = {}

        if athlete_ids:
            athletes = (
                db.query(Athlete)
                .filter(Athlete.id.in_(athlete_ids))
                .all()
            )
            athletes_by_id = {athlete.id: athlete for athlete in athletes}

        for result in results:
            athlete = athletes_by_id.get(result.athlete_id)

            rows.append(
                {
                    "result": result,
                    "athlete": athlete,
                }
            )

    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={
            "races": races,
            "selected_race": selected_race,
            "rows": rows,
        },
    )


@router.get("/admin/results/{result_id}")
def result_detail_page(
    request: Request,
    result_id: int,
    db: Session = Depends(get_db),
):
    from backend.app.models.result import Result
    from backend.app.models.result_split import ResultSplit
    from backend.app.models.scan_punch import ScanPunch
    from backend.app.parser.emit_parser import format_seconds

    result = db.query(Result).filter(Result.id == result_id).first()

    if result is None:
        return RedirectResponse(
            url="/admin/results",
            status_code=303,
        )

    race = db.query(Race).filter(Race.id == result.race_id).first()
    athlete = db.query(Athlete).filter(Athlete.id == result.athlete_id).first()

    split_rows = (
        db.query(ResultSplit, Control, ScanPunch)
        .join(Control, ResultSplit.control_id == Control.id)
        .outerjoin(ScanPunch, ResultSplit.source_scan_punch_id == ScanPunch.id)
        .filter(ResultSplit.result_id == result.id)
        .order_by(Control.sort_order.asc())
        .all()
    )

    rows = []

    for result_split, control, scan_punch in split_rows:
        rows.append(
            {
                "split": result_split,
                "control": control,
                "punch": scan_punch,
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="result_detail.html",
        context={
            "race": race,
            "athlete": athlete,
            "result": result,
            "rows": rows,
            "format_seconds": format_seconds,
        },
    )


@router.post("/admin/races/{race_id}/rebuild-results")
def rebuild_results_admin(
    race_id: int,
    db: Session = Depends(get_db),
):
    from backend.app.services.result_service import rebuild_results_for_race

    race = db.query(Race).filter(Race.id == race_id).first()

    if race is None:
        return _redirect_to_admin(message="Løp finnes ikke")

    summary = rebuild_results_for_race(
        db=db,
        race_id=race.id,
    )

    db.commit()

    return _redirect_to_admin(
        race.id,
        (
            f"Resultater beregnet på nytt: "
            f"{summary['rebuilt']} oppdatert, "
            f"{summary['skipped']} hoppet over."
        ),
    )


@router.get("/admin/scans/unknown")
def unknown_scans_page(
    request: Request,
    race_id: int | None = None,
    message: str | None = None,
    db: Session = Depends(get_db),
):
    from backend.app.models.raw_scan import RawScan

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

    unknown_scans = []

    if selected_race is not None:
        unknown_scans = (
            db.query(RawScan)
            .filter(
                RawScan.race_id == selected_race.id,
                RawScan.is_active.is_(True),
                RawScan.parse_status == "unknown_chip",
            )
            .order_by(RawScan.received_at.desc())
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="unknown_scans.html",
        context={
            "races": races,
            "selected_race": selected_race,
            "unknown_scans": unknown_scans,
            "message": message,
        },
    )


@router.post("/admin/scans/unknown/{raw_scan_id}/match")
def match_unknown_scan(
    raw_scan_id: int,
    race_id: int = Form(...),
    start_number: int = Form(...),
    db: Session = Depends(get_db),
):
    from backend.app.models.raw_scan import RawScan
    from backend.app.services.result_service import rebuild_result_for_scan

    raw_scan = (
        db.query(RawScan)
        .filter(
            RawScan.id == raw_scan_id,
            RawScan.race_id == race_id,
        )
        .first()
    )

    if raw_scan is None:
        return RedirectResponse(
            url=f"/admin/scans/unknown?race_id={race_id}&message=Skanning finnes ikke",
            status_code=303,
        )

    if not raw_scan.chip_number:
        return RedirectResponse(
            url=f"/admin/scans/unknown?race_id={race_id}&message=Skanningen mangler brikkenummer",
            status_code=303,
        )

    athlete = (
        db.query(Athlete)
        .filter(
            Athlete.race_id == race_id,
            Athlete.start_number == start_number,
        )
        .first()
    )

    if athlete is None:
        return RedirectResponse(
            url=f"/admin/scans/unknown?race_id={race_id}&message=Fant ikke startnummer {start_number}",
            status_code=303,
        )

    existing_chip_owner = (
        db.query(Athlete)
        .filter(
            Athlete.race_id == race_id,
            Athlete.chip_number == raw_scan.chip_number,
            Athlete.id != athlete.id,
        )
        .first()
    )

    if existing_chip_owner is not None:
        return RedirectResponse(
            url=(
                f"/admin/scans/unknown?race_id={race_id}"
                f"&message=Brikke {raw_scan.chip_number} er allerede koblet til startnummer {existing_chip_owner.start_number}"
            ),
            status_code=303,
        )

    old_chip = athlete.chip_number
    athlete.chip_number = raw_scan.chip_number
    raw_scan.athlete_id = athlete.id

    remaining_warnings = []

    if raw_scan.error_message:
        for line in raw_scan.error_message.splitlines():
            if "finnes ikke på løperlisten" not in line:
                remaining_warnings.append(line)

    raw_scan.error_message = "\n".join(remaining_warnings) if remaining_warnings else None
    raw_scan.parse_status = "warning" if remaining_warnings else "ok"

    db.add(
        EventLog(
            race_id=race_id,
            severity="INFO",
            source="admin.unknown_chip",
            message=(
                f"Koblet ukjent brikke {raw_scan.chip_number} "
                f"til startnummer {athlete.start_number}. "
                f"Tidligere brikke: {old_chip or '-'}"
            ),
            related_scan_id=raw_scan.id,
            related_athlete_id=athlete.id,
        )
    )

    rebuild_result_for_scan(
        db=db,
        raw_scan=raw_scan,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        return RedirectResponse(
            url=(
                f"/admin/scans/unknown?race_id={race_id}"
                f"&message=Kunne ikke koble brikke. Brikkenummeret er sannsynligvis allerede i bruk."
            ),
            status_code=303,
        )

    return RedirectResponse(
        url=(
            f"/admin/scans/unknown?race_id={race_id}"
            f"&message=Brikke {raw_scan.chip_number} koblet til startnummer {athlete.start_number}"
        ),
        status_code=303,
    )


@router.get("/admin/rs232")
def rs232_page(
    request: Request,
    message: str | None = None,
    db: Session = Depends(get_db),
):
    from backend.app.models.rs232_settings import Rs232Settings
    from backend.app.rs232.serial_ports import list_serial_ports

    ports = list_serial_ports()

    races = (
        db.query(Race)
        .order_by(Race.created_at.desc())
        .all()
    )

    settings = (
        db.query(Rs232Settings)
        .filter(Rs232Settings.id == 1)
        .first()
    )

    return templates.TemplateResponse(
        request=request,
        name="rs232.html",
        context={
            "ports": ports,
            "races": races,
            "settings": settings,
            "message": message,
        },
    )


@router.post("/admin/rs232/settings")
def save_rs232_settings(
    race_id: str | None = Form(default=None),
    port_select: str | None = Form(default=None),
    port_manual: str | None = Form(default=None),
    baudrate: str = Form(default="9600"),
    db: Session = Depends(get_db),
):
    from urllib.parse import quote

    from backend.app.models.rs232_settings import Rs232Settings

    try:
        selected_race_id = int(race_id) if race_id and race_id.strip() else None
    except ValueError:
        return RedirectResponse(
            url="/admin/rs232?message=Ugyldig løp",
            status_code=303,
        )

    try:
        baudrate_value = int(baudrate)
    except ValueError:
        return RedirectResponse(
            url="/admin/rs232?message=Ugyldig baudrate",
            status_code=303,
        )

    if baudrate_value <= 0:
        return RedirectResponse(
            url="/admin/rs232?message=Ugyldig baudrate",
            status_code=303,
        )

    if selected_race_id is not None:
        race = db.query(Race).filter(Race.id == selected_race_id).first()

        if race is None:
            return RedirectResponse(
                url="/admin/rs232?message=Løp finnes ikke",
                status_code=303,
            )
    else:
        race = None

    port = (port_manual or "").strip() or (port_select or "").strip() or None

    settings = (
        db.query(Rs232Settings)
        .filter(Rs232Settings.id == 1)
        .first()
    )

    if settings is None:
        settings = Rs232Settings(id=1)

    settings.selected_race_id = selected_race_id
    settings.port = port
    settings.baudrate = baudrate_value
    settings.is_enabled = False

    db.add(settings)

    if race is not None:
        db.add(
            EventLog(
                race_id=race.id,
                severity="INFO",
                source="admin.rs232",
                message=(
                    f"Oppdaterte RS-232-oppsett: "
                    f"port={port or '-'}, baudrate={baudrate_value}"
                ),
            )
        )

    db.commit()

    message = quote("RS-232-oppsett lagret")

    return RedirectResponse(
        url=f"/admin/rs232?message={message}",
        status_code=303,
    )


@router.post("/admin/rs232/read-once")
def read_one_rs232_scan(
    db: Session = Depends(get_db),
):
    from urllib.parse import quote

    from backend.app.models.rs232_settings import Rs232Settings
    from backend.app.rs232.serial_reader import RS232EmitReader
    from backend.app.services.scan_service import store_emit_scan

    settings = (
        db.query(Rs232Settings)
        .filter(Rs232Settings.id == 1)
        .first()
    )

    if settings is None:
        return RedirectResponse(
            url="/admin/rs232?message=RS-232-oppsett mangler",
            status_code=303,
        )

    if not settings.selected_race_id:
        return RedirectResponse(
            url="/admin/rs232?message=Velg løp før lesing",
            status_code=303,
        )

    if not settings.port:
        return RedirectResponse(
            url="/admin/rs232?message=Velg serieport før lesing",
            status_code=303,
        )

    race = db.query(Race).filter(Race.id == settings.selected_race_id).first()

    if race is None:
        return RedirectResponse(
            url="/admin/rs232?message=Valgt løp finnes ikke",
            status_code=303,
        )

    try:
        reader = RS232EmitReader(
            port=settings.port,
            baudrate=settings.baudrate,
            timeout=settings.timeout_seconds or 1.0,
        )

        raw_text = reader.read_one_frame()

    except Exception as exc:
        message = quote(f"Kunne ikke lese fra {settings.port}: {exc}")

        return RedirectResponse(
            url=f"/admin/rs232?message={message}",
            status_code=303,
        )

    if raw_text is None:
        message = quote(
            "Ingen komplett EMIT-skanning mottatt. "
            "Dette er normalt hvis skanneren ikke er koblet til eller ikke sender nå."
        )

        return RedirectResponse(
            url=f"/admin/rs232?message={message}",
            status_code=303,
        )

    try:
        summary = store_emit_scan(
            db=db,
            race_id=race.id,
            raw_text=raw_text,
        )

        db.commit()

    except Exception as exc:
        db.rollback()

        message = quote(f"Mottok skanning, men klarte ikke å lagre den: {exc}")

        return RedirectResponse(
            url=f"/admin/rs232?message={message}",
            status_code=303,
        )

    if summary.athlete_name:
        message_text = (
            f"Lagret skanning for brikke {summary.chip_number} "
            f"({summary.athlete_name})"
        )
    else:
        message_text = (
            f"Lagret skanning for brikke {summary.chip_number}. "
            "Brikken er ikke koblet til løper."
        )

    message = quote(message_text)

    return RedirectResponse(
        url=f"/admin/rs232?message={message}",
        status_code=303,
    )
