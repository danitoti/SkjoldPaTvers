from backend.app.parser.emit_parser import parse_emit_scan
from backend.app.rs232.serial_reader import RS232EmitReader


class FakeSerial:
    def __init__(self, lines: list[str]):
        self.lines = [line.encode("utf-8") for line in lines]
        self.index = 0
        self.closed = False

    def readline(self):
        if self.index >= len(self.lines):
            return b""

        value = self.lines[self.index]
        self.index += 1
        return value

    def close(self):
        self.closed = True


LINES = [
    "Startup text\r\n",
    "Noise before scan\r\n",
    "   EMIT timing system\r\n",
    "  14:54:26  06.04.2025\r\n",
    "527451  >>>  1:54:03 <<<\r\n",
    "01    18:00    18:00 100\r\n",
    "02    08:02    26:02 111\r\n",
    "03    09:13    35:15 113\r\n",
    "04    10:46    46:01 117\r\n",
    "05    27:56  1:13:57 119\r\n",
    "06    18:05  1:32:02 120\r\n",
    "07    07:46  1:39:48 121\r\n",
    "F     14:15  1:54:03 150\r\n",
    "\r\n",
    "2.10  00:11  1:54:14\r\n",
    "Emit EPT V6.00      \r\n",
]


def main():
    fake_serial = FakeSerial(LINES)

    reader = RS232EmitReader(
        port="FAKE",
        serial_connection=fake_serial,
    )

    frame = reader.read_one_frame()

    assert frame is not None
    assert "Startup text" not in frame
    assert "Noise before scan" not in frame
    assert "EMIT timing system" in frame
    assert "Emit EPT V6.00" in frame

    parsed = parse_emit_scan(frame)

    assert parsed.chip_number == "527451"
    assert parsed.emit_total_time_raw == "1:54:03"
    assert parsed.finish_to_scan_time_raw == "00:11"
    assert len(parsed.punches) == 8

    print("OK - RS232-leser fungerer med simulert serieport")


if __name__ == "__main__":
    main()
