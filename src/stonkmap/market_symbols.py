from __future__ import annotations


PORTFOLIO_EXCHANGE_TO_YAHOO_SUFFIX: dict[str, str] = {
    "ASX": ".AX",
    "NASDAQ": "",
    "NYSE": "",
    "LSE": ".L",
    "TSX": ".TO",
    "NZX": ".NZ",
    "BME": ".MC",
    "XETRA": ".DE",
    "EPA": ".PA",
    "BIT": ".MI",
    "AMS": ".AS",
    "SWX": ".SW",
    "HKEX": ".HK",
    "TSE": ".T",
}

BLOOMBERG_EXCHANGE_CODE_TO_PORTFOLIO_EXCHANGE: dict[str, str] = {
    "AT": "ASX",
    "AU": "ASX",
    "UN": "NYSE",
    "UW": "NASDAQ",
    "UQ": "NASDAQ",
    "LN": "LSE",
    "CT": "TSX",
    "NZ": "NZX",
    "SQ": "BME",
    "GY": "XETRA",
    "FP": "EPA",
    "IM": "BIT",
    "NA": "AMS",
    "SE": "SWX",
    "HK": "HKEX",
    "JT": "TSE",
}


def yahoo_symbol(exchange: str, ticker: str) -> str | None:
    suffix = PORTFOLIO_EXCHANGE_TO_YAHOO_SUFFIX.get(exchange.upper())
    if suffix is None:
        return None
    return f"{ticker.upper()}{suffix}"


def exchange_from_source_code(source_exchange_code: str | None) -> str | None:
    if not source_exchange_code:
        return None
    return BLOOMBERG_EXCHANGE_CODE_TO_PORTFOLIO_EXCHANGE.get(source_exchange_code.upper())
