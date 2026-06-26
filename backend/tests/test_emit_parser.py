from backend.app.parser.emit_parser import format_seconds, parse_emit_scan


SAMPLE = """

   EMIT timing system
  14:54:26  06.04.2025
527451  >>>  1:54:03 <<<
01    18:00    18:00 100
02    08:02    26:02 111
03    09:13    35:15 113
04    10:46    46:01 117
05    27:56  1:13:57 119
06    18:05  1:32:02 120
07    07:46  1:39:48 121
F     14:15  1:54:03 150

2.10  00:11  1:54:14
Emit EPT V6.00      

"""


def main():
    parsed = parse_emit_scan(SAMPLE)

    assert parsed.line_count == 13
    assert parsed.chip_number == "527451"

    assert parsed.emit_total_seconds == 6843
    assert format_seconds(parsed.emit_total_seconds) == "1:54:03"

    assert parsed.finish_to_scan_seconds == 11
    assert parsed.scanner_time_seconds == 6854

    assert len(parsed.punches) == 8

    assert parsed.punches[0].sequence_code == "01"
    assert parsed.punches[0].emit_code == "100"
    assert parsed.punches[0].split_seconds == 1080
    assert parsed.punches[0].accumulated_seconds == 1080

    assert parsed.punches[-1].sequence_code == "F"
    assert parsed.punches[-1].emit_code == "150"
    assert parsed.punches[-1].accumulated_seconds == 6843

    assert parsed.warnings == []

    print("OK - EMIT-parser fungerer")


if __name__ == "__main__":
    main()
