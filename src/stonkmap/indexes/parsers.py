from __future__ import annotations

import csv
import io
import json
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


def _parse_decimal(value: object | None) -> Decimal | None:
    if value is None:
        return None
    stripped = str(value).strip().replace(",", "")
    if not stripped:
        return None
    return Decimal(stripped)


def _parse_date(value: str) -> datetime:
    stripped = value.strip()
    for pattern in (
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ):
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


def parse_vanguard_personal_json(content: str) -> ParsedHoldings:
    payload = json.loads(content)
    items = payload.get("data") or []
    if not isinstance(items, list) or not items:
        raise ValueError("Vanguard holdings payload does not include any constituents")

    as_of = _parse_date(str(items[0].get("effectiveDate", "")).strip())
    constituents: list[Constituent] = []

    for item in items:
        raw_ticker = str(item.get("ticker") or "").strip().upper()
        if not raw_ticker:
            continue
        constituents.append(
            Constituent(
                ticker=raw_ticker,
                exchange=None,
                source_ticker=raw_ticker,
                source_exchange_code=str(item.get("countryCode") or "").strip().upper() or None,
                name=str(item.get("longName") or item.get("name") or raw_ticker).strip(),
                asset_class="Equity",
                sector=str(item.get("sectorName") or "").strip() or None,
                country=str(item.get("countryCode") or "").strip() or None,
                currency=None,
                weight_percentage=_parse_decimal(item.get("marketValPercent")) or Decimal("0"),
                units_held=_parse_decimal(item.get("units")),
                market_value=_parse_decimal(item.get("marketValue")),
            )
        )

    return ParsedHoldings(as_of=as_of, constituents=constituents)


def parse_vaneck_fund_dataset_json(content: str) -> ParsedHoldings:
    payload = json.loads(content)
    holdings_lists = payload.get("HoldingsList") or []
    if not isinstance(holdings_lists, list) or not holdings_lists:
        raise ValueError("VanEck dataset payload is missing HoldingsList")

    first_list = holdings_lists[0]
    as_of = _parse_date(str(first_list.get("AsOfDate", "")).strip())
    constituents: list[Constituent] = []

    for item in first_list.get("Holdings", []):
        source_ticker = (
            str(item.get("Label") or item.get("HoldingTicker") or item.get("Ticker") or "").strip()
        )
        if not source_ticker:
            continue
        ticker, source_exchange_code = _split_source_ticker(source_ticker)
        if not ticker:
            continue
        constituents.append(
            Constituent(
                ticker=ticker,
                exchange=exchange_from_source_code(source_exchange_code),
                source_ticker=source_ticker,
                source_exchange_code=source_exchange_code,
                name=str(item.get("HoldingName") or ticker).strip(),
                asset_class=str(item.get("AssetClass") or "").strip() or None,
                sector=str(item.get("Sector") or "").strip() or None,
                country=str(item.get("Country") or "").strip() or None,
                currency=str(item.get("CurrencyCode") or "").strip() or None,
                weight_percentage=_parse_decimal(item.get("Weight")) or Decimal("0"),
                units_held=_parse_decimal(item.get("Shares")),
                market_value=_parse_decimal(item.get("MV")),
            )
        )

    return ParsedHoldings(as_of=as_of, constituents=constituents)


PARSER_REGISTRY: dict[str, ParserFn] = {
    "betashares_csv": parse_betashares_csv,
    "blackrock_spreadsheet_xml": parse_blackrock_spreadsheet_xml,
    "vanguard_personal_json": parse_vanguard_personal_json,
    "vaneck_fund_dataset_json": parse_vaneck_fund_dataset_json,
}
