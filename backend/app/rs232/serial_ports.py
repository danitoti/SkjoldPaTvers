from dataclasses import dataclass

from serial.tools import list_ports


@dataclass
class SerialPortInfo:
    device: str
    description: str
    hwid: str


def list_serial_ports() -> list[SerialPortInfo]:
    ports = []

    for port in list_ports.comports():
        ports.append(
            SerialPortInfo(
                device=port.device,
                description=port.description,
                hwid=port.hwid,
            )
        )

    return ports
