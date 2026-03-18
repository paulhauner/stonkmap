from pathlib import Path
from decimal import Decimal

from stonkmap.indexes.parsers import (
    parse_betashares_csv,
    parse_blackrock_spreadsheet_xml,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_betashares_csv_extracts_holdings_metadata() -> None:
    parsed = parse_betashares_csv((FIXTURES / "betashares_sample.csv").read_text())

    assert parsed.as_of.date().isoformat() == "2026-03-17"
    assert len(parsed.constituents) == 3
    assert parsed.constituents[0].ticker == "CBA"
    assert parsed.constituents[0].exchange == "ASX"
    assert parsed.constituents[0].weight_percentage == Decimal("9.12")


def test_parse_blackrock_xml_extracts_holdings_metadata() -> None:
    parsed = parse_blackrock_spreadsheet_xml(
        (FIXTURES / "blackrock_sample.xml").read_text()
    )

    assert parsed.as_of.date().isoformat() == "2026-03-16"
    assert len(parsed.constituents) == 3
    assert parsed.constituents[1].ticker == "BHP"
    assert parsed.constituents[1].exchange == "ASX"
    assert parsed.constituents[1].weight_percentage == Decimal("8.80")
