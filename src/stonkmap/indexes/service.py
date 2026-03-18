from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from ..config import IndexConfig
from ..models import IndexBreakdown
from .parsers import PARSER_REGISTRY


class DocumentStore:
    def fetch_text(self, url: str) -> str:
        raise NotImplementedError


class HttpDocumentStore(DocumentStore):
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/csv,application/xml,text/xml,text/plain,*/*",
                "Accept-Language": "en-AU,en;q=0.9",
            },
        )

    def fetch_text(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()
        return response.text

    def close(self) -> None:
        self.client.close()


@dataclass
class IndexRefreshResult:
    exchange: str
    ticker: str
    constituent_count: int
    as_of: str


class IndexService:
    def __init__(self, document_store: DocumentStore | None = None) -> None:
        self.document_store = document_store or HttpDocumentStore()

    def fetch_breakdown(self, index_config: IndexConfig) -> IndexBreakdown:
        parser = PARSER_REGISTRY[index_config.holdings.provider]
        parsed = parser(self.document_store.fetch_text(index_config.holdings.url))
        include_asset_classes = {value.casefold() for value in index_config.holdings.include_asset_classes}
        constituents = [
            item
            for item in parsed.constituents
            if item.asset_class is None or item.asset_class.casefold() in include_asset_classes
        ]
        constituents.sort(key=lambda item: item.weight_percentage, reverse=True)
        return IndexBreakdown(
            name=index_config.name,
            exchange=index_config.exchange,
            ticker=index_config.ticker,
            as_of=parsed.as_of.date(),
            fetched_at=datetime.utcnow(),
            constituents=constituents,
        )

    def close(self) -> None:
        close = getattr(self.document_store, "close", None)
        if callable(close):
            close()
