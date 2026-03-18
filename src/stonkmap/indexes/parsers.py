from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from typing import Callable

from pydantic import BaseModel, ConfigDict

from ..market_symbols import exchange_from_source_code
from ..models import Constituent

SPREADSHEETML_NAMESPACE = "urn:schemas-microsoft-com:office:spreadsheet"
SPREADSHEETML_NS = {"ss": SPREADSHEETML_NAMESPACE}


class ParsedHoldings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    constituents: list[Constituent]


ParserFn = Callable[[str], ParsedHoldings]


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    stripped = value.strip().replace(",", "")
    if not stripped:
        return None
    return Decimal(stripped)


def _parse_date(value: str) -> datetime:
    stripped = value.strip()
    for pattern in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(stripped, pattern)
        except ValueError:
            continue
    raise ValueError(f"unsupported date format: {value}")


def _split_source_ticker(raw_ticker: str) -> tuple[str, str | None]:
    parts = raw_ticker.strip().split()
    if not parts:
        return "", None
    ticker = parts[0].strip().upper()
    exchange_code = parts[1].strip().upper() if len(parts) > 1 else None
    return ticker, exchange_code


def parse_betashares_csv(content: str) -> ParsedHoldings:
    reader = csv.reader(io.StringIO(content))
    headers: list[str] | None = None
    as_of: datetime | None = None
    constituents: list[Constituent] = []

    for raw_row in reader:
        row = [cell.strip() for cell in raw_row]
        if not any(row):
            continue
        if len(row) >= 2 and row[0] == "Date":
            as_of = _parse_date(row[1])
            continue
        if row[0] == "Ticker":
            headers = row
            continue
        if headers is None:
            continue
        data = {headers[index]: row[index] if index < len(row) else "" for index in range(len(headers))}
        raw_ticker = data.get("Ticker", "").strip()
        if not raw_ticker:
            continue
        ticker, source_exchange_code = _split_source_ticker(raw_ticker)
        constituents.append(
            Constituent(
                ticker=ticker,
                exchange=exchange_from_source_code(source_exchange_code),
                source_ticker=raw_ticker,
                source_exchange_code=source_exchange_code,
                name=data.get("Name", "").strip() or ticker,
                asset_class=data.get("Asset Class", "").strip() or None,
                sector=data.get("Sector", "").strip() or None,
                country=data.get("Country", "").strip() or None,
                currency=data.get("Currency", "").strip() or None,
                weight_percentage=_parse_decimal(data.get("Weight (%)")) or Decimal("0"),
                units_held=_parse_decimal(data.get("Shares/Units (#)")),
                market_value=_parse_decimal(data.get("Market Value (AUD)")),
            )
        )

    if as_of is None:
        raise ValueError("Betashares holdings file is missing a Date row")
    return ParsedHoldings(as_of=as_of, constituents=constituents)


def _read_spreadsheetml_row(row: ET.Element) -> list[str]:
    values: list[str] = []
    current_position = 1
    for cell in row.findall("ss:Cell", SPREADSHEETML_NS):
        indexed_at = cell.attrib.get(f"{{{SPREADSHEETML_NAMESPACE}}}Index")
        if indexed_at is not None:
            target = int(indexed_at)
            while current_position < target:
                values.append("")
                current_position += 1
        data = cell.find("ss:Data", SPREADSHEETML_NS)
        values.append((data.text or "").strip() if data is not None else "")
        current_position += 1
    return values


def parse_blackrock_spreadsheet_xml(content: str) -> ParsedHoldings:
    sanitized = re.sub(r"&(?!#?\w+;)", "&amp;", content.lstrip("\ufeff"))
    root = ET.fromstring(sanitized)
    worksheet = None
    for item in root.findall("ss:Worksheet", SPREADSHEETML_NS):
        if item.attrib.get(f"{{{SPREADSHEETML_NAMESPACE}}}Name") == "Holdings":
            worksheet = item
            break
    if worksheet is None:
        raise ValueError("BlackRock holdings workbook does not include a Holdings sheet")

    table = worksheet.find("ss:Table", SPREADSHEETML_NS)
    if table is None:
        raise ValueError("BlackRock holdings workbook is missing a Holdings table")

    rows = [_read_spreadsheetml_row(row) for row in table.findall("ss:Row", SPREADSHEETML_NS)]
    as_of: datetime | None = None
    headers: list[str] | None = None
    constituents: list[Constituent] = []

    for row in rows:
        if not any(row):
            if headers is not None and constituents:
                break
            continue
        if row[0] == "Fund Holdings as of" and len(row) > 1:
            as_of = _parse_date(row[1])
            continue
        if row[0] == "Ticker" and len(row) > 1 and row[1] == "Name":
            headers = row
            continue
        if headers is None:
            continue
        data = {headers[index]: row[index] if index < len(row) else "" for index in range(len(headers))}
        raw_ticker = data.get("Ticker", "").strip()
        if not raw_ticker:
            continue
        ticker, source_exchange_code = _split_source_ticker(raw_ticker)
        constituents.append(
            Constituent(
                ticker=ticker,
                exchange=exchange_from_source_code(source_exchange_code),
                source_ticker=raw_ticker,
                source_exchange_code=source_exchange_code,
                name=data.get("Name", "").strip() or ticker,
                asset_class=data.get("Asset Class", "").strip() or None,
                sector=data.get("Sector", "").strip() or None,
                country=data.get("Location", "").strip() or None,
                currency=data.get("Currency", "").strip() or None,
                weight_percentage=_parse_decimal(data.get("Weight (%)")) or Decimal("0"),
                units_held=_parse_decimal(data.get("Shares")),
                market_value=_parse_decimal(data.get("Market Value")),
            )
        )

    if as_of is None:
        raise ValueError("BlackRock holdings file is missing the Fund Holdings as of row")
    return ParsedHoldings(as_of=as_of, constituents=constituents)


PARSER_REGISTRY: dict[str, ParserFn] = {
    "betashares_csv": parse_betashares_csv,
    "blackrock_spreadsheet_xml": parse_blackrock_spreadsheet_xml,
}
