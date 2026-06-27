from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.app.database.dependencies import get_db
from backend.app.models.athlete import Athlete
from backend.app.models.race import Race
from backend.app.models.result import Result
from backend.app.parser.emit_parser import format_seconds

router = APIRouter(tags=["live"])

templates = Jinja2Templates(directory="backend/app/templates")


def _gender_group(gender: str | None, class_name: str | None) -> str:
    value = f"{gender or ''} {class_name or ''}".strip().lower()

    female_words = [
        "k",
        "f",
        "female",
        "woman",
        "women",
        "dame",
        "damer",
        "kvinne",
        "kvinner",
        "jente",
        "jenter",
    ]

    male_words = [
        "m",
        "male",
        "man",
        "men",
        "herre",
        "herrer",
        "gutt",
        "gutter",
    ]

    words = set(value.replace("-", " ").replace("_", " ").split())

    if words.intersection(female_words):
        return "female"

    if words.intersection(male_words):
        return "male"

    if "dame" in value or "kvinne" in value:
        return "female"

    if "herre" in value or "mann" in value:
        return "male"

    return "unknown"


def _result_row(result: Result, athlete: Athlete | None) -> dict:
    return {
        "result_id": result.id,
        "start_number": athlete.start_number if athlete else None,
        "name": (
            f"{athlete.first_name or ''} {athlete.last_name or ''}".strip()
            if athlete
            else "Ukjent løper"
        ),
        "club": athlete.club if athlete else "",
        "class_name": athlete.class_name if athlete else "",
        "gender": athlete.gender if athlete else "",
        "time": format_seconds(result.total_seconds),
        "total_seconds": result.total_seconds,
        "missing_controls": result.missing_controls,
        "status": result.status,
    }


@router.get("/live")
def live_results(
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

    if race_id is not None:
        selected_race = db.query(Race).filter(Race.id == race_id).first()
    elif races:
        selected_race = races[0]

    women = []
    men = []
    unknown = []

    if selected_race is not None:
        results = (
            db.query(Result)
            .filter(
                Result.race_id == selected_race.id,
                Result.total_seconds.isnot(None),
            )
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
            row = _result_row(result, athlete)

            group = _gender_group(
                athlete.gender if athlete else None,
                athlete.class_name if athlete else None,
            )

            if group == "female":
                women.append(row)
            elif group == "male":
                men.append(row)
            else:
                unknown.append(row)

    return templates.TemplateResponse(
        request=request,
        name="live.html",
        context={
            "races": races,
            "selected_race": selected_race,
            "women": women,
            "men": men,
            "unknown": unknown,
        },
    )
