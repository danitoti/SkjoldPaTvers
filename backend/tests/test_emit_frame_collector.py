from backend.app.rs232.emit_frame_collector import EmitFrameCollector
from backend.app.parser.emit_parser import parse_emit_scan


LINES = [
    "",
    "",
    "   EMIT timing system",
    "  14:54:26  06.04.2025",
    "527451  >>>  1:54:03 <<<",
    "01    18:00    18:00 100",
    "02    08:02    26:02 111",
    "03    09:13    35:15 113",
    "04    10:46    46:01 117",
    "05    27:56  1:13:57 119",
    "06    18:05  1:32:02 120",
    "07    07:46  1:39:48 121",
    "F     14:15  1:54:03 150",
    "",
    "2.10  00:11  1:54:14",
    "Emit EPT V6.00      ",
    "",
]


def main():
    collector = EmitFrameCollector()

    completed = None

    for line in LINES:
        result = collector.add_line(line)

        if result is not None:
            completed = result

    assert completed is not None

    parsed = parse_emit_scan(completed)

    assert parsed.chip_number == "527451"
    assert parsed.emit_total_time_raw == "1:54:03"
    assert parsed.finish_to_scan_time_raw == "00:11"
    assert parsed.scanner_time_raw == "1:54:14"
    assert len(parsed.punches) == 8

    print("OK - EMIT frame collector fungerer")


if __name__ == "__main__":
    main()
