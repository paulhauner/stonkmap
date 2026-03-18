from pathlib import Path
from decimal import Decimal

from stonkmap.indexes.parsers import (
    parse_betashares_csv,
    parse_blackrock_spreadsheet_xml,
    parse_vaneck_fund_dataset_json,
    parse_vanguard_personal_json,
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


def test_parse_vanguard_json_extracts_holdings_metadata() -> None:
    parsed = parse_vanguard_personal_json(
        (FIXTURES / "vanguard_holdings_sample.json").read_text()
    )

    assert parsed.as_of.date().isoformat() == "2026-02-28"
    assert len(parsed.constituents) == 3
    assert parsed.constituents[0].ticker == "NVDA"
    assert parsed.constituents[0].exchange is None
    assert parsed.constituents[0].weight_percentage == Decimal("6.0963")


def test_parse_vaneck_json_extracts_holdings_metadata() -> None:
    parsed = parse_vaneck_fund_dataset_json(
        (FIXTURES / "vaneck_sample.json").read_text()
    )

    assert parsed.as_of.date().isoformat() == "2026-03-17"
    assert len(parsed.constituents) == 3
    assert parsed.constituents[0].ticker == "ENLT"
    assert parsed.constituents[0].exchange is None
    assert parsed.constituents[0].weight_percentage == Decimal("6.02")
