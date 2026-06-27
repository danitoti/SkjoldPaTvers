import csv
import io

from sqlalchemy.orm import Session

from backend.app.models.athlete import Athlete
from backend.app.models.control import Control
from backend.app.models.race import Race
from backend.app.models.result import Result
from backend.app.models.result_split import ResultSplit
from backend.app.parser.emit_parser import format_seconds


EQ_TIMING_HEADER = [
    "Startnummer",
    "Fornavn",
    "Etternavn",
    "Fødselsdato",
    "Kjønn",
    "Klubb",
    "Nasjonalitet",
    "Øvelse",
    "Klasse",
    "Starttid",
    "Punkt",
    "Sluttid",
    "Exitstatus",
    "Plassering",
    "",
]


def _format_start_time(race: Race) -> str:
    if race.start_time is None:
        return ""

    return race.start_time.strftime("%H:%M:%S")


def _result_sort_key(row: tuple[Result, Athlete]) -> tuple[int, int]:
    result, athlete = row

    if result.total_seconds is None:
        return (999999999, athlete.start_number or 999999999)

    return (result.total_seconds, athlete.start_number or 999999999)


def build_results_export_csv(
    db: Session,
    race_id: int,
) -> str:
    """
    Builds an EQ Timing compatible semicolon-separated CSV.

    Format matches the EQ Timing export template:

        Startnummer;Fornavn;Etternavn;Fødselsdato;Kjønn;Klubb;Nasjonalitet;Øvelse;Klasse;Starttid;Punkt;Sluttid;Exitstatus;Plassering;

    Important:
    - Only athletes with a finished result are exported.
    - The file has one row per athlete per point/control.
    - Sluttid contains accumulated time from common start to that point.
    - Column order is kept identical to the EQ Timing file.
    """

    race = db.query(Race).filter(Race.id == race_id).first()

    if race is None:
        raise ValueError("Løp finnes ikke")

    controls = (
        db.query(Control)
        .filter(Control.race_id == race_id)
        .order_by(Control.sort_order.asc())
        .all()
    )

    result_athlete_rows = (
        db.query(Result, Athlete)
        .join(Athlete, Result.athlete_id == Athlete.id)
        .filter(
            Result.race_id == race_id,
            Result.total_seconds.isnot(None),
        )
        .all()
    )

    result_athlete_rows = sorted(result_athlete_rows, key=_result_sort_key)

    result_ids = [
        result.id
        for result, athlete in result_athlete_rows
    ]

    splits_by_result_and_control: dict[tuple[int, int], ResultSplit] = {}

    if result_ids:
        splits = (
            db.query(ResultSplit)
            .filter(ResultSplit.result_id.in_(result_ids))
            .all()
        )

        splits_by_result_and_control = {
            (split.result_id, split.control_id): split
            for split in splits
        }

    output = io.StringIO()

    writer = csv.writer(
        output,
        delimiter=";",
        lineterminator="\n",
    )

    writer.writerow(EQ_TIMING_HEADER)

    start_time = _format_start_time(race)

    placing = 0
    previous_total_seconds = None
    visible_rank = 0

    for result, athlete in result_athlete_rows:
        placing += 1

        if previous_total_seconds != result.total_seconds:
            visible_rank = placing
            previous_total_seconds = result.total_seconds

        for control in controls:
            split = splits_by_result_and_control.get(
                (result.id, control.id)
            )

            if split is None or split.time_from_start_seconds is None:
                sluttid = ""
            else:
                sluttid = format_seconds(split.time_from_start_seconds)

            writer.writerow(
                [
                    athlete.start_number or "",
                    athlete.first_name or "",
                    athlete.last_name or "",
                    "",
                    athlete.gender or "",
                    athlete.club or "",
                    "",
                    race.name,
                    athlete.class_name or "",
                    start_time,
                    control.name,
                    sluttid,
                    "",
                    visible_rank,
                    "",
                ]
            )

    return "\ufeff" + output.getvalue()
