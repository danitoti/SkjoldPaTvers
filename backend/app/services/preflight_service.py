from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.app.models.athlete import Athlete
from backend.app.models.control import Control
from backend.app.models.race import Race
from backend.app.models.raw_scan import RawScan
from backend.app.models.result import Result


@dataclass
class PreflightItem:
    title: str
    status: str
    message: str
    details: list[str] = field(default_factory=list)


@dataclass
class PreflightReport:
    race: Race | None
    items: list[PreflightItem]
    ok_count: int
    warning_count: int
    error_count: int

    @property
    def is_ready(self) -> bool:
        return self.error_count == 0


def _add(
    items: list[PreflightItem],
    title: str,
    status: str,
    message: str,
    details: list[str] | None = None,
) -> None:
    items.append(
        PreflightItem(
            title=title,
            status=status,
            message=message,
            details=details or [],
        )
    )


def _format_control(control: Control) -> str:
    return f"{control.sort_order}. {control.name} ({control.emit_code or 'mangler kode'})"


def build_preflight_report(
    db: Session,
    race_id: int | None,
) -> PreflightReport:
    items: list[PreflightItem] = []

    race = None

    if race_id is not None:
        race = db.query(Race).filter(Race.id == race_id).first()
    else:
        race = (
            db.query(Race)
            .order_by(Race.created_at.desc())
            .first()
        )

    if race is None:
        _add(
            items,
            "Løp",
            "error",
            "Ingen løp er opprettet.",
            ["Opprett et løp i admin før du går videre."],
        )

        return _finish_report(race, items)

    _add(
        items,
        "Løp",
        "ok",
        f"Valgt løp: {race.name}",
    )

    if race.start_time is None:
        _add(
            items,
            "Fellesstart",
            "error",
            "Fellesstart er ikke satt.",
            ["Sett starttid før løpet. Resultatberegning krever fellesstart."],
        )
    else:
        _add(
            items,
            "Fellesstart",
            "ok",
            f"Starttid er satt til {race.start_time}.",
        )

    controls = (
        db.query(Control)
        .filter(Control.race_id == race.id)
        .order_by(Control.sort_order.asc())
        .all()
    )

    if not controls:
        _add(
            items,
            "Poster/topper",
            "error",
            "Ingen poster er lagt inn.",
            ["Legg inn alle topper og målpost med riktig EMIT-kode."],
        )
    else:
        _add(
            items,
            "Poster/topper",
            "ok",
            f"{len(controls)} poster er lagt inn.",
            [_format_control(control) for control in controls],
        )

        controls_without_code = [
            control
            for control in controls
            if not control.emit_code
        ]

        if controls_without_code:
            _add(
                items,
                "EMIT-koder på poster",
                "error",
                f"{len(controls_without_code)} post(er) mangler EMIT-kode.",
                [_format_control(control) for control in controls_without_code],
            )
        else:
            _add(
                items,
                "EMIT-koder på poster",
                "ok",
                "Alle poster har EMIT-kode.",
            )

        control_code_counter = Counter(
            str(control.emit_code).strip()
            for control in controls
            if control.emit_code
        )

        duplicate_control_codes = [
            code
            for code, count in control_code_counter.items()
            if count > 1
        ]

        if duplicate_control_codes:
            details = []

            for code in duplicate_control_codes:
                matched = [
                    _format_control(control)
                    for control in controls
                    if str(control.emit_code).strip() == code
                ]
                details.append(f"EMIT-kode {code}: " + ", ".join(matched))

            _add(
                items,
                "Dupliserte postkoder",
                "error",
                "Samme EMIT-kode er brukt på flere poster.",
                details,
            )
        else:
            _add(
                items,
                "Dupliserte postkoder",
                "ok",
                "Ingen dupliserte EMIT-koder på poster.",
            )

    athletes = (
        db.query(Athlete)
        .filter(Athlete.race_id == race.id)
        .order_by(Athlete.start_number.asc())
        .all()
    )

    if not athletes:
        _add(
            items,
            "Løpere",
            "error",
            "Ingen løpere er importert.",
            ["Importer deltakerfil fra EQ Timing."],
        )
    else:
        _add(
            items,
            "Løpere",
            "ok",
            f"{len(athletes)} løpere er importert.",
        )

        start_number_counter = Counter(
            athlete.start_number
            for athlete in athletes
            if athlete.start_number is not None
        )

        duplicate_start_numbers = [
            start_number
            for start_number, count in start_number_counter.items()
            if count > 1
        ]

        if duplicate_start_numbers:
            _add(
                items,
                "Startnummer",
                "error",
                "Dupliserte startnummer funnet.",
                [str(value) for value in duplicate_start_numbers],
            )
        else:
            _add(
                items,
                "Startnummer",
                "ok",
                "Ingen dupliserte startnummer.",
            )

        athletes_without_chip = [
            athlete
            for athlete in athletes
            if not athlete.chip_number
        ]

        if athletes_without_chip:
            status = "warning"

            if len(athletes_without_chip) == len(athletes):
                message = "Ingen løpere har brikkenummer."
            else:
                message = f"{len(athletes_without_chip)} løper(e) mangler brikkenummer."

            _add(
                items,
                "Brikkenummer",
                status,
                message,
                [
                    f"{athlete.start_number}: {athlete.first_name or ''} {athlete.last_name or ''}".strip()
                    for athlete in athletes_without_chip[:20]
                ],
            )
        else:
            _add(
                items,
                "Brikkenummer",
                "ok",
                "Alle løpere har brikkenummer.",
            )

        chip_counter = Counter(
            str(athlete.chip_number).strip()
            for athlete in athletes
            if athlete.chip_number
        )

        duplicate_chips = [
            chip
            for chip, count in chip_counter.items()
            if count > 1
        ]

        if duplicate_chips:
            details = []

            for chip in duplicate_chips:
                owners = [
                    f"{athlete.start_number}: {athlete.first_name or ''} {athlete.last_name or ''}".strip()
                    for athlete in athletes
                    if athlete.chip_number and str(athlete.chip_number).strip() == chip
                ]
                details.append(f"Brikke {chip}: " + ", ".join(owners))

            _add(
                items,
                "Dupliserte brikker",
                "error",
                "Samme brikke er koblet til flere løpere.",
                details,
            )
        else:
            _add(
                items,
                "Dupliserte brikker",
                "ok",
                "Ingen dupliserte brikkenummer.",
            )

    active_scans = (
        db.query(RawScan)
        .filter(
            RawScan.race_id == race.id,
            RawScan.is_active.is_(True),
        )
        .all()
    )

    unknown_chip_count = sum(
        1
        for scan in active_scans
        if scan.parse_status == "unknown_chip"
    )

    warning_scan_count = sum(
        1
        for scan in active_scans
        if scan.parse_status not in ("ok", "unknown_chip")
    )

    if active_scans:
        _add(
            items,
            "Skanninger",
            "ok",
            f"{len(active_scans)} aktive skanninger er lagret.",
        )
    else:
        _add(
            items,
            "Skanninger",
            "warning",
            "Ingen skanninger er lagret ennå.",
            ["Dette er normalt før løpet starter."],
        )

    if unknown_chip_count:
        _add(
            items,
            "Ukjente brikker",
            "warning",
            f"{unknown_chip_count} aktiv(e) skanning(er) har ukjent brikke.",
            ["Gå til Ukjente brikker og koble dem til startnummer."],
        )
    else:
        _add(
            items,
            "Ukjente brikker",
            "ok",
            "Ingen aktive ukjente brikker.",
        )

    if warning_scan_count:
        _add(
            items,
            "Skanningsadvarsler",
            "warning",
            f"{warning_scan_count} aktiv(e) skanning(er) har advarsler.",
        )
    else:
        _add(
            items,
            "Skanningsadvarsler",
            "ok",
            "Ingen aktive skanningsadvarsler.",
        )

    result_count = (
        db.query(Result)
        .filter(
            Result.race_id == race.id,
            Result.total_seconds.isnot(None),
        )
        .count()
    )

    if result_count:
        _add(
            items,
            "Resultater",
            "ok",
            f"{result_count} løper(e) har resultat.",
        )
    else:
        _add(
            items,
            "Resultater",
            "warning",
            "Ingen resultater ennå.",
            ["Dette er normalt før første løper er i mål."],
        )

    try:
        from backend.app.models.rs232_settings import Rs232Settings
        from backend.app.rs232.reader_worker import get_rs232_reader_status

        settings = (
            db.query(Rs232Settings)
            .filter(Rs232Settings.id == 1)
            .first()
        )

        reader_status = get_rs232_reader_status()

        if settings is None:
            _add(
                items,
                "RS-232-oppsett",
                "warning",
                "RS-232-oppsett finnes ikke.",
            )
        else:
            rs232_details = [
                f"Løp-ID: {settings.selected_race_id or '-'}",
                f"Port: {settings.port or '-'}",
                f"Baudrate: {settings.baudrate}",
            ]

            if settings.selected_race_id != race.id:
                _add(
                    items,
                    "RS-232-oppsett",
                    "warning",
                    "RS-232 er ikke knyttet til valgt løp.",
                    rs232_details,
                )
            elif not settings.port:
                _add(
                    items,
                    "RS-232-oppsett",
                    "warning",
                    "RS-232 mangler valgt port.",
                    rs232_details,
                )
            else:
                _add(
                    items,
                    "RS-232-oppsett",
                    "ok",
                    "RS-232-oppsett er satt.",
                    rs232_details,
                )

        if reader_status.is_running:
            _add(
                items,
                "RS-232-leser",
                "ok",
                "Kontinuerlig RS-232-lesing kjører.",
                [
                    f"Port: {reader_status.port or '-'}",
                    f"Mottatt: {reader_status.frames_received}",
                    f"Lagret: {reader_status.scans_saved}",
                    f"Siste melding: {reader_status.last_message or '-'}",
                ],
            )
        else:
            _add(
                items,
                "RS-232-leser",
                "warning",
                "Kontinuerlig RS-232-lesing kjører ikke.",
                ["Dette er normalt før løpet, men bør startes når skanneren er koblet til."],
            )

    except Exception as exc:
        _add(
            items,
            "RS-232",
            "warning",
            f"Klarte ikke å lese RS-232-status: {exc}",
        )

    return _finish_report(race, items)


def _finish_report(
    race: Race | None,
    items: list[PreflightItem],
) -> PreflightReport:
    ok_count = sum(1 for item in items if item.status == "ok")
    warning_count = sum(1 for item in items if item.status == "warning")
    error_count = sum(1 for item in items if item.status == "error")

    return PreflightReport(
        race=race,
        items=items,
        ok_count=ok_count,
        warning_count=warning_count,
        error_count=error_count,
    )
