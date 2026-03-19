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


class MissingPriceDataError(Exception):
    def __init__(self, missing_holdings: list[tuple[str, str, str]]) -> None:
        self.missing_holdings = sorted(set(missing_holdings))
        formatted = ", ".join(
            f"{portfolio_name} {exchange}:{ticker}"
            for portfolio_name, exchange, ticker in self.missing_holdings
        )
        super().__init__(
            f"Missing price quotes for portfolio holdings: {formatted}. Refresh prices before loading the dashboard."
        )


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

    @staticmethod
    def _resolve_exposure_key(
        exposures: dict[tuple[str | None, str], dict[str, object]],
        exchange: str | None,
        ticker: str,
    ) -> tuple[str | None, str]:
        exact_key = (exchange, ticker)
        if exact_key in exposures:
            return exact_key

        same_ticker_keys = [key for key in exposures if key[1] == ticker]
        if not same_ticker_keys:
            return exact_key

        unknown_key = (None, ticker)
        if exchange is not None and unknown_key in exposures:
            payload = exposures.pop(unknown_key)
            payload["exchange"] = exchange
            exposures[exact_key] = payload
            return exact_key

        non_null_matches = [key for key in same_ticker_keys if key[0] is not None]
        if exchange is None and len(non_null_matches) == 1:
            return non_null_matches[0]
        if len(same_ticker_keys) == 1:
            return same_ticker_keys[0]
        return exact_key

    @staticmethod
    def _update_exposure_metadata(
        item: dict[str, object],
        *,
        exchange: str | None,
        name: str,
        latest_price: Decimal | None,
        sector: str | None,
        country: str | None,
        currency: str | None,
    ) -> None:
        if item["exchange"] is None and exchange is not None:
            item["exchange"] = exchange
        if (not item["name"] or item["name"] == item["ticker"]) and name:
            item["name"] = name
        if item["latest_price"] is None and latest_price is not None:
            item["latest_price"] = latest_price
        if item["sector"] is None and sector is not None:
            item["sector"] = sector
        if item["country"] is None and country is not None:
            item["country"] = country
        if item["currency"] is None and currency is not None:
            item["currency"] = currency

    def build_dashboard(self) -> DashboardData:
        indexes = self.list_indexes()
        index_lookup = {(item.exchange, item.ticker): item for item in indexes}
        configured_index_keys = {(item.exchange, item.ticker) for item in self.indexes}
        price_lookup = {
            (item.exchange, item.ticker): item for item in self.database.list_prices()
        }
        portfolios: list[PortfolioBreakdown] = []
        unknown_indexes: list[UnknownIndex] = []
        missing_price_holdings: list[tuple[str, str, str]] = []

        for portfolio in self.config.portfolios:
            holdings = load_portfolio_holdings(portfolio.csv_path)
            exposures: dict[tuple[str | None, str], dict[str, object]] = {}
            total_market_value = Decimal("0")
            latest_price_at = None
            portfolio_unknown_indexes: list[UnknownIndex] = []

            for holding in holdings:
                price = price_lookup.get((holding.exchange, holding.ticker))
                if price is None:
                    missing_price_holdings.append(
                        (portfolio.name, holding.exchange, holding.ticker)
                    )
                    continue
                if price is not None:
                    latest_price_at = max(
                        [value for value in [latest_price_at, price.fetched_at] if value is not None]
                    )
                position_market_value = (
                    holding.units * price.price if price is not None else Decimal("0")
                )
                total_market_value += position_market_value
                if not holding.is_index:
                    key = self._resolve_exposure_key(exposures, holding.exchange, holding.ticker)
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
                    self._update_exposure_metadata(
                        item,
                        exchange=holding.exchange,
                        name=price.name or holding.ticker if price is not None else holding.ticker,
                        latest_price=price.price if price is not None else None,
                        sector=None,
                        country=None,
                        currency=price.currency if price is not None else None,
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
                    key = self._resolve_exposure_key(
                        exposures,
                        constituent.exchange,
                        constituent.ticker,
                    )
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
                    self._update_exposure_metadata(
                        item,
                        exchange=constituent.exchange,
                        name=constituent.name,
                        latest_price=constituent_price.price if constituent_price is not None else None,
                        sector=constituent.sector,
                        country=constituent.country,
                        currency=constituent.currency,
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

        if missing_price_holdings:
            raise MissingPriceDataError(missing_price_holdings)

        return DashboardData(
            generated_at=datetime.now(timezone.utc),
            indexes=indexes,
            portfolios=portfolios,
            unknown_indexes=unknown_indexes,
            prices_last_updated_at=self.database.latest_price_fetched_at(),
        )
