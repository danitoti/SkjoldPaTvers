from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.models.athlete import Athlete
from backend.app.models.control import Control
from backend.app.models.event_log import EventLog
from backend.app.models.raw_scan import RawScan
from backend.app.models.scan_punch import ScanPunch
from backend.app.parser.emit_parser import parse_emit_scan
from backend.app.services.result_service import rebuild_result_for_scan
from backend.app.utils.time_utils import server_now
from backend.app.services.emit_validation_service import (
    validate_emit_scan_against_controls,
)


@dataclass
class StoredScanSummary:
    raw_scan_id: int
    race_id: int
    chip_number: str | None
    athlete_id: int | None
    athlete_name: str | None
    parse_status: str
    punch_count: int
    valid_punch_count: int
    ignored_punch_count: int
    warning_count: int
    warnings: list[str]


def store_emit_scan(
    db: Session,
    race_id: int,
    raw_text: str,
    received_at_override: datetime | None = None,
) -> StoredScanSummary:
    parsed = parse_emit_scan(raw_text)

    controls = (
        db.query(Control)
        .filter(Control.race_id == race_id)
        .order_by(Control.sort_order.asc())
        .all()
    )

    validation = validate_emit_scan_against_controls(
        parsed=parsed,
        controls=controls,
    )

    athlete = None

    if parsed.chip_number:
        athlete = (
            db.query(Athlete)
            .filter(
                Athlete.race_id == race_id,
                Athlete.chip_number == parsed.chip_number,
            )
            .first()
        )

    warnings = []
    warnings.extend(parsed.warnings)
    warnings.extend(validation.warnings)

    parse_status = "ok"

    if parsed.chip_number is None:
        parse_status = "error"
        warnings.append("Skanningen mangler brikkenummer")
    elif athlete is None:
        parse_status = "unknown_chip"
        warnings.append(f"Brikkenummer {parsed.chip_number} finnes ikke på løperlisten")
    elif warnings:
        parse_status = "warning"

    if parsed.chip_number:
        (
            db.query(RawScan)
            .filter(
                RawScan.race_id == race_id,
                RawScan.chip_number == parsed.chip_number,
                RawScan.is_active.is_(True),
            )
            .update({"is_active": False})
        )

    received_at = received_at_override or server_now()

    raw_scan = RawScan(
        race_id=race_id,
        athlete_id=athlete.id if athlete else None,
        chip_number=parsed.chip_number,
        raw_text=raw_text,
        received_at=received_at,
        emit_total_time_raw=parsed.emit_total_time_raw,
        emit_total_seconds=parsed.emit_total_seconds,
        scanner_time_raw=parsed.scanner_time_raw,
        scanner_time_seconds=parsed.scanner_time_seconds,
        finish_to_scan_time_raw=parsed.finish_to_scan_time_raw,
        finish_to_scan_seconds=parsed.finish_to_scan_seconds,
        parse_status=parse_status,
        error_message="\n".join(warnings) if warnings else None,
        is_active=True,
    )

    db.add(raw_scan)
    db.flush()

    for punch in validation.punches:
        scan_punch = ScanPunch(
            raw_scan_id=raw_scan.id,
            control_id=punch.control_id,
            emit_code=punch.emit_code,
            sequence_code=punch.sequence_code,
            split_time_raw=punch.split_time_raw,
            split_seconds=punch.split_seconds,
            accumulated_time_raw=punch.accumulated_time_raw,
            accumulated_seconds=punch.accumulated_seconds,
            calculated_time_from_start_seconds=None,
            ignored=punch.ignored,
            ignore_reason=punch.ignore_reason,
        )

        db.add(scan_punch)

    athlete_name = None

    if athlete is not None:
        athlete_name = f"{athlete.first_name or ''} {athlete.last_name or ''}".strip()

    if parse_status == "ok":
        severity = "INFO"
        message = (
            f"Lagret skanning for brikke {parsed.chip_number}"
            + (f" ({athlete_name})" if athlete_name else "")
        )
    elif parse_status == "unknown_chip":
        severity = "WARNING"
        message = f"Lagret skanning med ukjent brikke {parsed.chip_number}"
    elif parse_status == "warning":
        severity = "WARNING"
        message = (
            f"Lagret skanning for brikke {parsed.chip_number}, "
            f"men med {len(warnings)} advarsel/advarsler"
        )
    else:
        severity = "ERROR"
        message = "Lagret skanning med feil"

    db.add(
        EventLog(
            race_id=race_id,
            severity=severity,
            source="scan.manual",
            message=message,
            related_scan_id=raw_scan.id,
            related_athlete_id=athlete.id if athlete else None,
        )
    )

    if athlete is not None:
        rebuild_result_for_scan(db=db, raw_scan=raw_scan)

    db.commit()
    db.refresh(raw_scan)

    return StoredScanSummary(
        raw_scan_id=raw_scan.id,
        race_id=race_id,
        chip_number=parsed.chip_number,
        athlete_id=athlete.id if athlete else None,
        athlete_name=athlete_name,
        parse_status=parse_status,
        punch_count=len(validation.punches),
        valid_punch_count=validation.valid_count,
        ignored_punch_count=validation.ignored_count,
        warning_count=len(warnings),
        warnings=warnings,
    )
