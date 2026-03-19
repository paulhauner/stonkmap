import {
  ArrowPathIcon,
  BanknotesIcon,
  ChevronDownIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/react';
import { type ReactNode, useEffect, useState } from 'react';
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useParams,
} from 'react-router-dom';

import { fetchDashboard, refreshIndexes, refreshPrices } from './api';
import { Heatmap } from './components/Heatmap';
import { StatPill } from './components/StatPill';
import { StockModal } from './components/StockModal';
import { formatDateTime, formatMoney, formatPercent } from './format';
import type {
  CompanyExposure,
  Constituent,
  DashboardData,
  IndexBreakdown,
  PortfolioBreakdown,
  UnknownIndex,
} from './types';

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

type AppRoutesProps = {
  dashboard: DashboardData;
  busyAction: 'indexes' | 'prices' | null;
  onRunAction: (action: 'indexes' | 'prices') => Promise<void>;
  onSelectStock: (stock: SelectedStock) => void;
};

function slugify(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function portfolioPath(portfolio: PortfolioBreakdown) {
  return `/portfolios/${slugify(portfolio.name)}`;
}

function indexPath(index: IndexBreakdown) {
  return `/indexes/${index.exchange}/${index.ticker}`;
}

function buildUnknownIndexesPrompt(unknownIndexes: UnknownIndex[]) {
  const missingIndexes = Array.from(
    new Set(unknownIndexes.map((entry) => `${entry.exchange}:${entry.ticker}`)),
  ).sort();

  return [
    'Update indexes.yaml for this Stonkmap project.',
    '',
    'The following holdings are marked is_index=true in portfolio CSVs but are missing from indexes.yaml:',
    ...missingIndexes.map((entry) => `- ${entry}`),
    '',
    'Requirements:',
    '- Keep existing indexes.yaml entries unchanged unless a correction is required.',
    '- Add new entries under the top-level `indexes:` list.',
    '- Use a canonical holdings source URL for each fund.',
    '- Use one of the currently supported providers: `betashares_csv` or `blackrock_spreadsheet_xml`.',
    '- Set `include_asset_classes` so equity holdings are kept.',
    '- If a fund cannot be supported with the current providers, explain which new provider is needed instead of inventing a broken entry.',
  ].join('\n');
}

function UnknownIndexesCard({ unknownIndexes }: { unknownIndexes: UnknownIndex[] }) {
  const [copied, setCopied] = useState(false);

  if (unknownIndexes.length === 0) {
    return null;
  }

  const prompt = buildUnknownIndexesPrompt(unknownIndexes);

  async function copyPrompt() {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="panel-card warning-card">
      <div className="panel-header">
        <div>
          <p className="eyebrow subtle">Unknown indexes</p>
          <h2>Some holdings are marked `is_index=true` but do not exist in `indexes.yaml`.</h2>
          <p>Copy this prompt into an LLM chat to patch `indexes.yaml` with the missing scraping definitions.</p>
        </div>
      </div>
      <div className="copy-actions">
        <button className="secondary-button" onClick={() => void copyPrompt()} type="button">
          {copied ? 'Copied' : 'Copy LLM Prompt'}
        </button>
        <span className="copy-hint">The prompt is also shown below as plain text.</span>
      </div>
      <textarea className="copy-prompt" readOnly rows={12} value={prompt} />
    </section>
  );
}

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

function TopBar({ dashboard, busyAction, onRunAction }: Omit<AppRoutesProps, 'onSelectStock'>) {
  const location = useLocation();
  const homePath = dashboard.portfolios[0] ? portfolioPath(dashboard.portfolios[0]) : '/indexes';

  return (
    <nav className="top-bar">
      <Link className="brand-link" to={homePath}>
        <span className="brand-mark">SM</span>
        <span className="brand-copy">
          <strong>Stonkmap</strong>
          <small>Portfolio heatmaps</small>
        </span>
      </Link>

      <div className="top-bar-links">
        <Menu as="div" className="nav-menu">
          <MenuButton className="nav-button">
            Portfolios
            <ChevronDownIcon />
          </MenuButton>
          <MenuItems anchor="bottom start" className="dropdown-menu">
            {dashboard.portfolios.map((portfolio) => {
              const path = portfolioPath(portfolio);
              const active = location.pathname === path;
              return (
                <MenuItem key={portfolio.name}>
                  {({ focus }) => (
                    <Link className={`dropdown-item${focus || active ? ' is-active' : ''}`} to={path}>
                      <span>{portfolio.name}</span>
                      <small>{portfolio.holdings.length} holdings</small>
                    </Link>
                  )}
                </MenuItem>
              );
            })}
          </MenuItems>
        </Menu>

        <NavLink
          className={({ isActive }) => `nav-button${isActive ? ' is-active' : ''}`}
          to="/indexes"
        >
          Indexes
        </NavLink>
      </div>

      <div className="top-bar-actions">
        <button
          className="primary-button"
          onClick={() => void onRunAction('indexes')}
          disabled={busyAction !== null}
        >
          <ArrowPathIcon />
          {busyAction === 'indexes' ? 'Refreshing indexes…' : 'Refresh Indexes'}
        </button>
        <button
          className="secondary-button"
          onClick={() => void onRunAction('prices')}
          disabled={busyAction !== null}
        >
          <BanknotesIcon />
          {busyAction === 'prices' ? 'Refreshing prices…' : 'Refresh Prices'}
        </button>
      </div>
    </nav>
  );
}

function PageChrome({ dashboard, children }: { dashboard: DashboardData; children: ReactNode }) {
  return (
    <>
      <section className="stats-row">
        <StatPill label="Portfolios" value={String(dashboard.portfolios.length)} />
        <StatPill label="Tracked Indexes" value={String(dashboard.indexes.length)} />
        <StatPill label="Prices Updated" value={formatDateTime(dashboard.prices_last_updated_at)} />
        <StatPill label="Generated" value={formatDateTime(dashboard.generated_at)} />
      </section>

      <main className="page-stack">{children}</main>
    </>
  );
}

function PortfolioPage({
  dashboard,
  onSelectStock,
}: Pick<AppRoutesProps, 'dashboard' | 'onSelectStock'>) {
  const { portfolioSlug } = useParams();
  const portfolio = dashboard.portfolios.find((entry) => slugify(entry.name) === portfolioSlug);

  if (!portfolio) {
    return (
      <section className="panel-card">
        <h2>Portfolio not found</h2>
      </section>
    );
  }

  return (
    <>
      <section className="panel-card page-header-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow subtle">Portfolio</p>
            <h2>{portfolio.name}</h2>
            <p>{portfolio.holdings.length} config-defined holdings</p>
          </div>
          <div className="panel-meta">
            <span>Total value {formatMoney(portfolio.total_market_value)}</span>
            <span>Prices refreshed {formatDateTime(portfolio.last_price_at)}</span>
          </div>
        </div>
        <div className="holding-chip-row">
          {portfolio.holdings.map((holding) => (
            <div className="holding-chip" key={`${holding.exchange}:${holding.ticker}`}>
              <strong>
                {holding.exchange}:{holding.ticker}
              </strong>
              <span>{holding.units} units{holding.is_index ? ' · index' : ''}</span>
            </div>
          ))}
        </div>
      </section>

      <UnknownIndexesCard unknownIndexes={portfolio.unknown_indexes} />

      <Heatmap
        title={`${portfolio.name} company exposure`}
        data={portfolio.companies.map(toPortfolioTile)}
        emptyMessage="Price data is missing for this portfolio. Refresh prices to generate a meaningful heatmap."
        formatValue={(value) => formatMoney(value)}
        onSelect={(item) =>
          onSelectStock({
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
        valueLabel="value"
      />
    </>
  );
}

function IndexesListPage({ dashboard }: Pick<AppRoutesProps, 'dashboard'>) {
  return (
    <>
      <UnknownIndexesCard unknownIndexes={dashboard.unknown_indexes} />
      <section className="index-grid">
        {dashboard.indexes.map((index) => (
          <Link className="panel-card index-card-link" key={`${index.exchange}:${index.ticker}`} to={indexPath(index)}>
            <div className="panel-header">
              <div>
                <p className="eyebrow subtle">Index</p>
                <h2>
                  {index.exchange}:{index.ticker}
                </h2>
                <p>{index.name}</p>
              </div>
              <div className="panel-meta">
                <span>{index.constituents.length} companies</span>
                <span>Holdings {formatDateTime(index.as_of)}</span>
              </div>
            </div>
          </Link>
        ))}
      </section>
    </>
  );
}

function IndexDetailPage({
  dashboard,
  onSelectStock,
}: Pick<AppRoutesProps, 'dashboard' | 'onSelectStock'>) {
  const { exchange, ticker } = useParams();
  const index = dashboard.indexes.find(
    (entry) => entry.exchange === exchange && entry.ticker === ticker,
  );

  if (!index) {
    return (
      <section className="panel-card">
        <h2>Index not found</h2>
      </section>
    );
  }

  return (
    <>
      <section className="panel-card page-header-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow subtle">Index</p>
            <h2>
              {index.exchange}:{index.ticker}
            </h2>
            <p>{index.name}</p>
          </div>
          <div className="panel-meta">
            <span>{index.constituents.length} companies</span>
            <span>Holdings {formatDateTime(index.as_of)}</span>
            <span>Fetched {formatDateTime(index.fetched_at)}</span>
          </div>
        </div>
      </section>

      <Heatmap
        title={`${index.ticker} constituents`}
        data={index.constituents.map(toIndexTile)}
        formatValue={(value) => formatPercent(value)}
        onSelect={(item) =>
          onSelectStock({
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
        valueLabel="weight"
      />
    </>
  );
}

function AppRoutes({ dashboard, busyAction, onRunAction, onSelectStock }: AppRoutesProps) {
  const defaultPortfolio = dashboard.portfolios[0];

  return (
    <>
      <TopBar dashboard={dashboard} busyAction={busyAction} onRunAction={onRunAction} />
      <PageChrome dashboard={dashboard}>
        <Routes>
          <Route
            path="/"
            element={
              defaultPortfolio ? (
                <Navigate replace to={portfolioPath(defaultPortfolio)} />
              ) : (
                <Navigate replace to="/indexes" />
              )
            }
          />
          <Route
            path="/portfolios/:portfolioSlug"
            element={<PortfolioPage dashboard={dashboard} onSelectStock={onSelectStock} />}
          />
          <Route path="/indexes" element={<IndexesListPage dashboard={dashboard} />} />
          <Route
            path="/indexes/:exchange/:ticker"
            element={<IndexDetailPage dashboard={dashboard} onSelectStock={onSelectStock} />}
          />
          <Route
            path="*"
            element={<Navigate replace to={defaultPortfolio ? portfolioPath(defaultPortfolio) : '/indexes'} />}
          />
        </Routes>
      </PageChrome>
    </>
  );
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
    <BrowserRouter>
      <div className="app-shell">
        {error ? <div className="error-banner">{error}</div> : null}
        {loading ? <div className="loading-panel">Loading dashboard…</div> : null}

        {!loading && dashboard ? (
          <AppRoutes
            dashboard={dashboard}
            busyAction={busyAction}
            onRunAction={runAction}
            onSelectStock={setSelectedStock}
          />
        ) : null}

        {!loading &&
        dashboard &&
        dashboard.indexes.length === 0 &&
        dashboard.portfolios.every((portfolio) => portfolio.companies.length === 0) ? (
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
    </BrowserRouter>
  );
}
