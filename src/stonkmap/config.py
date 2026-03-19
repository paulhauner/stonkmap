from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SUPPORTED_HOLDINGS_PROVIDERS = (
    "betashares_csv",
    "blackrock_spreadsheet_xml",
    "vanguard_personal_json",
    "vaneck_fund_dataset_json",
)


class HoldingsSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal[
        "betashares_csv",
        "blackrock_spreadsheet_xml",
        "vanguard_personal_json",
        "vaneck_fund_dataset_json",
    ]
    url: str
    include_asset_classes: list[str] = Field(
        default_factory=lambda: ["Equity", "Equities"]
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped.startswith("http://") and not stripped.startswith("https://"):
            raise ValueError("holdings.url must be an absolute http(s) URL")
        return stripped


class IndexConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    exchange: str
    ticker: str
    holdings: HoldingsSourceConfig

    @field_validator("exchange", "ticker")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("symbols must not be empty")
        return stripped


class PortfolioConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    csv_path: Path


class TickerCombinationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stocks: list[str]
    combine_as: str

    @field_validator("stocks")
    @classmethod
    def normalize_stocks(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            ticker = item.strip().upper()
            if not ticker:
                raise ValueError("ticker combinations must not contain empty symbols")
            if ticker not in normalized:
                normalized.append(ticker)
        if len(normalized) < 2:
            raise ValueError("ticker combinations must contain at least two unique stocks")
        return normalized

    @field_validator("combine_as")
    @classmethod
    def normalize_combine_as(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not ticker:
            raise ValueError("combine_as must not be empty")
        return ticker


class PortsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: int
    frontend: int


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ports: PortsConfig
    portfolios: list[PortfolioConfig]
    ticker_combinations: list[TickerCombinationConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ticker_combinations(self) -> "AppConfig":
        seen_stocks: dict[str, str] = {}
        for combination in self.ticker_combinations:
            for stock in combination.stocks:
                previous = seen_stocks.get(stock)
                if previous is not None:
                    raise ValueError(
                        f"ticker {stock} appears in multiple ticker_combinations: {previous} and {combination.combine_as}"
                    )
                seen_stocks[stock] = combination.combine_as
        return self

    def resolve_paths(self, root: Path) -> "ResolvedAppConfig":
        return ResolvedAppConfig(
            ports=self.ports,
            portfolios=[
                ResolvedPortfolioConfig(name=item.name, csv_path=(root / item.csv_path).resolve())
                for item in self.portfolios
            ],
            ticker_combinations=self.ticker_combinations,
        )


class ResolvedPortfolioConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    csv_path: Path


class ResolvedAppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ports: PortsConfig
    portfolios: list[ResolvedPortfolioConfig]
    ticker_combinations: list[TickerCombinationConfig] = Field(default_factory=list)


class IndexCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indexes: list[IndexConfig]


def load_config(path: str | Path) -> ResolvedAppConfig:
    config_path = Path(path).resolve()
    raw = yaml.safe_load(config_path.read_text()) or {}
    config = AppConfig.model_validate(raw).resolve_paths(config_path.parent)
    for portfolio in config.portfolios:
        if not portfolio.csv_path.exists():
            raise FileNotFoundError(f"portfolio CSV not found: {portfolio.csv_path}")
        validate_portfolio_csv(portfolio.csv_path)
    return config


def load_index_catalog(path: str | Path) -> list[IndexConfig]:
    catalog_path = Path(path).resolve()
    raw = yaml.safe_load(catalog_path.read_text()) or {}
    catalog = IndexCatalog.model_validate(raw)
    return catalog.indexes


def validate_portfolio_csv(path: Path) -> None:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"exchange", "ticker", "units", "is_index"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError(
                f"{path} must have exactly these headers: exchange,ticker,units,is_index"
            )
