from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import IndexConfig, ResolvedAppConfig, load_config, load_index_catalog
from .dashboard import DashboardService
from .database import Database
from .indexes.service import IndexService
from .portfolio import load_portfolio_holdings
from .prices.service import PriceProvider, YahooFinancePriceProvider

DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_INDEXES_PATH = Path("indexes.yaml")
DEFAULT_DATABASE_PATH = Path("data/stonkmap.sqlite3")


class ApplicationServices:
    def __init__(
        self,
        config: ResolvedAppConfig,
        indexes: list[IndexConfig],
        database: Database,
        index_service: IndexService,
        price_provider: PriceProvider,
    ) -> None:
        self.config = config
        self.indexes = indexes
        self.database = database
        self.index_service = index_service
        self.price_provider = price_provider
        self.dashboard_service = DashboardService(config, indexes, database)

    def tracked_indexes(self):
        tracked = self.dashboard_service.tracked_index_keys()
        return [
            item
            for item in self.indexes
            if (item.exchange, item.ticker) in tracked
        ]


def create_app(
    config_path: str | Path | None = None,
    indexes_path: str | Path | None = None,
    database_path: str | Path | None = None,
    index_service: IndexService | None = None,
    price_provider: PriceProvider | None = None,
) -> FastAPI:
    resolved_config_path = Path(config_path or os.getenv("STONKMAP_CONFIG", DEFAULT_CONFIG_PATH))
    resolved_indexes_path = Path(
        indexes_path or os.getenv("STONKMAP_INDEXES_PATH", DEFAULT_INDEXES_PATH)
    )
    resolved_database_path = Path(
        database_path or os.getenv("STONKMAP_DB_PATH", DEFAULT_DATABASE_PATH)
    )
    config = load_config(resolved_config_path)
    indexes = load_index_catalog(resolved_indexes_path)
    database = Database(resolved_database_path)
    database.initialize()
    services = ApplicationServices(
        config=config,
        indexes=indexes,
        database=database,
        index_service=index_service or IndexService(),
        price_provider=price_provider or YahooFinancePriceProvider(),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = services
        yield
        services.index_service.close()

    app = FastAPI(title="Stonkmap API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://localhost:{config.ports.frontend}",
            f"http://127.0.0.1:{config.ports.frontend}",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def healthcheck():
        return {"status": "ok"}

    @app.get("/api/dashboard")
    def dashboard():
        return services.dashboard_service.build_dashboard().model_dump(mode="json")

    @app.get("/api/indexes")
    def indexes():
        return [item.model_dump(mode="json") for item in services.dashboard_service.list_indexes()]

    @app.post("/api/indexes/refresh")
    def refresh_indexes():
        refreshed = []
        for index_config in services.tracked_indexes():
            breakdown = services.index_service.fetch_breakdown(index_config)
            fetched_at = datetime.now(timezone.utc)
            services.database.save_index_breakdown(breakdown, fetched_at)
            refreshed.append(
                {
                    "exchange": breakdown.exchange,
                    "ticker": breakdown.ticker,
                    "constituents": len(breakdown.constituents),
                    "as_of": breakdown.as_of.isoformat(),
                    "fetched_at": fetched_at.isoformat(),
                }
            )
        return {"indexes": refreshed}

    @app.post("/api/prices/refresh")
    def refresh_prices():
        symbols = {(holding.exchange, holding.ticker) for portfolio in services.config.portfolios for holding in load_portfolio_holdings(portfolio.csv_path)}
        for index in services.dashboard_service.list_indexes():
            for constituent in index.constituents:
                if constituent.exchange is not None:
                    symbols.add((constituent.exchange, constituent.ticker))
        quotes, skipped = services.price_provider.fetch_quotes(sorted(symbols))
        fetched_at = datetime.now(timezone.utc)
        services.database.save_prices(quotes, fetched_at)
        return {
            "stored": len(quotes),
            "skipped": [{"exchange": exchange, "ticker": ticker} for exchange, ticker in skipped],
            "fetched_at": fetched_at.isoformat(),
        }

    return app


def create_default_app() -> FastAPI:
    config_path = Path(os.getenv("STONKMAP_CONFIG", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        config_path = Path("config.example.yaml")
    indexes_path = Path(os.getenv("STONKMAP_INDEXES_PATH", DEFAULT_INDEXES_PATH))
    database_path = Path(os.getenv("STONKMAP_DB_PATH", DEFAULT_DATABASE_PATH))
    return create_app(
        config_path=config_path,
        indexes_path=indexes_path,
        database_path=database_path,
    )


app = create_default_app()


def run() -> None:
    import uvicorn

    config = load_config(Path(os.getenv("STONKMAP_CONFIG", DEFAULT_CONFIG_PATH)))
    uvicorn.run(
        "stonkmap.main:app",
        host="0.0.0.0",
        port=config.ports.backend,
        reload=False,
    )
