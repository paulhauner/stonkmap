import { ArrowPathIcon, BanknotesIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { useEffect, useState } from 'react';

import { fetchDashboard, refreshIndexes, refreshPrices } from './api';
import { Heatmap } from './components/Heatmap';
import { StatPill } from './components/StatPill';
import { StockModal } from './components/StockModal';
import { formatDateTime, formatMoney, formatPercent } from './format';
import type { CompanyExposure, Constituent, DashboardData, IndexBreakdown, PortfolioBreakdown } from './types';

type SelectedStock = {
  exchange?: string | null;
  ticker: string;
  name: string;
  weightPercentage?: string | null;
  marketValue?: string | null;
  price?: string | null;
  sector?: string | null;
  country?: string | null;
  currency?: string | null;
  sources?: string[];
};

function toPortfolioTile(item: CompanyExposure) {
  return {
    id: `${item.exchange ?? 'unknown'}:${item.ticker}`,
    ticker: item.ticker,
    name: item.name,
    size: Number(item.market_value),
    secondaryLabel: formatMoney(item.market_value),
    exchange: item.exchange,
    marketValue: item.market_value,
    price: item.latest_price,
    sector: item.sector,
    country: item.country,
    currency: item.currency,
    sources: item.sources,
    weightPercentage: item.weight_percentage,
  };
}

function toIndexTile(item: Constituent) {
  return {
    id: `${item.exchange ?? 'unknown'}:${item.ticker}`,
    ticker: item.ticker,
    name: item.name,
    size: Number(item.weight_percentage),
    secondaryLabel: formatPercent(item.weight_percentage),
    exchange: item.exchange,
    marketValue: item.market_value,
    price: null,
    sector: item.sector,
    country: item.country,
    currency: item.currency,
    sources: [`Constituent of ${item.source_ticker}`],
    weightPercentage: item.weight_percentage,
  };
}

export default function App() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<'indexes' | 'prices' | null>(null);
  const [selectedStock, setSelectedStock] = useState<SelectedStock | null>(null);

  async function loadDashboard() {
    setError(null);
    setLoading(true);
    try {
      setDashboard(await fetchDashboard());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function runAction(action: 'indexes' | 'prices') {
    setBusyAction(action);
    try {
      if (action === 'indexes') {
        await refreshIndexes();
      } else {
        await refreshPrices();
      }
      await loadDashboard();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Refresh failed');
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Stonkmap</p>
          <h1>See the actual companies hiding inside your ETF-heavy portfolio.</h1>
          <p className="hero-copy">
            Portfolios are loaded from config-driven CSV files. Index breakdowns and stock prices are cached in SQLite and refreshed on demand.
          </p>
        </div>
        <div className="hero-actions">
          <button className="primary-button" onClick={() => void runAction('indexes')} disabled={busyAction !== null}>
            <ArrowPathIcon />
            {busyAction === 'indexes' ? 'Refreshing index breakdowns…' : 'Refresh Index Breakdown'}
          </button>
          <button className="secondary-button" onClick={() => void runAction('prices')} disabled={busyAction !== null}>
            <BanknotesIcon />
            {busyAction === 'prices' ? 'Refreshing stock prices…' : 'Refresh Prices'}
          </button>
        </div>
      </header>

      {dashboard ? (
        <section className="stats-row">
          <StatPill label="Portfolios" value={String(dashboard.portfolios.length)} />
          <StatPill label="Tracked Indexes" value={String(dashboard.indexes.length)} />
          <StatPill label="Prices Updated" value={formatDateTime(dashboard.prices_last_updated_at)} />
          <StatPill label="Generated" value={formatDateTime(dashboard.generated_at)} />
        </section>
      ) : null}

      {error ? <div className="error-banner">{error}</div> : null}
      {loading ? <div className="loading-panel">Loading dashboard…</div> : null}

      {dashboard ? (
        <main className="dashboard-grid">
          <section className="column">
            <div className="section-heading">
              <h2>Portfolios</h2>
              <span>Config-defined portfolio CSVs</span>
            </div>
            {dashboard.portfolios.map((portfolio: PortfolioBreakdown) => (
              <article className="panel-card" key={portfolio.name}>
                <div className="panel-header">
                  <div>
                    <h3>{portfolio.name}</h3>
                    <p>{portfolio.holdings.length} holdings</p>
                  </div>
                  <div className="panel-meta">
                    <span>Total value {formatMoney(portfolio.total_market_value)}</span>
                    <span>Prices {formatDateTime(portfolio.last_price_at)}</span>
                  </div>
                </div>
                <Heatmap
                  title={`${portfolio.name} company exposure`}
                  data={portfolio.companies.map(toPortfolioTile)}
                  onSelect={(item) =>
                    setSelectedStock({
                      exchange: item.exchange,
                      ticker: item.ticker,
                      name: item.name,
                      weightPercentage: item.weightPercentage ?? null,
                      marketValue: item.marketValue ?? null,
                      price: item.price ?? null,
                      sector: item.sector ?? null,
                      country: item.country ?? null,
                      currency: item.currency ?? null,
                      sources: item.sources ?? [],
                    })
                  }
                />
              </article>
            ))}
          </section>

          <section className="column">
            <div className="section-heading">
              <h2>Index Breakdowns</h2>
              <span>Only indexes found in the configured portfolios</span>
            </div>
            {dashboard.indexes.map((index: IndexBreakdown) => (
              <article className="panel-card" key={`${index.exchange}:${index.ticker}`}>
                <div className="panel-header">
                  <div>
                    <h3>
                      {index.exchange}:{index.ticker}
                    </h3>
                    <p>{index.name}</p>
                  </div>
                  <div className="panel-meta">
                    <span>Holdings as of {formatDateTime(index.as_of)}</span>
                    <span>Fetched {formatDateTime(index.fetched_at)}</span>
                  </div>
                </div>
                <Heatmap
                  title={`${index.ticker} constituents`}
                  data={index.constituents.map(toIndexTile)}
                  onSelect={(item) =>
                    setSelectedStock({
                      exchange: item.exchange,
                      ticker: item.ticker,
                      name: item.name,
                      weightPercentage: item.weightPercentage ?? null,
                      marketValue: item.marketValue ?? null,
                      price: item.price ?? null,
                      sector: item.sector ?? null,
                      country: item.country ?? null,
                      currency: item.currency ?? null,
                    })
                  }
                />
              </article>
            ))}
          </section>
        </main>
      ) : null}

      {!loading && dashboard && dashboard.indexes.length === 0 && dashboard.portfolios.every((portfolio) => portfolio.companies.length === 0) ? (
        <section className="empty-dashboard">
          <SparklesIcon />
          <div>
            <h2>Start by refreshing index breakdowns, then stock prices.</h2>
            <p>The sample config is wired up, but the dashboard stays empty until the first refresh populates SQLite.</p>
          </div>
        </section>
      ) : null}

      <StockModal stock={selectedStock} onClose={() => setSelectedStock(null)} />
    </div>
  );
}
