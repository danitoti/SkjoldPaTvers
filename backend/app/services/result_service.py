from sqlalchemy.orm import Session

from backend.app.models.control import Control
from backend.app.models.event_log import EventLog
from backend.app.models.race import Race
from backend.app.models.raw_scan import RawScan
from backend.app.models.result import Result
from backend.app.models.result_split import ResultSplit
from backend.app.models.scan_punch import ScanPunch


def rebuild_result_for_scan(
    db: Session,
    raw_scan: RawScan,
) -> Result | None:
    """
    Rebuilds the official result for a scan.

    Official time basis:
    - raw_scan.received_at is the server time when the scan was stored
    - raw_scan.finish_to_scan_seconds is read from EMIT
    - finish_datetime = received_at - finish_to_scan_seconds
    - total_seconds = finish_datetime - race.start_time

    EMIT accumulated times are only used to place intermediate controls
    relative to the official finish time.
    """

    if raw_scan.athlete_id is None:
        db.add(
            EventLog(
                race_id=raw_scan.race_id,
                severity="WARNING",
                source="result",
                message=(
                    f"Kan ikke beregne resultat for brikke "
                    f"{raw_scan.chip_number or '-'}: ukjent løper"
                ),
                related_scan_id=raw_scan.id,
            )
        )
        return None

    race = db.query(Race).filter(Race.id == raw_scan.race_id).first()

    if race is None:
        db.add(
            EventLog(
                race_id=raw_scan.race_id,
                severity="ERROR",
                source="result",
                message="Kan ikke beregne resultat: løp finnes ikke",
                related_scan_id=raw_scan.id,
                related_athlete_id=raw_scan.athlete_id,
            )
        )
        return None

    if race.start_time is None:
        db.add(
            EventLog(
                race_id=raw_scan.race_id,
                severity="WARNING",
                source="result",
                message="Kan ikke beregne resultat: fellesstart er ikke satt",
                related_scan_id=raw_scan.id,
                related_athlete_id=raw_scan.athlete_id,
            )
        )
        return None

    if raw_scan.received_at is None:
        db.add(
            EventLog(
                race_id=raw_scan.race_id,
                severity="ERROR",
                source="result",
                message="Kan ikke beregne resultat: mangler serverens mottakstid",
                related_scan_id=raw_scan.id,
                related_athlete_id=raw_scan.athlete_id,
            )
        )
        return None

    if raw_scan.finish_to_scan_seconds is None:
        db.add(
            EventLog(
                race_id=raw_scan.race_id,
                severity="WARNING",
                source="result",
                message="Kan ikke beregne resultat: mangler tid fra mål til skanner",
                related_scan_id=raw_scan.id,
                related_athlete_id=raw_scan.athlete_id,
            )
        )
        return None

    from datetime import timedelta

    finish_datetime = raw_scan.received_at.replace(microsecond=0) - timedelta(
        seconds=raw_scan.finish_to_scan_seconds
    )

    total_seconds = int((finish_datetime - race.start_time).total_seconds())

    result = (
        db.query(Result)
        .filter(
            Result.race_id == raw_scan.race_id,
            Result.athlete_id == raw_scan.athlete_id,
        )
        .first()
    )

    if result is None:
        result = Result(
            race_id=raw_scan.race_id,
            athlete_id=raw_scan.athlete_id,
        )
        db.add(result)
        db.flush()
    else:
        db.query(ResultSplit).filter(ResultSplit.result_id == result.id).delete()

    result.source_raw_scan_id = raw_scan.id
    result.finish_datetime = finish_datetime
    result.total_seconds = total_seconds
    result.status = "ok"
    result.note = None

    controls = (
        db.query(Control)
        .filter(Control.race_id == raw_scan.race_id)
        .order_by(Control.sort_order.asc())
        .all()
    )

    valid_punches = (
        db.query(ScanPunch)
        .filter(
            ScanPunch.raw_scan_id == raw_scan.id,
            ScanPunch.ignored.is_(False),
            ScanPunch.control_id.isnot(None),
        )
        .all()
    )

    punches_by_control_id = {
        punch.control_id: punch
        for punch in valid_punches
    }

    finish_control = next(
        (control for control in controls if control.is_finish),
        None,
    )

    finish_punch = None

    if finish_control is not None:
        finish_punch = punches_by_control_id.get(finish_control.id)

    missing_controls = 0
    previous_time_from_start = None

    for control in controls:
        punch = punches_by_control_id.get(control.id)

        has_punch = punch is not None
        time_from_start_seconds = None
        split_seconds = None

        if not has_punch:
            missing_controls += 1
        elif control.is_finish:
            time_from_start_seconds = total_seconds
        elif (
            finish_punch is not None
            and finish_punch.accumulated_seconds is not None
            and punch.accumulated_seconds is not None
        ):
            seconds_before_finish = (
                finish_punch.accumulated_seconds - punch.accumulated_seconds
            )
            time_from_start_seconds = total_seconds - seconds_before_finish

        if time_from_start_seconds is not None:
            if previous_time_from_start is None:
                split_seconds = time_from_start_seconds
            else:
                split_seconds = time_from_start_seconds - previous_time_from_start

            previous_time_from_start = time_from_start_seconds

        db.add(
            ResultSplit(
                result_id=result.id,
                control_id=control.id,
                source_scan_punch_id=punch.id if punch is not None else None,
                has_punch=has_punch,
                time_from_start_seconds=time_from_start_seconds,
                split_seconds=split_seconds,
            )
        )

    result.missing_controls = missing_controls

    db.add(
        EventLog(
            race_id=raw_scan.race_id,
            severity="INFO",
            source="result",
            message=(
                f"Beregnet resultat for løper-id {raw_scan.athlete_id}: "
                f"{total_seconds} sek"
            ),
            related_scan_id=raw_scan.id,
            related_athlete_id=raw_scan.athlete_id,
        )
    )

    return result
