# Design

Stonkmap is a self-hosted, locally-served web application that visualises stock portfolios.

The application is not designed to be an exhaustive portfolio management tool, it implements a few features only.

## Tech Stack

- Backend: Python FastAPI
- Frontend: React with Typescript
    - UI Components: Headless UI
    - Icons: heroicons/reach
- Database: sqlite

## Configuration

A `config.example.yaml` file is located in the root directory which contains an example configuration file. This should include:

- The ports for the front and backend.
- A list of initial indexes to include in the scrape.

## Features

- Ability to support multiple exchanges (e.g. exchange is always specified alongside index).

### Index Breakdowns

For a given list of indexes, we present the weights of the companies included.

- We find canonical methods for determining the stocks that constitute that index.
- We store the latest breakdown for each index, including:
    - Exchange and ticker for the index (e.g. VESG on the ASX)
    - Each company inside that index (e.g. GOOG, APPL)
    - The number of units held in the index (e.g. 1000)
- There is an option in the front-end to trigger an update of the index components from the canonical source. No routine updates.
- On the front-end show, the date of the last update.
- Provide a "Stock Heatmap" (See "UI Components" section) for each index.

### Portfolio Breakdowns

For a "portfolio" (a list of stocks/indexes), give breakdowns of the companies included.

- Support for multiple named portfolios.
- A portfolio may include stocks or indexes from multiple exchanges.
- Provide a "Stock Heatmap" (See "UI Components" section) for each portfolio.

### Stock Prices

For each of the stocks in a tracked index or a portfolio, store the current stock price.

- Pull these from reliable market data sources.
- Provide a front-end option to refresh all prices. No routine price updates.
- On the front-end show, the date of the last update.

## UI Components

### Stock Heatmap

A front-end to display each stock inside an index\portfolio as a heatmap.

- Use an existing visualisation library, don't reinvent the wheel.
- Larger $ portion of index\portfolio = larger square.
- Each square has the stock ticker.
- Hover shows the name of the stock.
- Clicking on the square opens up an information modal, showing basic info.

## Goals

- Should *not* be an at-scale, multi-user production app.
- Should be easy to spin up using `docker compose`.
- Should be developed by LLMs.