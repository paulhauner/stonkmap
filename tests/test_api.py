from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from stonkmap.indexes.service import DocumentStore, IndexService
from stonkmap.main import create_app
from stonkmap.models import Constituent, IndexBreakdown, PriceQuote
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
                price={"A200": "135", "IOZ": "31", "VESG": "102.4", "VGE": "55.6", "CBA": "137.5", "BHP": "37.7", "MSFT": "489.2", "GOOG": "175", "GOOGL": "170", "TESTX": "250"}[
                    ticker
                ],
                quoted_at="2026-03-18T09:10:00+00:00",
            )
            for exchange, ticker in symbols
            if ticker in {"A200", "IOZ", "VESG", "VGE", "CBA", "BHP", "MSFT", "GOOG", "GOOGL", "TESTX"}
        ]
        skipped = [item for item in symbols if item[1] not in {"A200", "IOZ", "VESG", "VGE", "CBA", "BHP", "MSFT", "GOOG", "GOOGL", "TESTX"}]
        return quotes, skipped


class StaticIndexBreakdownService:
    def __init__(self, breakdowns: dict[tuple[str, str], IndexBreakdown]) -> None:
        self.breakdowns = breakdowns

    def fetch_breakdown(self, index_config):
        return self.breakdowns[(index_config.exchange, index_config.ticker)]

    def close(self) -> None:
        return None


def write_test_config(tmp_path: Path) -> Path:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text(
        "exchange,ticker,units,is_index\nASX,A200,10,true\nASX,IOZ,8,true\nASX,VGE,3,true\nNASDAQ,MSFT,4,false\n"
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
        assert payload["portfolios"][0]["unknown_indexes"][0]["ticker"] == "VGE"
        assert payload["unknown_indexes"][0]["ticker"] == "VGE"


def test_configured_indexes_are_not_marked_unknown_before_refresh(tmp_path: Path) -> None:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text("exchange,ticker,units,is_index\nASX,A200,10,true\n")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ports:
  backend: 18000
  frontend: 15173
portfolios:
  - name: Known Index Portfolio
    csv_path: ./portfolio.csv
"""
    )
    indexes_path = write_test_indexes(tmp_path)
    app = create_app(
        config_path=config_path,
        indexes_path=indexes_path,
        database_path=tmp_path / "stonkmap.sqlite3",
        index_service=IndexService(document_store=StaticDocumentStore({})),
        price_provider=StaticPriceProvider(),
    )

    with TestClient(app) as client:
        refresh_prices = client.post("/api/prices/refresh")
        assert refresh_prices.status_code == 200

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        payload = dashboard.json()
        assert payload["portfolios"][0]["unknown_indexes"] == []
        assert payload["unknown_indexes"] == []


def test_direct_holdings_merge_with_same_ticker_from_index(tmp_path: Path) -> None:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text(
        "exchange,ticker,units,is_index\nASX,VESG,10,true\nNASDAQ,MSFT,4,false\n"
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ports:
  backend: 18000
  frontend: 15173
portfolios:
  - name: Merge Portfolio
    csv_path: ./portfolio.csv
"""
    )
    indexes_path = tmp_path / "indexes.yaml"
    indexes_path.write_text(
        """
indexes:
  - name: Vanguard Ethically Conscious International Shares Index ETF
    exchange: ASX
    ticker: VESG
    holdings:
      provider: vanguard_personal_json
      url: https://example.test/vesg.json
      include_asset_classes:
        - Equity
        - Equities
"""
    )

    app = create_app(
        config_path=config_path,
        indexes_path=indexes_path,
        database_path=tmp_path / "stonkmap.sqlite3",
        index_service=IndexService(
            document_store=StaticDocumentStore(
                {
                    "https://example.test/vesg.json": (
                        FIXTURES / "vanguard_holdings_sample.json"
                    ).read_text(),
                }
            )
        ),
        price_provider=StaticPriceProvider(),
    )

    with TestClient(app) as client:
        refresh_indexes = client.post("/api/indexes/refresh")
        assert refresh_indexes.status_code == 200

        refresh_prices = client.post("/api/prices/refresh")
        assert refresh_prices.status_code == 200

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        portfolio = dashboard.json()["portfolios"][0]
        msft_companies = [company for company in portfolio["companies"] if company["ticker"] == "MSFT"]
        assert len(msft_companies) == 1
        assert msft_companies[0]["exchange"] == "NASDAQ"
        assert sorted(msft_companies[0]["sources"]) == [
            "Direct holding: NASDAQ:MSFT",
            "Index ASX:VESG (10 units)",
        ]


