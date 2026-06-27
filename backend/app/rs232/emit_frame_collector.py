from dataclasses import dataclass, field


@dataclass
class EmitFrameCollector:
    """
    Collects text lines from an EMIT RS-232 scanner.

    The scanner sends one result as multiple text lines.
    This collector buffers lines until it sees the EMIT footer line,
    for example:

        Emit EPT V6.00

    Then it returns the complete raw EMIT text.
    """

    buffer: list[str] = field(default_factory=list)
    is_collecting: bool = False

    def reset(self) -> None:
        self.buffer.clear()
        self.is_collecting = False

    def add_line(self, line: str) -> str | None:
        """
        Add one line from the serial port.

        Returns:
        - None while the scan is incomplete
        - raw EMIT text when one full scan is complete
        """

        cleaned_line = line.rstrip("\r\n")

        # Ignore empty lines before a scan starts.
        if not self.is_collecting and cleaned_line.strip() == "":
            return None

        if not self.is_collecting:
            self.is_collecting = True
            self.buffer = []

        self.buffer.append(cleaned_line)

        if cleaned_line.strip().startswith("Emit EPT"):
            raw_text = "\n".join(self.buffer)
            self.reset()
            return raw_text

        return None


def decode_serial_bytes(data: bytes) -> str:
    """
    Decode one line from RS-232.

    EMIT text is simple ASCII-like text, but errors are ignored
    so a bad byte does not crash the reader.
    """

    return data.decode("utf-8", errors="ignore")
