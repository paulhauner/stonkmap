from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from .config import IndexConfig, ResolvedAppConfig
from .database import Database
from .models import (
    CompanyExposure,
    DashboardData,
    IndexBreakdown,
    PortfolioBreakdown,
    UnknownIndex,
)
from .portfolio import load_portfolio_holdings


class DashboardService:
    def __init__(
        self, config: ResolvedAppConfig, indexes: list[IndexConfig], database: Database
    ) -> None:
        self.config = config
        self.indexes = indexes
        self.database = database

    def tracked_index_keys(self) -> set[tuple[str, str]]:
        configured_indexes = {(item.exchange, item.ticker) for item in self.indexes}
        tracked: set[tuple[str, str]] = set()
        for portfolio in self.config.portfolios:
            for holding in load_portfolio_holdings(portfolio.csv_path):
                key = (holding.exchange, holding.ticker)
                if holding.is_index and key in configured_indexes:
                    tracked.add(key)
        return tracked

    def list_indexes(self) -> list[IndexBreakdown]:
        tracked = self.tracked_index_keys()
        return [
            item
            for item in self.database.list_index_breakdowns()
            if (item.exchange, item.ticker) in tracked
        ]

    def build_dashboard(self) -> DashboardData:
        indexes = self.list_indexes()
        index_lookup = {(item.exchange, item.ticker): item for item in indexes}
        configured_index_keys = {(item.exchange, item.ticker) for item in self.indexes}
        price_lookup = {
            (item.exchange, item.ticker): item for item in self.database.list_prices()
        }
        portfolios: list[PortfolioBreakdown] = []
        unknown_indexes: list[UnknownIndex] = []

        for portfolio in self.config.portfolios:
            holdings = load_portfolio_holdings(portfolio.csv_path)
            exposures: dict[tuple[str | None, str], dict[str, object]] = {}
            total_market_value = Decimal("0")
            latest_price_at = None
            portfolio_unknown_indexes: list[UnknownIndex] = []

            for holding in holdings:
                price = price_lookup.get((holding.exchange, holding.ticker))
                if price is not None:
                    latest_price_at = max(
                        [value for value in [latest_price_at, price.fetched_at] if value is not None]
                    )
                position_market_value = (
                    holding.units * price.price if price is not None else Decimal("0")
                )
                total_market_value += position_market_value
                if not holding.is_index:
                    key = (holding.exchange, holding.ticker)
                    item = exposures.setdefault(
                        key,
                        {
                            "exchange": holding.exchange,
                            "ticker": holding.ticker,
                            "name": price.name or holding.ticker if price is not None else holding.ticker,
                            "market_value": Decimal("0"),
                            "latest_price": price.price if price is not None else None,
                            "sector": None,
                            "country": None,
                            "currency": price.currency if price is not None else None,
                            "sources": [],
                        },
                    )
                    item["market_value"] += position_market_value
                    item["sources"].append(f"Direct holding: {holding.exchange}:{holding.ticker}")
                    continue

                key = (holding.exchange, holding.ticker)
                if key not in configured_index_keys:
                    unknown_index = UnknownIndex(
                        portfolio_name=portfolio.name,
                        exchange=holding.exchange,
                        ticker=holding.ticker,
                        units=holding.units,
                    )
                    portfolio_unknown_indexes.append(unknown_index)
                    unknown_indexes.append(unknown_index)
                    continue
                breakdown = index_lookup.get(key)
                if breakdown is None:
                    continue

                for constituent in breakdown.constituents:
                    key = (constituent.exchange, constituent.ticker)
                    constituent_price = (
                        price_lookup.get((constituent.exchange, constituent.ticker))
                        if constituent.exchange is not None
                        else None
                    )
                    constituent_market_value = (
                        position_market_value * constituent.weight_percentage / Decimal("100")
                    )
                    item = exposures.setdefault(
                        key,
                        {
                            "exchange": constituent.exchange,
                            "ticker": constituent.ticker,
                            "name": constituent.name,
                            "market_value": Decimal("0"),
                            "latest_price": constituent_price.price if constituent_price is not None else None,
                            "sector": constituent.sector,
                            "country": constituent.country,
                            "currency": constituent.currency,
                            "sources": [],
                        },
                    )
                    item["market_value"] += constituent_market_value
                    item["sources"].append(
                        f"Index {breakdown.exchange}:{breakdown.ticker} ({holding.units} units)"
                    )

            companies = [
                CompanyExposure(
                    exchange=payload["exchange"],
                    ticker=payload["ticker"],
                    name=payload["name"],
                    market_value=payload["market_value"],
                    weight_percentage=(
                        (payload["market_value"] / total_market_value * Decimal("100"))
                        if total_market_value > 0
                        else None
                    ),
                    latest_price=payload["latest_price"],
                    sector=payload["sector"],
                    country=payload["country"],
                    currency=payload["currency"],
                    sources=sorted(set(payload["sources"])),
                )
                for payload in exposures.values()
            ]
            companies.sort(key=lambda item: item.market_value, reverse=True)
            portfolios.append(
                PortfolioBreakdown(
                    name=portfolio.name,
                    holdings=holdings,
                    total_market_value=total_market_value,
                    last_price_at=latest_price_at,
                    companies=companies,
                    unknown_indexes=portfolio_unknown_indexes,
                )
            )

        return DashboardData(
            generated_at=datetime.now(timezone.utc),
            indexes=indexes,
            portfolios=portfolios,
            unknown_indexes=unknown_indexes,
            prices_last_updated_at=self.database.latest_price_fetched_at(),
        )