def test_same_ticker_from_two_indexes_merges_into_one_company(tmp_path: Path) -> None:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text(
        "exchange,ticker,units,is_index\nASX,A200,10,true\nASX,IOZ,8,true\n"
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ports:
  backend: 18000
  frontend: 15173
portfolios:
  - name: Multi Index Portfolio
    csv_path: ./portfolio.csv
"""
    )
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

        refresh_prices = client.post("/api/prices/refresh")
        assert refresh_prices.status_code == 200

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        portfolio = dashboard.json()["portfolios"][0]
        cba_companies = [company for company in portfolio["companies"] if company["ticker"] == "CBA"]
        assert len(cba_companies) == 1
        assert sorted(cba_companies[0]["sources"]) == [
            "Index ASX:A200 (10 units)",
            "Index ASX:IOZ (8 units)",
        ]


def test_dashboard_errors_when_portfolio_holding_quote_is_missing(tmp_path: Path) -> None:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text("exchange,ticker,units,is_index\nNASDAQ,META,1222,false\n")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ports:
  backend: 18000
  frontend: 15173
portfolios:
  - name: Missing Quote Portfolio
    csv_path: ./portfolio.csv
"""
    )
    indexes_path = tmp_path / "indexes.yaml"
    indexes_path.write_text("indexes: []\n")

    app = create_app(
        config_path=config_path,
        indexes_path=indexes_path,
        database_path=tmp_path / "stonkmap.sqlite3",
        index_service=IndexService(document_store=StaticDocumentStore({})),
        price_provider=StaticPriceProvider(),
    )

    with TestClient(app) as client:
        refresh_prices = client.post("/api/prices/refresh")
        assert refresh_prices.status_code == 200

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 409
        assert "Missing price quotes for portfolio holdings" in dashboard.json()["detail"]
        assert "Missing Quote Portfolio NASDAQ:META" in dashboard.json()["detail"]


def test_direct_holdings_can_be_combined_via_config(tmp_path: Path) -> None:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text(
        "exchange,ticker,units,is_index\nNASDAQ,GOOG,2,false\nNASDAQ,GOOGL,3,false\n"
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ports:
  backend: 18000
  frontend: 15173
portfolios:
  - name: Alphabet Portfolio
    csv_path: ./portfolio.csv
ticker_combinations:
  - stocks: [GOOGL, GOOG]
    combine_as: GOOG(L)
"""
    )
    indexes_path = tmp_path / "indexes.yaml"
    indexes_path.write_text("indexes: []\n")

    app = create_app(
        config_path=config_path,
        indexes_path=indexes_path,
        database_path=tmp_path / "stonkmap.sqlite3",
        index_service=IndexService(document_store=StaticDocumentStore({})),
        price_provider=StaticPriceProvider(),
    )

    with TestClient(app) as client:
        refresh_prices = client.post("/api/prices/refresh")
        assert refresh_prices.status_code == 200

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        portfolio = dashboard.json()["portfolios"][0]
        assert [company["ticker"] for company in portfolio["companies"]] == ["GOOG(L)"]
        assert portfolio["companies"][0]["latest_price"] is None
        assert portfolio["companies"][0]["market_value"] == "860"
        assert sorted(portfolio["companies"][0]["sources"]) == [
            "Direct holding: NASDAQ:GOOG",
            "Direct holding: NASDAQ:GOOGL",
        ]


def test_index_constituents_can_be_combined_via_config(tmp_path: Path) -> None:
    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text("exchange,ticker,units,is_index\nNASDAQ,TESTX,1,true\n")

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
ports:
  backend: 18000
  frontend: 15173
portfolios:
  - name: Combined Index Portfolio
    csv_path: ./portfolio.csv
ticker_combinations:
  - stocks: [GOOGL, GOOG]
    combine_as: GOOG(L)
"""
    )
    indexes_path = tmp_path / "indexes.yaml"
    indexes_path.write_text(
        """
indexes:
  - name: Test Alphabet Index
    exchange: NASDAQ
    ticker: TESTX
    holdings:
      provider: betashares_csv
      url: https://example.test/testx.csv
"""
    )

    breakdown = IndexBreakdown(
        name="Test Alphabet Index",
        exchange="NASDAQ",
        ticker="TESTX",
        as_of=date(2026, 3, 18),
        fetched_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
        constituents=[
            Constituent(
                ticker="GOOG",
                exchange="NASDAQ",
                source_ticker="GOOG UW",
                source_exchange_code="UW",
                name="Alphabet Inc. Class C",
                asset_class="Equities",
                sector="Communication Services",
                country="United States",
                currency="USD",
                weight_percentage="60",
                units_held="10",
                market_value="1500",
            ),
            Constituent(
                ticker="GOOGL",
                exchange="NASDAQ",
                source_ticker="GOOGL UW",
                source_exchange_code="UW",
                name="Alphabet Inc. Class A",
                asset_class="Equities",
                sector="Communication Services",
                country="United States",
                currency="USD",
                weight_percentage="40",
                units_held="8",
                market_value="1200",
            ),
        ],
    )

    app = create_app(
        config_path=config_path,
        indexes_path=indexes_path,
        database_path=tmp_path / "stonkmap.sqlite3",
        index_service=StaticIndexBreakdownService({("NASDAQ", "TESTX"): breakdown}),
        price_provider=StaticPriceProvider(),
    )

    with TestClient(app) as client:
        refresh_indexes = client.post("/api/indexes/refresh")
        assert refresh_indexes.status_code == 200

        refresh_prices = client.post("/api/prices/refresh")
        assert refresh_prices.status_code == 200

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        payload = dashboard.json()
        assert [item["ticker"] for item in payload["indexes"][0]["constituents"]] == ["GOOG(L)"]
        assert payload["indexes"][0]["constituents"][0]["weight_percentage"] == "100"
        assert [item["ticker"] for item in payload["portfolios"][0]["companies"]] == ["GOOG(L)"]
