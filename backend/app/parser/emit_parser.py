from dataclasses import dataclass, field
import re


_TIME_PATTERN = r"\d{1,2}:\d{2}(?::\d{2})?"

_HEADER_RE = re.compile(
    rf"^(?P<chip>\d+)\s+>>>\s+(?P<total>{_TIME_PATTERN})\s+<<<$"
)

_PUNCH_RE = re.compile(
    rf"^(?P<sequence>\d{{2}}|F)\s+"
    rf"(?P<split>{_TIME_PATTERN})\s+"
    rf"(?P<accumulated>{_TIME_PATTERN})\s+"
    rf"(?P<emit_code>\d+)$"
)

_SCANNER_RE = re.compile(
    rf"^\d+\.\d+\s+"
    rf"(?P<finish_to_scan>{_TIME_PATTERN})\s+"
    rf"(?P<scanner>{_TIME_PATTERN})$"
)


@dataclass
class ParsedPunch:
    sequence_code: str
    split_time_raw: str
    split_seconds: int
    accumulated_time_raw: str
    accumulated_seconds: int
    emit_code: str


@dataclass
class ParsedEmitScan:
    raw_text: str
    line_count: int

    chip_number: str | None = None

    emit_total_time_raw: str | None = None
    emit_total_seconds: int | None = None

    scanner_time_raw: str | None = None
    scanner_time_seconds: int | None = None

    finish_to_scan_time_raw: str | None = None
    finish_to_scan_seconds: int | None = None

    punches: list[ParsedPunch] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_time_to_seconds(value: str) -> int:
    """
    Parses time strings used by EMIT.

    Supported:
    - MM:SS
    - H:MM:SS
    - HH:MM:SS
    """

    parts = value.strip().split(":")

    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

    raise ValueError(f"Ugyldig tidsformat: {value}")


def format_seconds(seconds: int | None) -> str:
    if seconds is None:
        return ""

    hours = seconds // 3600
    rest = seconds % 3600
    minutes = rest // 60
    secs = rest % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def parse_emit_scan(raw_text: str) -> ParsedEmitScan:
    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    ]

    result = ParsedEmitScan(
        raw_text=raw_text,
        line_count=len(lines),
    )

    for line in lines:
        header_match = _HEADER_RE.match(line)

        if header_match:
            result.chip_number = header_match.group("chip")
            result.emit_total_time_raw = header_match.group("total")
            result.emit_total_seconds = parse_time_to_seconds(
                result.emit_total_time_raw
            )
            continue

        punch_match = _PUNCH_RE.match(line)

        if punch_match:
            split_time_raw = punch_match.group("split")
            accumulated_time_raw = punch_match.group("accumulated")

            result.punches.append(
                ParsedPunch(
                    sequence_code=punch_match.group("sequence"),
                    split_time_raw=split_time_raw,
                    split_seconds=parse_time_to_seconds(split_time_raw),
                    accumulated_time_raw=accumulated_time_raw,
                    accumulated_seconds=parse_time_to_seconds(accumulated_time_raw),
                    emit_code=punch_match.group("emit_code"),
                )
            )
            continue

        scanner_match = _SCANNER_RE.match(line)

        if scanner_match:
            result.finish_to_scan_time_raw = scanner_match.group("finish_to_scan")
            result.finish_to_scan_seconds = parse_time_to_seconds(
                result.finish_to_scan_time_raw
            )

            result.scanner_time_raw = scanner_match.group("scanner")
            result.scanner_time_seconds = parse_time_to_seconds(
                result.scanner_time_raw
            )
            continue

    if result.chip_number is None:
        result.warnings.append("Fant ikke brikkenummer")

    if result.emit_total_seconds is None:
        result.warnings.append("Fant ikke EMIT-total")

    if result.scanner_time_seconds is None:
        result.warnings.append("Fant ikke skannertid")

    if result.finish_to_scan_seconds is None:
        result.warnings.append("Fant ikke tid fra mål til skanner")

    if not result.punches:
        result.warnings.append("Fant ingen stemplinger")

    return result
