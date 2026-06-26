from dataclasses import dataclass
from typing import Any

from backend.app.parser.emit_parser import ParsedEmitScan


@dataclass
class ValidatedPunch:
    sequence_code: str
    emit_code: str | None

    split_time_raw: str | None
    split_seconds: int | None

    accumulated_time_raw: str | None
    accumulated_seconds: int | None

    control_id: int | None
    control_name: str | None
    control_sort_order: int | None

    ignored: bool
    ignore_reason: str | None


@dataclass
class EmitValidationResult:
    punches: list[ValidatedPunch]
    warnings: list[str]

    valid_count: int
    ignored_count: int
    unknown_control_count: int
    duplicate_count: int


def validate_emit_scan_against_controls(
    parsed: ParsedEmitScan,
    controls: list[Any],
) -> EmitValidationResult:
    controls_by_emit_code = {}

    for control in controls:
        if control.emit_code is None:
            continue

        emit_code = str(control.emit_code).strip()

        if emit_code:
            controls_by_emit_code[emit_code] = control

    seen_emit_codes: set[str] = set()
    punches: list[ValidatedPunch] = []
    warnings: list[str] = []

    unknown_control_count = 0
    duplicate_count = 0

    for punch in parsed.punches:
        control = controls_by_emit_code.get(punch.emit_code)

        ignored = False
        ignore_reason = None

        if control is None:
            ignored = True
            ignore_reason = "unknown_control"
            unknown_control_count += 1
            warnings.append(
                f"Ukjent EMIT-kode {punch.emit_code} funnet og ignorert."
            )
        elif punch.emit_code in seen_emit_codes:
            ignored = True
            ignore_reason = "duplicate"
            duplicate_count += 1
            warnings.append(
                f"Duplikatstempling på EMIT-kode {punch.emit_code} ignorert."
            )
        else:
            seen_emit_codes.add(punch.emit_code)

        punches.append(
            ValidatedPunch(
                sequence_code=punch.sequence_code,
                emit_code=punch.emit_code,
                split_time_raw=punch.split_time_raw,
                split_seconds=punch.split_seconds,
                accumulated_time_raw=punch.accumulated_time_raw,
                accumulated_seconds=punch.accumulated_seconds,
                control_id=control.id if control is not None else None,
                control_name=control.name if control is not None else None,
                control_sort_order=control.sort_order if control is not None else None,
                ignored=ignored,
                ignore_reason=ignore_reason,
            )
        )

    ignored_count = sum(1 for punch in punches if punch.ignored)
    valid_count = len(punches) - ignored_count

    return EmitValidationResult(
        punches=punches,
        warnings=warnings,
        valid_count=valid_count,
        ignored_count=ignored_count,
        unknown_control_count=unknown_control_count,
        duplicate_count=duplicate_count,
    )
