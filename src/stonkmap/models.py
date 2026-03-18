from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Constituent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    exchange: str | None = None
    source_ticker: str
    source_exchange_code: str | None = None
    name: str
    asset_class: str | None = None
    sector: str | None = None
    country: str | None = None
    currency: str | None = None
    weight_percentage: Decimal
    units_held: Decimal | None = None
    market_value: Decimal | None = None


class IndexBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    exchange: str
    ticker: str
    as_of: date
    fetched_at: datetime | None = None
    constituents: list[Constituent]


class PriceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: str
    ticker: str
    provider_symbol: str
    price: Decimal
    currency: str | None = None
    name: str | None = None
    quoted_at: datetime
    fetched_at: datetime | None = None


class PortfolioHolding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: str
    ticker: str
    units: Decimal


class CompanyExposure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: str | None = None
    ticker: str
    name: str
    market_value: Decimal
    weight_percentage: Decimal | None = None
    latest_price: Decimal | None = None
    sector: str | None = None
    country: str | None = None
    currency: str | None = None
    sources: list[str]


class PortfolioBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    holdings: list[PortfolioHolding]
    total_market_value: Decimal
    last_price_at: datetime | None = None
    companies: list[CompanyExposure]


class DashboardData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    indexes: list[IndexBreakdown]
    portfolios: list[PortfolioBreakdown]
    prices_last_updated_at: datetime | None = None
