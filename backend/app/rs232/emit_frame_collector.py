from dataclasses import dataclass, field


@dataclass
class EmitFrameCollector:
    """
    Collects text lines from an EMIT RS-232 scanner.

    Startup noise from the scanner is ignored.

    A real EMIT scan starts when we see a line containing:

        EMIT timing system

    A scan is complete when we see a footer line starting with:

        Emit EPT

    Then the full raw EMIT text is returned.
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
        - None while no complete scan is available
        - raw EMIT text when one full scan is complete
        """

        cleaned_line = line.rstrip("\r\n")
        stripped = cleaned_line.strip()

        # Ignore everything until a real EMIT printout starts.
        if not self.is_collecting:
            if "EMIT timing system" not in stripped:
                return None

            self.is_collecting = True
            self.buffer = []

        self.buffer.append(cleaned_line)

        if stripped.startswith("Emit EPT"):
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
