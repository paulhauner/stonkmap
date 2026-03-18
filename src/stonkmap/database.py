from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .models import Constituent, IndexBreakdown, PriceQuote


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS index_breakdowns (
                    exchange TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    holdings_as_of TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (exchange, ticker)
                );

                CREATE TABLE IF NOT EXISTS index_constituents (
                    index_exchange TEXT NOT NULL,
                    index_ticker TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    exchange TEXT,
                    source_ticker TEXT NOT NULL,
                    source_exchange_code TEXT,
                    name TEXT NOT NULL,
                    asset_class TEXT,
                    sector TEXT,
                    country TEXT,
                    currency TEXT,
                    weight_percentage TEXT NOT NULL,
                    units_held TEXT,
                    market_value TEXT,
                    position_order INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stock_prices (
                    exchange TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    provider_symbol TEXT NOT NULL,
                    price TEXT NOT NULL,
                    currency TEXT,
                    name TEXT,
                    quoted_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (exchange, ticker)
                );
                """
            )

    def save_index_breakdown(self, breakdown: IndexBreakdown, fetched_at: datetime) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO index_breakdowns(exchange, ticker, name, holdings_as_of, fetched_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(exchange, ticker) DO UPDATE SET
                    name = excluded.name,
                    holdings_as_of = excluded.holdings_as_of,
                    fetched_at = excluded.fetched_at
                """,
                (
                    breakdown.exchange,
                    breakdown.ticker,
                    breakdown.name,
                    breakdown.as_of.isoformat(),
                    fetched_at.isoformat(),
                ),
            )
            connection.execute(
                """
                DELETE FROM index_constituents
                WHERE index_exchange = ? AND index_ticker = ?
                """,
                (breakdown.exchange, breakdown.ticker),
            )
            for position, constituent in enumerate(breakdown.constituents):
                connection.execute(
                    """
                    INSERT INTO index_constituents(
                        index_exchange,
                        index_ticker,
                        ticker,
                        exchange,
                        source_ticker,
                        source_exchange_code,
                        name,
                        asset_class,
                        sector,
                        country,
                        currency,
                        weight_percentage,
                        units_held,
                        market_value,
                        position_order
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        breakdown.exchange,
                        breakdown.ticker,
                        constituent.ticker,
                        constituent.exchange,
                        constituent.source_ticker,
                        constituent.source_exchange_code,
                        constituent.name,
                        constituent.asset_class,
                        constituent.sector,
                        constituent.country,
                        constituent.currency,
                        str(constituent.weight_percentage),
                        str(constituent.units_held) if constituent.units_held is not None else None,
                        str(constituent.market_value) if constituent.market_value is not None else None,
                        position,
                    ),
                )

    def list_index_breakdowns(self) -> list[IndexBreakdown]:
        with self.connect() as connection:
            breakdown_rows = connection.execute(
                """
                SELECT exchange, ticker, name, holdings_as_of, fetched_at
                FROM index_breakdowns
                ORDER BY exchange, ticker
                """
            ).fetchall()
            breakdowns: list[IndexBreakdown] = []
            for row in breakdown_rows:
                constituent_rows = connection.execute(
                    """
                    SELECT ticker, exchange, source_ticker, source_exchange_code, name,
                           asset_class, sector, country, currency, weight_percentage,
                           units_held, market_value
                    FROM index_constituents
                    WHERE index_exchange = ? AND index_ticker = ?
                    ORDER BY position_order ASC
                    """,
                    (row["exchange"], row["ticker"]),
                ).fetchall()
                breakdowns.append(
                    IndexBreakdown(
                        name=row["name"],
                        exchange=row["exchange"],
                        ticker=row["ticker"],
                        as_of=datetime.fromisoformat(row["holdings_as_of"]).date(),
                        fetched_at=datetime.fromisoformat(row["fetched_at"]),
                        constituents=[
                            Constituent(
                                ticker=item["ticker"],
                                exchange=item["exchange"],
                                source_ticker=item["source_ticker"],
                                source_exchange_code=item["source_exchange_code"],
                                name=item["name"],
                                asset_class=item["asset_class"],
                                sector=item["sector"],
                                country=item["country"],
                                currency=item["currency"],
                                weight_percentage=Decimal(item["weight_percentage"]),
                                units_held=_parse_decimal(item["units_held"]),
                                market_value=_parse_decimal(item["market_value"]),
                            )
                            for item in constituent_rows
                        ],
                    )
                )
            return breakdowns

    def get_index_breakdown(self, exchange: str, ticker: str) -> IndexBreakdown | None:
        lookup = {
            (item.exchange, item.ticker): item for item in self.list_index_breakdowns()
        }
        return lookup.get((exchange.upper(), ticker.upper()))

    def save_prices(self, quotes: list[PriceQuote], fetched_at: datetime) -> None:
        with self.connect() as connection:
            for quote in quotes:
                connection.execute(
                    """
                    INSERT INTO stock_prices(exchange, ticker, provider_symbol, price, currency, name, quoted_at, fetched_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(exchange, ticker) DO UPDATE SET
                        provider_symbol = excluded.provider_symbol,
                        price = excluded.price,
                        currency = excluded.currency,
                        name = excluded.name,
                        quoted_at = excluded.quoted_at,
                        fetched_at = excluded.fetched_at
                    """,
                    (
                        quote.exchange,
                        quote.ticker,
                        quote.provider_symbol,
                        str(quote.price),
                        quote.currency,
                        quote.name,
                        quote.quoted_at.isoformat(),
                        fetched_at.isoformat(),
                    ),
                )

    def list_prices(self) -> list[PriceQuote]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT exchange, ticker, provider_symbol, price, currency, name, quoted_at, fetched_at
                FROM stock_prices
                ORDER BY exchange, ticker
                """
            ).fetchall()
        return [
            PriceQuote(
                exchange=row["exchange"],
                ticker=row["ticker"],
                provider_symbol=row["provider_symbol"],
                price=Decimal(row["price"]),
                currency=row["currency"],
                name=row["name"],
                quoted_at=datetime.fromisoformat(row["quoted_at"]),
                fetched_at=datetime.fromisoformat(row["fetched_at"]),
            )
            for row in rows
        ]

    def get_price(self, exchange: str, ticker: str) -> PriceQuote | None:
        lookup = {(item.exchange, item.ticker): item for item in self.list_prices()}
        return lookup.get((exchange.upper(), ticker.upper()))

    def latest_price_fetched_at(self) -> datetime | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT MAX(fetched_at) AS latest FROM stock_prices"
            ).fetchone()
        if row is None or row["latest"] is None:
            return None
        return datetime.fromisoformat(row["latest"])
