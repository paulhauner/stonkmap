from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
import yfinance as yf

from ..market_symbols import yahoo_symbol
from ..models import PriceQuote


class PriceProvider:
    def fetch_quotes(
        self, symbols: list[tuple[str, str]]
    ) -> tuple[list[PriceQuote], list[tuple[str, str]]]:
        raise NotImplementedError


class YahooFinancePriceProvider(PriceProvider):
    def __init__(self, batch_size: int = 50) -> None:
        self.batch_size = batch_size

    def fetch_quotes(
        self, symbols: list[tuple[str, str]]
    ) -> tuple[list[PriceQuote], list[tuple[str, str]]]:
        mapped: list[tuple[str, str, str]] = []
        quotes: list[PriceQuote] = []
        skipped: list[tuple[str, str]] = []

        for exchange, ticker in symbols:
            provider_symbol = yahoo_symbol(exchange, ticker)
            if provider_symbol is None:
                skipped.append((exchange, ticker))
                continue
            mapped.append((exchange, ticker, provider_symbol))

        for start in range(0, len(mapped), self.batch_size):
            batch = mapped[start : start + self.batch_size]
            provider_symbols = [provider_symbol for _, _, provider_symbol in batch]
            history = yf.download(
                tickers=provider_symbols,
                period="5d",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
            close_frame = self._extract_close_frame(history)
            quoted_at = datetime.now(timezone.utc)
            for exchange, ticker, provider_symbol in batch:
                if provider_symbol not in close_frame.columns:
                    skipped.append((exchange, ticker))
                    continue
                close = close_frame[provider_symbol].dropna()
                if close.empty:
                    skipped.append((exchange, ticker))
                    continue
                quotes.append(
                    PriceQuote(
                        exchange=exchange,
                        ticker=ticker,
                        provider_symbol=provider_symbol,
                        price=Decimal(str(close.iloc[-1])),
                        quoted_at=quoted_at,
                    )
                )
        return quotes, skipped

    @staticmethod
    def _extract_close_frame(history: pd.DataFrame) -> pd.DataFrame:
        if history.empty:
            return pd.DataFrame()
        if isinstance(history.columns, pd.MultiIndex):
            return history["Close"]
        return history[["Close"]].rename(columns={"Close": history.columns[0]})
