from dataclasses import dataclass
from datetime import datetime
import threading

from backend.app.database.session import SessionLocal
from backend.app.rs232.serial_reader import RS232EmitReader
from backend.app.services.scan_service import store_emit_scan


@dataclass
class ReaderStatus:
    is_running: bool = False
    port: str | None = None
    baudrate: int | None = None
    race_id: int | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    last_frame_at: datetime | None = None
    last_saved_at: datetime | None = None
    last_message: str | None = None
    last_error: str | None = None
    frames_received: int = 0
    scans_saved: int = 0
    save_errors: int = 0


_lock = threading.Lock()
_status = ReaderStatus()
_worker_thread: threading.Thread | None = None
_reader: RS232EmitReader | None = None


def get_rs232_reader_status() -> ReaderStatus:
    with _lock:
        return ReaderStatus(
            is_running=_status.is_running,
            port=_status.port,
            baudrate=_status.baudrate,
            race_id=_status.race_id,
            started_at=_status.started_at,
            stopped_at=_status.stopped_at,
            last_frame_at=_status.last_frame_at,
            last_saved_at=_status.last_saved_at,
            last_message=_status.last_message,
            last_error=_status.last_error,
            frames_received=_status.frames_received,
            scans_saved=_status.scans_saved,
            save_errors=_status.save_errors,
        )


def _set_status(**kwargs) -> None:
    with _lock:
        for key, value in kwargs.items():
            setattr(_status, key, value)


def _worker_main(
    port: str,
    baudrate: int,
    timeout: float,
    race_id: int,
) -> None:
    global _reader

    reader = RS232EmitReader(
        port=port,
        baudrate=baudrate,
        timeout=timeout,
    )

    with _lock:
        _reader = reader

    def on_frame(raw_text: str) -> None:
        now = datetime.now()

        with _lock:
            _status.frames_received += 1
            _status.last_frame_at = now
            _status.last_message = "Mottok komplett EMIT-skanning fra RS-232"
            _status.last_error = None

        db = SessionLocal()

        try:
            summary = store_emit_scan(
                db=db,
                race_id=race_id,
                raw_text=raw_text,
            )

            db.commit()

            with _lock:
                _status.scans_saved += 1
                _status.last_saved_at = datetime.now()

                if summary.athlete_name:
                    _status.last_message = (
                        f"Lagret skanning for brikke "
                        f"{summary.chip_number} ({summary.athlete_name})"
                    )
                else:
                    _status.last_message = (
                        f"Lagret skanning for brikke "
                        f"{summary.chip_number}. Brikken er ikke koblet til løper."
                    )

                _status.last_error = None

        except Exception as exc:
            db.rollback()

            with _lock:
                _status.save_errors += 1
                _status.last_error = str(exc)
                _status.last_message = "Mottok skanning, men klarte ikke å lagre den"

        finally:
            db.close()

    try:
        reader.read_forever(on_frame)

    except Exception as exc:
        _set_status(
            is_running=False,
            stopped_at=datetime.now(),
            last_error=str(exc),
            last_message="RS-232-lesing stoppet på grunn av feil",
        )

    finally:
        with _lock:
            _status.is_running = False
            _status.stopped_at = datetime.now()
            _reader = None


def start_rs232_reader(
    port: str,
    baudrate: int,
    timeout: float,
    race_id: int,
) -> tuple[bool, str]:
    global _worker_thread

    with _lock:
        if _status.is_running:
            return False, "RS-232-lesing kjører allerede"

        _status.is_running = True
        _status.port = port
        _status.baudrate = baudrate
        _status.race_id = race_id
        _status.started_at = datetime.now()
        _status.stopped_at = None
        _status.last_frame_at = None
        _status.last_saved_at = None
        _status.last_message = "Starter RS-232-lesing"
        _status.last_error = None
        _status.frames_received = 0
        _status.scans_saved = 0
        _status.save_errors = 0

    _worker_thread = threading.Thread(
        target=_worker_main,
        kwargs={
            "port": port,
            "baudrate": baudrate,
            "timeout": timeout,
            "race_id": race_id,
        },
        daemon=True,
    )

    _worker_thread.start()

    return True, "RS-232-lesing startet"


def stop_rs232_reader() -> tuple[bool, str]:
    global _reader

    with _lock:
        if not _status.is_running:
            return False, "RS-232-lesing kjører ikke"

        reader = _reader
        _status.last_message = "Stopper RS-232-lesing"

    if reader is not None:
        reader.stop()

    _set_status(
        is_running=False,
        stopped_at=datetime.now(),
        last_message="RS-232-lesing stoppet",
    )

    return True, "RS-232-lesing stoppet"
