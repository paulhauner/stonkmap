from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from .models import PortfolioHolding


def load_portfolio_holdings(path: Path) -> list[PortfolioHolding]:
    holdings: list[PortfolioHolding] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            exchange = (row["exchange"] or "").strip().upper()
            ticker = (row["ticker"] or "").strip().upper()
            units = Decimal((row["units"] or "0").strip())
            holdings.append(PortfolioHolding(exchange=exchange, ticker=ticker, units=units))
    return holdings
