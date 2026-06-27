import csv
import io

from sqlalchemy.orm import Session

from backend.app.models.athlete import Athlete
from backend.app.models.control import Control
from backend.app.models.race import Race
from backend.app.models.result import Result
from backend.app.models.result_split import ResultSplit
from backend.app.parser.emit_parser import format_seconds


def build_results_export_csv(
    db: Session,
    race_id: int,
) -> str:
    """
    Builds a semicolon-separated CSV export with one row per athlete.

    Includes:
    - participant data
    - final result
    - missing-control count
    - dynamic split columns for all controls in the race

    This is intentionally stable and readable for Excel/EQ Timing workflows.
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

    athletes = (
        db.query(Athlete)
        .filter(Athlete.race_id == race_id)
        .order_by(Athlete.start_number.asc())
        .all()
    )

    results = (
        db.query(Result)
        .filter(Result.race_id == race_id)
        .all()
    )

    results_by_athlete_id = {
        result.athlete_id: result
        for result in results
    }

    result_ids = [
        result.id
        for result in results
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

    # Excel in Norwegian locale handles semicolon CSV best.
    writer = csv.writer(
        output,
        delimiter=";",
        lineterminator="\n",
    )

    header = [
        "Løp",
        "Startnummer",
        "Fornavn",
        "Etternavn",
        "Klubb",
        "Kjønn",
        "Klasse",
        "Brikke",
        "Status",
        "Sluttid",
        "Manglende poster",
    ]

    for control in controls:
        control_label = f"{control.sort_order} {control.name} ({control.emit_code})"

        header.extend(
            [
                f"{control_label} - tid fra start",
                f"{control_label} - strekktid",
                f"{control_label} - status",
            ]
        )

    writer.writerow(header)

    for athlete in athletes:
        result = results_by_athlete_id.get(athlete.id)

        if result is None:
            status = "ikke_i_maal"
            total_time = ""
            missing_controls = ""
        else:
            status = result.status or ""
            total_time = format_seconds(result.total_seconds)
            missing_controls = result.missing_controls

        row = [
            race.name,
            athlete.start_number,
            athlete.first_name or "",
            athlete.last_name or "",
            athlete.club or "",
            athlete.gender or "",
            athlete.class_name or "",
            athlete.chip_number or "",
            status,
            total_time,
            missing_controls,
        ]

        for control in controls:
            split = None

            if result is not None:
                split = splits_by_result_and_control.get(
                    (result.id, control.id)
                )

            if split is None or split.time_from_start_seconds is None:
                row.extend(["", "", "mangler"])
            else:
                row.extend(
                    [
                        format_seconds(split.time_from_start_seconds),
                        format_seconds(split.split_seconds),
                        "ok",
                    ]
                )

        writer.writerow(row)

    # UTF-8 BOM makes æøå display correctly in Excel.
    return "\ufeff" + output.getvalue()
