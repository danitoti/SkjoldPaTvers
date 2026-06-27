from collections.abc import Callable

import serial

from backend.app.rs232.emit_frame_collector import (
    EmitFrameCollector,
    decode_serial_bytes,
)


class RS232EmitReader:
    """
    Reads EMIT scans from a serial port.

    This class does not know anything about database, races or results.
    It only does this:

    serial bytes
    -> decoded lines
    -> EmitFrameCollector
    -> complete raw EMIT scan text

    The complete scan is then passed to a callback.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
        serial_connection=None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = serial_connection
        self.collector = EmitFrameCollector()
        self.is_running = False

    def _open_serial(self):
        if self.serial_connection is not None:
            return self.serial_connection

        return serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )

    def read_one_frame(self) -> str | None:
        """
        Reads until one complete EMIT frame is found.

        Returns:
        - raw EMIT text if a complete scan is read
        - None if no complete frame is available before the stream ends
        """

        connection = self._open_serial()

        close_when_done = self.serial_connection is None

        try:
            while True:
                data = connection.readline()

                if not data:
                    return None

                line = decode_serial_bytes(data)
                frame = self.collector.add_line(line)

                if frame is not None:
                    return frame
        finally:
            if close_when_done:
                connection.close()

    def read_forever(
        self,
        on_frame: Callable[[str], None],
    ) -> None:
        """
        Continuously reads from the serial port.

        For each complete EMIT scan, on_frame(raw_text) is called.
        """

        connection = self._open_serial()
        close_when_done = self.serial_connection is None

        self.is_running = True

        try:
            while self.is_running:
                data = connection.readline()

                if not data:
                    continue

                line = decode_serial_bytes(data)
                frame = self.collector.add_line(line)

                if frame is not None:
                    on_frame(frame)
        finally:
            self.is_running = False

            if close_when_done:
                connection.close()

    def stop(self) -> None:
        self.is_running = False
