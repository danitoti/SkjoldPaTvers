from backend.app.services.eqtiming_import_service import (
    build_column_map,
    normalize_column_name,
)


def main():
    assert normalize_column_name("Kjønn") == "kjonn"
    assert normalize_column_name("Chip 1") == "chip1"
    assert normalize_column_name("Start nummer") == "startnummer"
    assert normalize_column_name(" EMIT-brikke ") == "emitbrikke"

    columns = [
        "Klasse",
        "Chip 1",
        "Etternavn",
        "Fornavn",
        "Startnummer",
        "Kjønn",
        "Klubb",
        "Et nytt felt EQ Timing fant på",
    ]

    column_map = build_column_map(columns)

    assert column_map["start_number"] == "Startnummer"
    assert column_map["first_name"] == "Fornavn"
    assert column_map["last_name"] == "Etternavn"
    assert column_map["club"] == "Klubb"
    assert column_map["gender"] == "Kjønn"
    assert column_map["class_name"] == "Klasse"
    assert column_map["chip_number"] == "Chip 1"

    print("OK - EQ Timing import tåler endret kolonnerekkefølge og ekstra kolonner")


if __name__ == "__main__":
    main()
