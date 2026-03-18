from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from stonkmap.indexes.service import DocumentStore, IndexService
from stonkmap.main import create_app
from stonkmap.models import PriceQuote
from stonkmap.prices.service import PriceProvider


FIXTURES = Path(__file__).parent / "fixtures"


class StaticDocumentStore(DocumentStore):
    def __init__(self, payloads: dict[str, str]) -> None:
        self.payloads = payloads

    def fetch_text(self, url: str) -> str:
        return self.payloads[url]


class StaticPriceProvider(PriceProvider):
    def fetch_quotes(self, symbols: list[tuple[str, str]]):
        quotes = [
            PriceQuote(
                exchange=exchange,
                ticker=ticker,
                provider_symbol=f"{ticker}.TEST",
                price={"A200": "135", "IOZ": "31", "CBA": "137.5", "BHP": "37.7", "MSFT": "489.2"}[
                    ticker
                ],
                quoted_at="2026-03-18T09:10:00+00:00",
            )
            for exchange, ticker in symbols
            if ticker in {"A200", "IOZ", "CBA", "BHP", "MSFT"}
        ]
        skipped = [item for item in symbols if item[1] not in {"A200", "IOZ", "CBA", "BHP", "MSFT"}]
        return quotes, skipped


def write_test_config(tmp_path: Path) -> Path:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text(
        "exchange,ticker,units\nASX,A200,10\nASX,IOZ,8\nNASDAQ,MSFT,4\n"
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
ports:
  backend: 18000
  frontend: 15173
portfolios:
  - name: Test Portfolio
    csv_path: ./portfolio.csv
"""
    )
    return config_path


def write_test_indexes(tmp_path: Path) -> Path:
    indexes_path = tmp_path / "indexes.yaml"
    indexes_path.write_text(
        """
indexes:
  - name: Betashares Australia 200 ETF
    exchange: ASX
    ticker: A200
    holdings:
      provider: betashares_csv
      url: https://example.test/a200.csv
      include_asset_classes:
        - Equity
        - Equities
  - name: iShares Core S&P/ASX 200 ETF
    exchange: ASX
    ticker: IOZ
    holdings:
      provider: blackrock_spreadsheet_xml
      url: https://example.test/ioz.xml
      include_asset_classes:
        - Equity
        - Equities
"""
    )
    return indexes_path


def test_refresh_endpoints_populate_dashboard(tmp_path: Path) -> None:
    config_path = write_test_config(tmp_path)
    indexes_path = write_test_indexes(tmp_path)
    app = create_app(
        config_path=config_path,
        indexes_path=indexes_path,
        database_path=tmp_path / "stonkmap.sqlite3",
        index_service=IndexService(
            document_store=StaticDocumentStore(
                {
                    "https://example.test/a200.csv": (
                        FIXTURES / "betashares_sample.csv"
                    ).read_text(),
                    "https://example.test/ioz.xml": (
                        FIXTURES / "blackrock_sample.xml"
                    ).read_text(),
                }
            )
        ),
        price_provider=StaticPriceProvider(),
    )

    with TestClient(app) as client:
        refresh_indexes = client.post("/api/indexes/refresh")
        assert refresh_indexes.status_code == 200
        assert len(refresh_indexes.json()["indexes"]) == 2

        refresh_prices = client.post("/api/prices/refresh")
        assert refresh_prices.status_code == 200
        assert refresh_prices.json()["stored"] >= 5

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        payload = dashboard.json()
        assert len(payload["indexes"]) == 2
        assert payload["portfolios"][0]["name"] == "Test Portfolio"
        assert payload["portfolios"][0]["companies"][0]["ticker"] in {"CBA", "BHP", "MSFT"}
