from backend.app.rs232.serial_ports import list_serial_ports


def main():
    ports = list_serial_ports()

    if not ports:
        print("Fant ingen serieporter.")
        return

    print("Serieporter:")

    for port in ports:
        print(f"- {port.device}")
        print(f"  Beskrivelse: {port.description}")
        print(f"  HWID: {port.hwid}")


if __name__ == "__main__":
    main()
