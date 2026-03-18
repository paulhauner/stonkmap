from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


SUPPORTED_HOLDINGS_PROVIDERS = ("betashares_csv", "blackrock_spreadsheet_xml")


class HoldingsSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["betashares_csv", "blackrock_spreadsheet_xml"]
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


class PortsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: int
    frontend: int


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ports: PortsConfig
    portfolios: list[PortfolioConfig]

    def resolve_paths(self, root: Path) -> "ResolvedAppConfig":
        return ResolvedAppConfig(
            ports=self.ports,
            portfolios=[
                ResolvedPortfolioConfig(name=item.name, csv_path=(root / item.csv_path).resolve())
                for item in self.portfolios
            ],
        )


class ResolvedPortfolioConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    csv_path: Path


class ResolvedAppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ports: PortsConfig
    portfolios: list[ResolvedPortfolioConfig]


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
        expected = {"exchange", "ticker", "units"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError(
                f"{path} must have exactly these headers: exchange,ticker,units"
            )
