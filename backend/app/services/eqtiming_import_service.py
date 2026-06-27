import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.app.models.athlete import Athlete
from backend.app.models.event_log import EventLog
from backend.app.models.race import Race


@dataclass
class EqTimingImportSummary:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    detected_columns: dict[str, str] = field(default_factory=dict)


FIELD_ALIASES = {
    "start_number": [
        "startnummer",
        "startnr",
        "start nr",
        "start_number",
        "bib",
        "bibnumber",
        "bib number",
    ],
    "first_name": [
        "fornavn",
        "first name",
        "firstname",
        "first_name",
    ],
    "last_name": [
        "etternavn",
        "last name",
        "lastname",
        "last_name",
        "surname",
    ],
    "club": [
        "klubb",
        "club",
        "team",
        "lag",
    ],
    "gender": [
        "kjønn",
        "kjonn",
        "gender",
        "sex",
    ],
    "class_name": [
        "klasse",
        "class",
        "class name",
        "class_name",
        "øvelseklasse",
        "ovelseklasse",
    ],
    "chip_number": [
        "chip1",
        "chip 1",
        "chip",
        "brikke",
        "brikkenummer",
        "brikkenr",
        "emit",
        "emitbrikke",
        "emit brikke",
        "emitnummer",
        "emit nummer",
        "emitnr",
    ],
}


def normalize_column_name(value: str | None) -> str:
    if value is None:
        return ""

    text = value.strip().lower()

    # Norwegian characters do not always decompose nicely with unicodedata.
    text = (
        text.replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
    )

    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    # Ignore spaces, underscores, hyphens, punctuation etc.
    text = re.sub(r"[^a-z0-9]", "", text)

    return text


NORMALIZED_ALIASES = {
    field_name: {normalize_column_name(alias) for alias in aliases}
    for field_name, aliases in FIELD_ALIASES.items()
}


def decode_csv_bytes(content: bytes) -> str:
    for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue

    return content.decode("latin-1", errors="replace")


def detect_dialect(text: str) -> csv.Dialect:
    sample = text[:4096]

    try:
        return csv.Sniffer().sniff(sample, delimiters=";\t,")
    except csv.Error:
        class FallbackDialect(csv.excel):
            delimiter = ";"

        return FallbackDialect


def build_column_map(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        return {}

    normalized_to_original = {
        normalize_column_name(column): column
        for column in fieldnames
        if column is not None
    }

    column_map = {}

    for target_field, aliases in NORMALIZED_ALIASES.items():
        for alias in aliases:
            if alias in normalized_to_original:
                column_map[target_field] = normalized_to_original[alias]
                break

    return column_map


def get_value(row: dict[str, str], column_map: dict[str, str], field_name: str) -> str:
    column_name = column_map.get(field_name)

    if not column_name:
        return ""

    value = row.get(column_name)

    if value is None:
        return ""

    return str(value).strip()


def parse_start_number(value: str) -> int | None:
    value = value.strip()

    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        digits = re.sub(r"[^0-9]", "", value)

        if not digits:
            return None

        return int(digits)


def clean_chip_number(value: str) -> str | None:
    value = value.strip()

    if not value:
        return None

    # EQ Timing may sometimes export chip as "527451.0" from spreadsheet-like tools.
    if value.endswith(".0") and value[:-2].isdigit():
        value = value[:-2]

    return value


def import_eqtiming_csv_bytes(
    db: Session,
    race_id: int,
    content: bytes,
) -> EqTimingImportSummary:
    race = db.query(Race).filter(Race.id == race_id).first()

    if race is None:
        raise ValueError("Løp finnes ikke")

    text = decode_csv_bytes(content)
    dialect = detect_dialect(text)

    reader = csv.DictReader(
        io.StringIO(text),
        dialect=dialect,
    )

    column_map = build_column_map(reader.fieldnames)

    summary = EqTimingImportSummary(
        detected_columns=column_map,
    )

    required_fields = ["start_number", "first_name", "last_name"]

    missing_required = [
        field_name
        for field_name in required_fields
        if field_name not in column_map
    ]

    if missing_required:
        raise ValueError(
            "Mangler nødvendige kolonner i importfil: "
            + ", ".join(missing_required)
            + ". Fant kolonner: "
            + ", ".join(reader.fieldnames or [])
        )

    for row_index, row in enumerate(reader, start=2):
        start_number_raw = get_value(row, column_map, "start_number")
        start_number = parse_start_number(start_number_raw)

        if start_number is None:
            summary.skipped += 1
            summary.errors.append(
                f"Rad {row_index}: mangler/ugyldig startnummer"
            )
            continue

        first_name = get_value(row, column_map, "first_name")
        last_name = get_value(row, column_map, "last_name")
        club = get_value(row, column_map, "club")
        gender = get_value(row, column_map, "gender")
        class_name = get_value(row, column_map, "class_name")
        chip_number = clean_chip_number(
            get_value(row, column_map, "chip_number")
        )

        athlete = (
            db.query(Athlete)
            .filter(
                Athlete.race_id == race_id,
                Athlete.start_number == start_number,
            )
            .first()
        )

        is_new = athlete is None

        if athlete is None:
            athlete = Athlete(
                race_id=race_id,
                start_number=start_number,
            )

        athlete.first_name = first_name
        athlete.last_name = last_name
        athlete.club = club
        athlete.gender = gender
        athlete.class_name = class_name

        if chip_number:
            existing_chip_owner = (
                db.query(Athlete)
                .filter(
                    Athlete.race_id == race_id,
                    Athlete.chip_number == chip_number,
                    Athlete.start_number != start_number,
                )
                .first()
            )

            if existing_chip_owner is not None:
                summary.errors.append(
                    f"Rad {row_index}: brikke {chip_number} er allerede "
                    f"koblet til startnummer {existing_chip_owner.start_number}. "
                    f"Startnummer {start_number} ble importert uten å endre brikke."
                )
            else:
                athlete.chip_number = chip_number

        db.add(athlete)

        if is_new:
            summary.created += 1
        else:
            summary.updated += 1

    db.add(
        EventLog(
            race_id=race_id,
            severity="INFO" if not summary.errors else "WARNING",
            source="eqtiming.import",
            message=(
                f"Importerte EQ Timing CSV: "
                f"{summary.created} nye, "
                f"{summary.updated} oppdatert, "
                f"{summary.skipped} hoppet over, "
                f"{len(summary.errors)} advarsler"
            ),
        )
    )

    return summary
