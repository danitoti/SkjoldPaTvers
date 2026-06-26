import csv
import io
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.models.athlete import Athlete
from backend.app.models.event_log import EventLog
from backend.app.models.race import Race


@dataclass
class ImportSummary:
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _decode_csv_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return value


def _to_int(value: str | None) -> int | None:
    value = _clean(value)

    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _get(row: dict, key: str) -> str | None:
    return _clean(row.get(key))


def import_eqtiming_csv(
    db: Session,
    race_id: int,
    content: bytes,
) -> ImportSummary:
    race = db.query(Race).filter(Race.id == race_id).first()

    if race is None:
        raise ValueError(f"Løp med id {race_id} finnes ikke")

    summary = ImportSummary()

    text = _decode_csv_bytes(content)
    reader = csv.DictReader(io.StringIO(text), delimiter=";")

    for line_number, row in enumerate(reader, start=2):
        start_number = _to_int(_get(row, "startnummer"))

        if start_number is None:
            summary.skipped += 1
            summary.errors.append(f"Linje {line_number}: mangler startnummer")
            continue

        birth_year = _to_int(_get(row, "yob"))

        chip_number = (
            _get(row, "chip1")
            or _get(row, "chip2")
        )

        club = (
            _get(row, "klubb")
            or _get(row, "klubb2")
            or _get(row, "team")
            or _get(row, "lagnavn")
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
            athlete = Athlete(
                race_id=race_id,
                start_number=start_number,
            )
            db.add(athlete)
            summary.imported += 1
        else:
            summary.updated += 1

        athlete.chip_number = chip_number
        athlete.first_name = _get(row, "fornavn")
        athlete.last_name = _get(row, "etternavn")
        athlete.club = club
        athlete.gender = _get(row, "kjonn")
        athlete.class_name = _get(row, "klasse")
        athlete.distance = _get(row, "distanse")
        athlete.country = _get(row, "land")
        athlete.birth_year = birth_year
        athlete.eqtiming_participant_uid = _get(row, "deltakeruid")
        athlete.eqtiming_athlete_uid = _get(row, "utoveruid")

    event = EventLog(
        race_id=race_id,
        severity="INFO",
        source="import.eqtiming",
        message=(
            f"Importerte EQ Timing CSV: "
            f"{summary.imported} nye, "
            f"{summary.updated} oppdatert, "
            f"{summary.skipped} hoppet over"
        ),
    )

    db.add(event)
    db.commit()

    return summary
